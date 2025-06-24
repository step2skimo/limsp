from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from lims.models import TestAssignment, Equipment, TestResult, QCMetrics
from lims.forms import ResultEntryForm, QCMetricsForm



@login_required
def enter_result(request, assignment_id):
    test_assignment = get_object_or_404(TestAssignment, id=assignment_id)
    sample = test_assignment.sample
    parameter = test_assignment.parameter

    equipment_qs = Equipment.objects.filter(parameters_supported=parameter, is_active=True)

    try:
        result_instance = test_assignment.testresult
    except TestResult.DoesNotExist:
        result_instance = None

    form = ResultEntryForm(request.POST or None, instance=result_instance)
    form.fields['equipment_used'].queryset = equipment_qs

    qc_form = None
    if test_assignment.is_control:
        qc_instance = getattr(test_assignment, "qc_metrics", None)
        qc_form = QCMetricsForm(request.POST or None, instance=qc_instance)

    if request.method == "POST":
        form_valid = form.is_valid()
        qc_valid = qc_form.is_valid() if qc_form else True

        if form_valid and qc_valid:
            result = form.save(commit=False)
            result.test_assignment = test_assignment
            result.recorded_by = request.user
            result.source = "manual"
            result.recorded_at = result.recorded_at or timezone.now()
            result.save()

            # Derived values
            results = TestResult.objects.filter(test_assignment__sample=sample)
            result_dict = {
                r.test_assignment.parameter.name: float(r.value)
                for r in results if r.value is not None
            }
            nfe, me = calculate_nfe_and_me(result_dict)
            if nfe is not None:
                _inject_derived_result("Carbohydrate", nfe, sample)
            if me is not None:
                _inject_derived_result("ME", me, sample)

            if test_assignment.is_control and qc_form:
                qc_metrics = qc_form.save(commit=False)
                qc_metrics.test_assignment = test_assignment
                qc_metrics.save()

                if qc_metrics.status == "pass":
                    messages.success(request, f"✅ QC Result Passed for {parameter.name}")
                elif qc_metrics.status == "fail":
                    messages.error(request, f"❌ QC Result Failed for {parameter.name}")

            messages.success(request, "✅ Result submitted successfully.")
            return redirect("lims:result_success", assignment_id=test_assignment.id)

        else:
            messages.error(request, "❌ Please correct the errors below.")

    return render(request, "lims/enter_result.html", {
        "form": form,
        "qc_form": qc_form,
        "test_assignment": test_assignment,
        "equipment_list": equipment_qs,
    })





@login_required
def result_success(request, assignment_id):
    test_assignment = get_object_or_404(TestAssignment, id=assignment_id)
    context = {
        "test_assignment": test_assignment,
    }
    return render(request, "lims/result_success.html", context)
