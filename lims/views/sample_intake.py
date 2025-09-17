from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from collections import defaultdict
from django.shortcuts import render, redirect
from django.utils import timezone
from lims.models import Client, Parameter, TestAssignment, SampleStatus
from lims.forms import ClientForm, SampleFormWithParameters
from django.forms import formset_factory
from django.contrib.auth import get_user_model
from notifications.utils import notify  
from lims.utils.notifications import notify_lab_manager_on_submission, notify_client_on_submission
from django.conf import settings
from users.models import RoleChoices
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.utils.timezone import now
from weasyprint import HTML, CSS



User = get_user_model()

from django.db.models import Max

def generate_client_id():
    prefix = "JGLSP"
    # Get the last numeric part after prefix
    last_client = Client.objects.aggregate(max_id=Max('client_id'))['max_id']
    
    if last_client and last_client.startswith(prefix):
        try:
            number = int(last_client[len(prefix):]) + 1
        except ValueError:
            number = 2500112
    else:
        number = 2500112
    
    return f"{prefix}{str(number).zfill(7)}"


def generate_token():
    today = timezone.now().date()
    count_today = Client.objects.filter(created__date=today).count() + 1
    return f"JGL-{today.strftime('%Y%m%d')}-{count_today:04d}"


@csrf_protect
@login_required
def sample_intake_view(request):
    SampleFormSet = formset_factory(SampleFormWithParameters, extra=1)

    if request.method == 'POST':
        client_form = ClientForm(request.POST)
        sample_formset = SampleFormSet(request.POST, prefix='samples')

        if client_form.is_valid() and sample_formset.is_valid():
            client = client_form.save(commit=False)
            client.client_id = generate_client_id()
            client.token = generate_token()
            client.save()

            # Save samples and assign parameters
            for form in sample_formset:
                sample = form.save(commit=False)
                sample.client = client
                sample.status = SampleStatus.RECEIVED
                sample.save()

                for param in form.cleaned_data['parameters']:
                    TestAssignment.objects.create(sample=sample, parameter=param)

            # ✅ Notify managers
            sample_count = len(sample_formset)
            client_name = client.name
            client_id = client.client_id
            clerk_name = request.user.get_full_name()
            sample_count = len(sample_formset)
            client_email = client.email
            client_token = client.token

            managers = User.objects.filter(role=RoleChoices.MANAGER, is_active=True)
            for manager in managers:
                print(f"📧 Manager email: {manager.email}")
                notify_lab_manager_on_submission(
                    manager.email,
                    sample_count,
                    client_name,
                    client_id,
                    clerk_name
                )
            
            all_parameters = set()
            for form in sample_formset:
                for param in form.cleaned_data['parameters']:
                    all_parameters.add(param.name)
            parameter_list = list(all_parameters)

            # Notify the client
            notify_client_on_submission(
                    client_email,
                    sample_count,
                    parameter_list,
                    client_id,
                    client_token
                    )
            return redirect('intake_confirmation', client_id=client.client_id)

    else:
        client_form = ClientForm()
        sample_formset = SampleFormSet(prefix='samples')

    # Build parameter groupings for checkbox rendering
    group_map = defaultdict(list)
    for param in Parameter.objects.select_related("group").all():
        group_map[param.group.name].append(param)

    parameter_groups = [{'name': k, 'parameters': v} for k, v in group_map.items()]

    return render(request, 'lims/clerk/sample_intake.html', {
        'client_form': client_form,
        'sample_formset': sample_formset,
        'parameter_groups': parameter_groups,
    })

@login_required
def download_sample_intake_pdf(request):
    # Generate blank forms for PDF template
    SampleFormSet = formset_factory(SampleFormWithParameters, extra=1)
    client_form = ClientForm()
    sample_formset = SampleFormSet(prefix='samples')

    # Group parameters by category
    group_map = defaultdict(list)
    for param in Parameter.objects.select_related("group").all():
        group_map[param.group.name].append(param)

    parameter_groups = [{'name': k, 'parameters': v} for k, v in group_map.items()]

    # Render HTML from static template
    html_string = render_to_string('lims/clerk/sample_intake_print.html', {
        'client_form': client_form,
        'sample_formset': sample_formset,
        'parameter_groups': parameter_groups,
    })

    # Render to PDF using WeasyPrint
    html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
    pdf = html.write_pdf()

    # Optional: add timestamp to filename
    timestamp = now().strftime('%Y%m%d_%H%M')
    filename = f"sample_intake_print_{timestamp}.pdf"

    # Return as downloadable PDF
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
