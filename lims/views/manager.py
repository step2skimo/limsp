from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from lims.models import Sample, TestAssignment, Client
from django.utils import timezone
from django.template.loader import render_to_string
from weasyprint import HTML
from django.http import HttpResponse
from collections import defaultdict
from django.db.models import Prefetch
from lims.models import QCMetrics
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from lims.models import Sample, Client
from lims.models.equipment import Equipment, CalibrationRecord
from datetime import timedelta, date
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from collections import defaultdict
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Prefetch
from weasyprint import HTML
from lims.models import Client, Sample, TestAssignment, Parameter

from django.contrib.auth.decorators import login_required
from django.db.models import Count, F, Q, Avg
from django.db.models.functions import TruncMonth

@login_required
def manager_dashboard(request):
    today = date.today()
    soon = today + timedelta(days=7)

    # 🧪 All verified samples
    verified_samples = Sample.objects.filter(status='results_verified').select_related('client')

    # 👥 Clients with verified samples
    clients = Client.objects.filter(sample__status='results_verified').distinct()

    # 📦 Per-client sample grouping
    client_data = []
    for client in clients:
        samples = verified_samples.filter(client=client)
        if samples.exists():
            client_data.append({
                'client': client,
                'samples': samples,
                'sample_count': samples.count()
            })

    # ✅ QC Metrics Summary
    qc_summary = {
        "total": QCMetrics.objects.count(),
        "pass": QCMetrics.objects.filter(status="pass").count(),
        "fail": QCMetrics.objects.filter(status="fail").count()
    }

    # 📊 QC Parameter Coverage
    total_parameters = Parameter.objects.count()
    qc_parameters = (
        TestAssignment.objects
        .filter(is_control=True, sample__sample_type='QC')
        .values('parameter_id')
        .distinct()
        .count()
    )

    # 🚨 Parameters with failed QC
    failed_qc_parameters = (
        QCMetrics.objects
        .exclude(
            measured_value__gte=F('min_acceptable'),
            measured_value__lte=F('max_acceptable')
        )
        .values_list('test_assignment__parameter_id', flat=True)
        .distinct()
    )
    failed_qc_param_names = Parameter.objects.filter(id__in=failed_qc_parameters)

    # 📈 QC Trend Data Grouped by Analyst and Parameter
    qc_chart_data = (
        QCMetrics.objects
        .annotate(month=TruncMonth('test_assignment__assigned_date'))
        .values(
            'test_assignment__parameter__name',
            'test_assignment__analyst__username',
            'month'
        )
        .annotate(avg_measured_value=Avg('measured_value'))
        .order_by('test_assignment__analyst__username', 'month')
    )

    # ⚙️ Equipment Calibration & Expiring Alerts
    equipment_list = Equipment.objects.prefetch_related("calibrations").all()
    expiring_calibrations = CalibrationRecord.objects.filter(
        expires_on__lte=soon,
        expires_on__gte=today
    ).select_related('equipment')

    # 🔁 Latest Client for linking assignment overview
    latest_client = Client.objects.order_by('-client_id').first()

    return render(request, "lims/manager_dashboard.html", {
        "client_data": client_data,
        "verified_samples": verified_samples,
        "qc_summary": qc_summary,
        "equipment_list": equipment_list,
        "expiring_calibrations": expiring_calibrations,
        "today": today,
        "latest_client": latest_client,
        "total_parameters": total_parameters,
        "qc_param_count": qc_parameters,
        "failed_qc_param_names": failed_qc_param_names,
        "qc_chart_data": list(qc_chart_data),  # For JSON safety in template
    })




@login_required
def manager_coa_dashboard(request, client_id):
    client = get_object_or_404(Client, client_id=client_id)
    samples = Sample.objects.filter(client=client, status='results_verified')

    context = {
        'client': client,
        'samples': samples,
        'formats': [
            {'name': 'Single-Sample', 'url': 'lims:generate_coa_pdf', 'icon': '📄'},
            {'name': 'Combined', 'url': 'lims:generate_combined_coa_pdf', 'icon': '📚'},
            {'name': 'Pivoted', 'url': 'lims:generate_pivoted_coa_pdf', 'icon': '📊'},
        ]
    }
    return render(request, 'lims/manager_coa_dashboard.html', context)



@login_required
def manager_coa_tools_view(request):
    query = request.GET.get('q', '')
    filter_days = request.GET.get('days', '')

    clients = Client.objects.all().prefetch_related('sample_set')

    if query:
        clients = clients.filter(
            Q(name__icontains=query) |
            Q(organization__icontains=query)
        )

    if filter_days:
        try:
            days = int(filter_days)
            recent_date = timezone.now() - timedelta(days=days)
            clients = clients.filter(sample__created__gte=recent_date).distinct()
        except ValueError:
            pass

    return render(request, 'lims/manager_coa_tools.html', {
        'clients': clients,
        'query': query,
        'filter_days': filter_days,
    })



@login_required
def result_review_view(request, sample_id):
    sample = get_object_or_404(Sample, id=sample_id)
    tests = TestAssignment.objects.filter(sample=sample).select_related('parameter', 'testresult')

    if request.method == 'POST':
        for test in tests:
            test.status = 'verified'
            test.save(update_fields=['status'])
        sample.status = 'results_verified'
        sample.verified_at = timezone.now()
        sample.save(update_fields=['status', 'verified_at'])
        return redirect('manager_dashboard')  

    return render(request, 'lims/review_results.html', {
        'sample': sample,
        'tests': tests
    })



@login_required
def generate_coa_pdf(request, client_id, sample_id):
    sample = get_object_or_404(Sample, id=sample_id)
    client = sample.client

    tests = TestAssignment.objects.filter(sample=sample)\
        .select_related('parameter', 'testresult')\
        .prefetch_related('testenvironment', 'testenvironment__instrument')

    context = {
        'sample': sample,
        'client': client,
        'tests': tests,
        'now': timezone.now(),
        'generated_by': request.user,
    }

    html = render_to_string('lims/coa_pdf.html', context)
    pdf = HTML(string=html).write_pdf()

    filename = f"COA_{client.client_id}_{sample.sample_code}.pdf"

    return HttpResponse(
        pdf,
        content_type='application/pdf',
        headers={'Content-Disposition': f'inline; filename="{filename}"'}
    )


@login_required
def generate_pivoted_coa_pdf(request, client_id):
    client = get_object_or_404(Client, client_id=client_id)
    samples = Sample.objects.filter(client=client, status='results_verified').order_by('received_date')

    test_qs = TestAssignment.objects.select_related('parameter')\
                                    .prefetch_related('testresult_set', 'testenvironment_set', 'testenvironment_set__instrument')

    samples = samples.prefetch_related(Prefetch('testassignment_set', queryset=test_qs, to_attr='tests'))

    parameter_map = {}
    result_matrix = defaultdict(dict)
    env_matrix = defaultdict(lambda: defaultdict(dict))

    for sample in samples:
        for test in getattr(sample, 'tests', []):
            param = test.parameter
            parameter_map[param.id] = param

            # Assume testresult_set is a related manager - get first test result
            testresult = test.testresult_set.first()
            result_matrix[sample.id][param.id] = testresult.value if testresult else None

            # For environment, similarly take first related environment if exists
            testenv = test.testenvironment_set.first()
            if testenv:
                env_matrix[sample.id][param.id] = {
                    'temperature': testenv.temperature,
                    'humidity': testenv.humidity,
                    'instrument': testenv.instrument.name if testenv.instrument else None,
                }

    parameters = sorted(parameter_map.values(), key=lambda p: p.name.lower())

    context = {
        'client': client,
        'samples': samples,
        'parameters': parameters,
        'results_dict': result_matrix,
        'env_dict': env_matrix,
        'now': timezone.now(),
        'generated_by': request.user
    }

    html = render_to_string('lims/pivoted_coa_pdf.html', context)
    pdf = HTML(string=html).write_pdf()

    filename = f"COA_{client.client_id}_Pivoted.pdf"
    return HttpResponse(pdf, content_type='application/pdf',
                        headers={'Content-Disposition': f'inline; filename="{filename}"'})


@login_required
def generate_combined_coa_pdf(request, client_id):
    client = get_object_or_404(Client, client_id=client_id)
    samples = Sample.objects.filter(client=client, status='results_verified')
    return render(request, "lims/combined_coa_view.html", {"client": client, "samples": samples})


@login_required
def result_review_page(request):
    return render(request, 'lims/result_review.html')