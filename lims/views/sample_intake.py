from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from collections import defaultdict
from django.shortcuts import render, redirect
from django.utils import timezone
from lims.models import Client, Parameter, TestAssignment
from lims.forms import ClientForm, SampleFormWithParameters
from django.forms import formset_factory


def generate_client_id():
    last = Client.objects.order_by('created').last()
    if last and last.client_id.startswith("JGLSP"):
        try:
            number = int(last.client_id.replace("JGLSP", "")) + 1
        except ValueError:
            number = 2500
    else:
        number = 2500
    return f"JGLSP{number}"


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

            # ✅ Auto-generate client_id and token
            client.client_id = generate_client_id()
            client.token = generate_token()
            client.save()

            samples = []
            for form in sample_formset:
                sample = form.save(commit=False)
                sample.client = client
                sample.save()
                samples.append(sample)

            # ✅ Gather parameters selected per sample
            selected_param_ids = []
            for i in range(len(sample_formset)):
                selected_param_ids += request.POST.getlist(f'samples-{i}-parameters')

            parameters = Parameter.objects.filter(id__in=selected_param_ids)

            # ✅ Assign parameters to each sample
            for sample in samples:
                for param in parameters:
                    TestAssignment.objects.create(sample=sample, parameter=param)

            return redirect('intake_confirmation', client_id=client.client_id)

    else:
        client_form = ClientForm()
        sample_formset = SampleFormSet(prefix='samples')

    # ✅ Group parameters by category for form display
    group_map = defaultdict(list)
    for param in Parameter.objects.select_related("group").all():
        group_map[param.group.name].append(param)

    parameter_groups = [{'name': k, 'parameters': v} for k, v in group_map.items()]

    return render(request, 'lims/sample_intake.html', {
        'client_form': client_form,
        'sample_formset': sample_formset,
        'parameter_groups': parameter_groups,
    })
