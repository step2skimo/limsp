from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from lims.utils.derived import _inject_derived_result
from lims.models import TestAssignment, Equipment, TestResult, QCMetrics
from lims.forms import ResultEntryForm, QCMetricsForm
from django.contrib.auth import get_user_model
from notifications.utils import notify  

User = get_user_model()


@login_required
def enter_result(request, assignment_id):
    test_assignment = get_object_or_404(TestAssignment, id=assignment_id)
    sample = test_assignment.sample
    parameter = test_assignment.parameter
    equipment_qs = Equipment.objects.filter(parameters_supported=parameter, is_active=True)

    result_instance = getattr(test_assignment, "testresult", None)
    form = ResultEntryForm(request.POST or None, instance=result_instance)
    form.fields['equipment_used'].queryset = equipment_qs

    qc_form = None
    if test_assignment.is_control:
        qc_instance = getattr(test_assignment, "qc_metrics", None)
        qc_form = QCMetricsForm(
            request.POST or None,
            instance=qc_instance,
            test_assignment=test_assignment
        )

    if request.method == "POST":
        form_valid = form.is_valid()
        qc_valid = qc_form.is_valid() if qc_form else True

        if not form_valid:
            print("🔍 Test Result Form Errors:", form.errors)

        if test_assignment.is_control and not qc_valid:
            print("🔬 QC Form Errors:", qc_form.errors)
            print("Non-field Errors:", qc_form.non_field_errors())
            print("Measured Value:", qc_form.cleaned_data.get("measured_value", None))

        if form_valid and qc_valid:
            result = form.save(commit=False)
            result.test_assignment = test_assignment
            result.recorded_by = request.user
            result.source = "manual"
            result.recorded_at = result.recorded_at or timezone.now()
            result.save()

            # Derived calculations
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

            # QC handling
            if test_assignment.is_control and qc_form:
                qc_metrics = qc_form.save(commit=False)
                qc_metrics.test_assignment = test_assignment
                qc_metrics.save()

                # mark QC assignment as completed
                test_assignment.status = "completed"
                test_assignment.save(update_fields=["status"])

                status = qc_metrics.status
                if status == "pass":
                    messages.success(request, f"✅ QC Passed for {parameter.name}")
                elif status == "fail":
                    messages.warning(request, f"❌ QC Failed for {parameter.name}")
                else:
                    messages.info(request, f"ℹ️ QC status undetermined for {parameter.name}")

            # mark non-QC assignment as completed
            if not test_assignment.is_control:
                test_assignment.status = "completed"
                test_assignment.save(update_fields=["status"])

            # ✅ NEW: mark sample SUBMITTED if all assignments are completed
            all_assignments = sample.testassignment_set.all()
            if all(a.status == "completed" for a in all_assignments):
                sample.status = SampleStatus.UNDER_REVIEW
                sample.save(update_fields=["status"])

            # Notify managers
            analyst_name = request.user.get_full_name()
            client_id = getattr(sample.client, 'client_id', '—')
            param_name = parameter.name
            managers = User.objects.filter(groups__name="Manager")
            for manager in managers:
                notify(
                    manager,
                    f"Hi {manager.first_name}, results were submitted by Analyst {analyst_name} "
                    f"for Client ID CID-{client_id}. Parameter: {param_name}."
                )

            messages.success(request, "✅ Result submitted successfully.")
            return redirect("result_success", assignment_id=test_assignment.id)

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
