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
from collections import defaultdict
from django.contrib import messages



def promote_samples_for_parameter_if_ready(parameter, client):
    samples = client.sample_set.all()
    assignments = TestAssignment.objects.filter(sample__in=samples, parameter=parameter)

    if all(a.status == "completed" for a in assignments):
        for sample in samples:
            if sample.status != SampleStatus.UNDER_REVIEW:
                sample.status = SampleStatus.UNDER_REVIEW
                sample.save(update_fields=["status"])
                print(f"📣 {sample.sample_code} marked as UNDER_REVIEW for parameter {parameter.name}")


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
def review_by_parameter(request, parameter_id):
    parameter = get_object_or_404(Parameter, id=parameter_id)

    # Get only non-QC completed assignments
    assignments = (
        TestAssignment.objects
        .filter(parameter=parameter, status="completed")
        .exclude(sample__sample_type="QC")
        .select_related("sample__client", "testresult", "qc_metrics")
        .order_by("sample__client__client_id", "sample__sample_code")
    )

    # Group assignments by client ID
    grouped = defaultdict(list)
    for assignment in assignments:
        grouped[assignment.sample.client.client_id].append(assignment)

    if request.method == "POST":
        action = request.POST.get("action")
        assignment_id = request.POST.get("assignment_id")
        comment = request.POST.get("comment", "").strip()
        is_bulk = request.POST.get("bulk")

        if is_bulk:
            # 🔁 Bulk Approve or Reject All
            for assignment in assignments:
                sample = assignment.sample
                if action == "approve_all":
                    assignment.status = "verified"
                    assignment.manager_comment = ""
                elif action == "reject_all":
                    assignment.status = "assigned"
                    assignment.manager_comment = "Rejected during bulk review"
                assignment.save(update_fields=["status", "manager_comment"])

                # ✅ Check if all other assignments are verified
                other = sample.testassignment_set.exclude(status="verified")
                if not other.exists():
                    sample.status = SampleStatus.APPROVED
                    sample.verified_at = timezone.now()
                    sample.save(update_fields=["status", "verified_at"])

            messages.success(request, f"✅ Bulk action '{action}' applied.")
            return redirect("review_by_parameter", parameter_id=parameter_id)

        # ✅ Individual Approve / ❌ Reject
        assignment = get_object_or_404(TestAssignment, id=assignment_id)
        sample = assignment.sample

        if action == "approve":
            assignment.status = "verified"
            assignment.manager_comment = ""
            assignment.save(update_fields=["status", "manager_comment"])

            # ✅ Check if all tests for this sample are now verified
            remaining = sample.testassignment_set.exclude(status="verified")
            if not remaining.exists():
                sample.status = SampleStatus.APPROVED
                sample.verified_at = timezone.now()
                sample.save(update_fields=["status", "verified_at"])

            messages.success(request, f"✅ {assignment.sample.sample_code} approved.")

        elif action == "reject":
            assignment.status = "rejected"
            assignment.manager_comment = comment
            assignment.save(update_fields=["status", "manager_comment"])
            messages.warning(request, f"❌ {assignment.sample.sample_code} rejected.")

        else:
            messages.error(request, "❌ Invalid action.")

        return redirect("review_by_parameter", parameter_id=parameter_id)

    return render(request, "lims/review_by_parameter.html", {
        "parameter": parameter,
        "grouped_assignments": dict(grouped),
    })



@login_required
def parameter_review_list(request):
    # Get only test samples with 'completed' status
    completed_assignments = (
        TestAssignment.objects
        .filter(status="completed", is_control=False)
        .select_related("parameter", "sample__client")
    )

    # Group parameters per client
    grouped_parameters = defaultdict(list)

    for ta in completed_assignments:
        client_id = ta.sample.client.client_id
        param = ta.parameter

        # Avoid duplicates per parameter per client
        already_added = any(p.id == param.id for p in grouped_parameters[client_id])
        if not already_added:
            # Count how many assignments this client has for this parameter
            count = sum(
                1 for t in completed_assignments
                if t.parameter.id == param.id and t.sample.client.client_id == client_id
            )
            param.pending_reviews = count
            grouped_parameters[client_id].append(param)

    return render(request, "lims/parameter_review_list.html", {
        "grouped_parameters": dict(grouped_parameters)
    })


