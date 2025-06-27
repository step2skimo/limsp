from django.shortcuts import render, redirect, get_object_or_404
from lims.models import Client, Sample, Parameter, TestAssignment, User
from django.urls import reverse
from django.db.models import Count, Q
from django.db.models import Count, F
from django.shortcuts import render, redirect, get_object_or_404
from lims.models import Client, Sample, Parameter, TestAssignment, QCMetrics, ControlSpec, User
import csv
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from notifications.utils import notify  # cross-app import
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect

User = get_user_model()

@csrf_protect
@login_required
def assign_parameter_tests(request, client_id, parameter_id):
    client = get_object_or_404(Client, client_id=client_id)
    parameter = get_object_or_404(Parameter, id=parameter_id)
    analysts = User.objects.filter(groups__name="Analyst")
    samples = Sample.objects.filter(client=client).exclude(sample_type="QC")

    if request.method == "POST":
        analyst_id = request.POST.get("analyst")
        analyst = get_object_or_404(User, id=analyst_id)
        sample_ids = request.POST.getlist("sample_ids")
        control_sample_id = request.POST.get("control_sample_id")

        selected_samples = Sample.objects.filter(id__in=sample_ids) if sample_ids else samples

        for sample in selected_samples:
            is_control = str(sample.id) == control_sample_id
            TestAssignment.objects.update_or_create(
                sample=sample,
                parameter=parameter,
                defaults={
                    "analyst": analyst,
                    "is_control": is_control,
                    "assigned_date": timezone.now(),
                }
            )

        # Update sample statuses if still in "received"
        for sample in selected_samples:
            if sample.status == SampleStatus.RECEIVED:
                sample.status = SampleStatus.ASSIGNED
                sample.save(update_fields=["status"])

        # Create QC sample if needed
        base_code = f"QC-{client.client_id}-{parameter.name[:3].upper()}"
        sample_code = base_code
        count = 1
        while Sample.objects.filter(sample_code=sample_code).exists():
            sample_code = f"{base_code}-{count}"
            count += 1

        qc_sample, _ = Sample.objects.get_or_create(
            sample_code=sample_code,
            defaults={
                "client": client,
                "sample_type": "QC",
                "weight": 0
            }
        )

        if qc_sample.status == SampleStatus.RECEIVED:
            qc_sample.status = SampleStatus.ASSIGNED
            qc_sample.save(update_fields=["status"])

        qc_assignment, _ = TestAssignment.objects.get_or_create(
            sample=qc_sample,
            parameter=parameter,
            defaults={
                "analyst": analyst,
                "is_control": True
            }
        )

        if hasattr(parameter, 'control_spec'):
            spec = parameter.control_spec
            QCMetrics.objects.update_or_create(
                test_assignment=qc_assignment,
                defaults={
                    "min_acceptable": spec.min_acceptable,
                    "max_acceptable": spec.max_acceptable,
                    "measured_value": None,
                }
            )

        sample_count = selected_samples.count()
        notify(
            analyst,
            f"Hi {analyst.first_name}, You’ve been assigned to analyze {sample_count} sample(s) for Client ID CID-{client.client_id}.\nParameter: {parameter.name}"
        )

        return redirect('assign_by_parameter_overview', client_id=client.client_id)

    assigned_sample_ids = TestAssignment.objects.filter(
        sample__client=client,
        parameter=parameter
    ).values_list('sample_id', flat=True)

    current_control_id = TestAssignment.objects.filter(
        sample__client=client,
        parameter=parameter,
        is_control=True
    ).values_list('sample_id', flat=True).first()

    for sample in samples:
        assignment = sample.testassignment_set.filter(parameter=parameter).first()
        sample.assigned_analyst_name = assignment.analyst.get_full_name() if assignment and assignment.analyst else ""

    return render(request, "lims/manager/assign_by_parameter_form.html", {
        "client": client,
        "parameter": parameter,
        "samples": samples,
        "analysts": analysts,
        "assigned_sample_ids": assigned_sample_ids,
        "current_control_id": current_control_id
    })


def assign_by_parameter_overview(request, client_id):
    client = get_object_or_404(Client, client_id=client_id)

    # Only non-QC client samples
    samples = Sample.objects.filter(client=client).exclude(sample_type="QC")
    total_samples = samples.count()

    # Count only assignments WITH analysts (true assignment)
    parameter_stats = (
        TestAssignment.objects
        .filter(sample__client=client, analyst__isnull=False)
        .exclude(sample__sample_type="QC")
        .values('parameter_id')
        .annotate(assigned_count=Count('sample', distinct=True))
    )
    assigned_lookup = {
        stat['parameter_id']: stat['assigned_count'] for stat in parameter_stats
    }

    # Parameters linked to client samples (exclude QC sample parameter ghosts)
    parameter_ids = (
        TestAssignment.objects
        .filter(sample__client=client)
        .exclude(sample__sample_type="QC")
        .values_list('parameter', flat=True)
        .distinct()
    )
    parameters = Parameter.objects.filter(id__in=parameter_ids).order_by('name')

    paginator = Paginator(parameters, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    paginated_parameters = page_obj.object_list

    # Detect QC for each parameter using only is_control (sample type doesn’t matter)
    control_stats = (
        TestAssignment.objects
        .filter(sample__client=client, is_control=True)
        .values('parameter')
        .annotate(control_sample_id=F('sample_id'))
    )
    control_lookup = {
        stat['parameter']: stat['control_sample_id'] for stat in control_stats
    }

    return render(request, "lims/manager/assign_by_parameter_overview.html", {
        "client": client,
        "samples": samples,
        "parameters": paginated_parameters,
        "page_obj": page_obj,
        "assigned_lookup": assigned_lookup,
        "total_samples": total_samples,
        "control_lookup": control_lookup,
    })



def export_assignments_csv(request, client_id):
    client = get_object_or_404(Client, client_id=client_id)
    assignments = TestAssignment.objects.filter(sample__client=client).select_related('sample', 'parameter', 'analyst')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="assignments_{client_id}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Sample ID', 'Parameter', 'Analyst', 'Is Control'])

    for a in assignments:
        writer.writerow([a.sample.sample_code, a.parameter.name, a.analyst.username if a.analyst else '', a.is_control])

    return response

def export_assignments_pdf(request, client_id):
    client = get_object_or_404(Client, client_id=client_id)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="assignments_{client_id}.pdf"'

    p = canvas.Canvas(response)
    p.setFont("Helvetica", 12)
    y = 800

    assignments = TestAssignment.objects.filter(sample__client=client).select_related('sample', 'parameter', 'analyst')
    p.drawString(50, y, f"Assignments for Client {client_id}")
    y -= 30

    for a in assignments:
        line = f"{a.sample.sample_code} | {a.parameter.name} | {a.analyst.username if a.analyst else '---'} | {'QC' if a.is_control else 'Normal'}"
        p.drawString(50, y, line)
        y -= 20
        if y < 50:
            p.showPage()
            y = 800

    p.save()
    return response
