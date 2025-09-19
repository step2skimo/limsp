from django.http import JsonResponse
from lims.models import QCMetrics
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def qc_metrics_chart_data(request):
    if request.user.groups.filter(name="Manager").exists():
        qcs = QCMetrics.objects.all()
    else:
        qcs = QCMetrics.objects.filter(test_assignment__analyst=request.user)

    data = []
    for qc in qcs:
        analyst = qc.test_assignment.analyst if qc.test_assignment else None

        analyst_name = (
            getattr(analyst, "get_full_name", lambda: None)() or
            getattr(analyst, "username", None) or
            "Unassigned"
        )

        data.append({
            "id": qc.id,
            "measured_value": float(qc.measured_value or 0),
            "min_acceptable": float(qc.min_acceptable or 0),
            "max_acceptable": float(qc.max_acceptable or 0),
            "parameter": getattr(qc.test_assignment.parameter, "name", "Unknown"),
            "sample": getattr(qc.test_assignment.sample, "sample_code", "Unknown"),
            "created_at": qc.created_at.strftime("%Y-%m-%d"),
            "status": qc.status,
            "analyst": analyst_name,
        })

    return JsonResponse(data, safe=False)


@login_required
def qc_dashboard(request):
    return render(request, "lims/qc/qc_dashboard.html")
