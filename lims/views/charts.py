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
        data.append({
            "id": qc.id,
            "measured_value": float(qc.measured_value or 0),
            "min_acceptable": float(qc.min_acceptable or 0),
            "max_acceptable": float(qc.max_acceptable or 0),
            "parameter": qc.test_assignment.parameter.name,
            "sample": qc.test_assignment.sample.sample_code,
            "created_at": qc.created_at.strftime("%Y-%m-%d"),
            "status": qc.status,
            "analyst": qc.test_assignment.analyst.get_full_name() or qc.test_assignment.analyst.username
        })

    return JsonResponse(data, safe=False)

@login_required
def qc_dashboard(request):
    return render(request, "lims/qc/qc_dashboard.html")
