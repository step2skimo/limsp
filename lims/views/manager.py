from django.shortcuts import render, get_object_or_404, redirect
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
from collections import defaultdict
from django.db.models import Count, Q, Prefetch
from django.contrib.auth.decorators import login_required
from django.db.models import Count, F, Q, Avg
from django.db.models.functions import TruncMonth
from lims.models import SampleStatus


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

    # 🚨 Parameters with failed QC (with analyst)
    failed_qc_info = (
        QCMetrics.objects
        .exclude(
            measured_value__gte=F('min_acceptable'),
            measured_value__lte=F('max_acceptable')
        )
        .select_related("test_assignment__parameter", "test_assignment__analyst", "test_assignment__sample__client")
        .values(
            parameter_name=F("test_assignment__parameter__name"),
            analyst_username=F("test_assignment__analyst__username"),
            client_id=F("test_assignment__sample__client__client_id"),
            client_name=F("test_assignment__sample__client__name")
        )
        .distinct()
    )

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
        "failed_qc_info": list(failed_qc_info),
        "qc_chart_data": list(qc_chart_data),
    })



@login_required
def result_review_view(request, sample_id):
    sample = get_object_or_404(Sample, id=sample_id)
    tests = TestAssignment.objects.filter(sample=sample).select_related('parameter', 'testresult', 'qc_metrics')

    if request.method == 'POST':
        # Ensure all tests are complete
        if any(t.status != 'completed' for t in tests):
            messages.error(request, "❌ Not all tests are completed.")
            return redirect('review_panel_grouped_by_client')

        # Final verification
        for test in tests:
            test.status = 'verified'
            test.save(update_fields=['status'])

        sample.status = SampleStatus.APPROVED
        sample.verified_at = timezone.now()
        sample.save(update_fields=['status', 'verified_at'])

        messages.success(request, "✅ Sample verified and approved.")
        return redirect('manager_dashboard')

    return render(request, 'lims/review_results.html', {
        'sample': sample,
        'tests': tests
    })


@login_required
def review_panel_grouped_by_client(request):
    samples = Sample.objects.filter(
        status=SampleStatus.IN_PROGRESS
    ).prefetch_related(
        Prefetch('testassignment_set', queryset=TestAssignment.objects.select_related('parameter', 'testresult', 'qc_metrics'))
    ).select_related('client').order_by('client__name')

    grouped = defaultdict(list)

    for sample in samples:
        test_assignments = sample.testassignment_set.all()

        if not test_assignments.exists():
            continue  # skip samples with no tests

        # Skip samples already verified
        if sample.status == SampleStatus.APPROVED or sample.status == 'results_verified':
            continue

        # Make sure all tests are marked completed before showing for review
        if any(t.status != 'completed' for t in test_assignments):
            continue

        total = test_assignments.count()
        verified = sum(1 for t in test_assignments if t.status == 'verified')
        pending = total - verified

        controls = [t for t in test_assignments if t.is_control]
        qc_pass = sum(1 for c in controls if getattr(c.qc_metrics, "status", None) == "pass")
        qc_fail = sum(1 for c in controls if getattr(c.qc_metrics, "status", None) == "fail")

        sample.review_summary = {
            "total": total,
            "verified": verified,
            "pending": pending,
            "qc_pass": qc_pass,
            "qc_fail": qc_fail,
        }

        grouped[sample.client].append(sample)

    return render(request, 'lims/review_grouped.html', {
        'grouped_samples': grouped
    })
