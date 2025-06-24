from django.shortcuts import render, get_object_or_404
from lims.forms import QCMetricsForm
from lims.models import Parameter, QCMetrics
from django.contrib.auth.decorators import login_required
from lims.models import TestAssignment
from django.http import JsonResponse
from django.contrib.auth.decorators import user_passes_test
from lims.models import QCMetrics, ControlSpec
from django.core.serializers.json import DjangoJSONEncoder
import json


from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from lims.models import TestAssignment
from collections import defaultdict


def qc_chart_data(request, parameter_id):
    param = Parameter.objects.get(id=parameter_id)
    qcs = QCMetrics.objects.filter(test_assignment__parameter=param).order_by('test_assignment__sample__created_at')

    data = {
        "name": param.name,
        "unit": param.unit,
        "labels": [qc.test_assignment.sample.created_at.strftime('%Y-%m-%d') for qc in qcs],
        "data": [float(qc.measured_value) for qc in qcs],
        "min_y": float(param.control_spec.min_acceptable),
        "max_y": float(param.control_spec.max_acceptable),
    }
    return JsonResponse(data)



def qc_chart(request, parameter_id):
    param = Parameter.objects.get(id=parameter_id)
    qcs = QCMetrics.objects.filter(test_assignment__parameter=param).order_by('test_assignment__sample__created_at')

    x = [qc.test_assignment.sample.created_at.strftime('%Y-%m-%d') for qc in qcs]
    y = [float(qc.measured_value) for qc in qcs]
    min_y = param.control_spec.min_acceptable
    max_y = param.control_spec.max_acceptable

    return render(request, "lims/qc_chart.html", {
        'labels': x,
        'data': y,
        'min_y': float(min_y),
        'max_y': float(max_y),
        'parameter': param
    })

 

@login_required
@user_passes_test(lambda u: u.is_manager)
def qc_overview_all_parameters(request):
    parameters = Parameter.objects.filter(name__in=["Protein", "Fat", "Moisture", "Ash", "Fiber"])
    return render(request, "lims/qc/manager_qc_overview.html", {"parameters": parameters})


@login_required
def analyst_qc_dashboard(request):
    # Pull all parameters that have control specs defined
    parameters = Parameter.objects.filter(control_spec__isnull=False).select_related('control_spec')

    chart_parameters = []

    for param in parameters:
        spec = param.control_spec

        # Get any control test assignments by this analyst for this parameter
        assignments = TestAssignment.objects.filter(
            parameter=param,
            analyst=request.user,
            is_control=True,
            qc_metrics__isnull=False
        ).select_related('sample', 'qc_metrics')

        labels = []
        values = []

        for a in assignments:
            labels.append(a.sample.sample_code)
            values.append(a.qc_metrics.measured_value)

        chart_parameters.append({
            'parameter_id': param.id,
            'name': param.name,
            'labels': labels,
            'values': values,
            'min': spec.min_acceptable,
            'max': spec.max_acceptable
        })

    return render(request, "lims/qc/analyst_dashboard.html", {
        "chart_parameters": chart_parameters
    })
