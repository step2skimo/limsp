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

@login_required
@user_passes_test(lambda u: u.is_manager)
def qc_overview_all_parameters(request):
    parameters = Parameter.objects.filter(control_spec__isnull=False)
    return render(request, "lims/qc/manager_qc_overview.html", {
        "parameters": parameters
    })



@login_required
def analyst_qc_dashboard(request):
    parameters = Parameter.objects.filter(control_spec__isnull=False).select_related('control_spec')
    chart_parameters = []

    for param in parameters:
        spec = param.control_spec
        assignments = (
            TestAssignment.objects
            .filter(parameter=param, is_control=True, qc_metrics__isnull=False)
            .select_related('sample', 'qc_metrics', 'analyst')
            .order_by('sample__received_date')
        )

        if not assignments:
            continue

        labels = [a.sample.sample_code for a in assignments]
        values = [a.qc_metrics.measured_value for a in assignments]
        ownership = ["me" if a.analyst == request.user else "other" for a in assignments]

        chart_parameters.append({
            'parameter_id': param.id,
            'name': param.name,
            'labels': labels,
            'values': values,
            'ownership': ownership,
            'min': spec.min_acceptable,
            'max': spec.max_acceptable
        })

    return render(request, "lims/qc/analyst_dashboard.html", {
        "chart_parameters": chart_parameters
    })
