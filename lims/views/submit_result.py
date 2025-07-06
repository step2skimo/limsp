from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from lims.utils.derived import _inject_derived_result
from lims.models import TestAssignment, Equipment, TestResult, QCMetrics, SampleStatus, TestEnvironment
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

    # ✅ Promotion helper: checks all samples for this client+parameter combo
    def promote_samples_for_parameter_if_ready(parameter, client):
        from lims.models import Sample, TestAssignment, SampleStatus
        samples = client.sample_set.all()
        assignments = TestAssignment.objects.filter(sample__in=samples, parameter=parameter)
        if all(a.status == "completed" for a in assignments):
            for s in samples:
                if s.status != SampleStatus.UNDER_REVIEW:
                    s.status = SampleStatus.UNDER_REVIEW
                    s.save(update_fields=["status"])
                    print(f"🔁 Promoted {s.sample_code} to UNDER_REVIEW for {parameter.name}")

    if request.method == "POST":
        form_valid = form.is_valid()
        qc_valid = qc_form.is_valid() if qc_form else True

        temperature = request.POST.get("temperature")
        humidity = request.POST.get("humidity")

        if not temperature or not humidity:
            messages.warning(
                request,
                "⚠️ Please enter both temperature and humidity before submitting results."
            )
            return redirect(request.META.get("HTTP_REFERER", "analyst_dashboard"))

        if not form_valid:
            print("🔍 Test Result Form Errors:", form.errors)

        if test_assignment.is_control and not qc_valid:
            print("🔬 QC Form Errors:", qc_form.errors)

        if form_valid and qc_valid:
            # Save result
            result = form.save(commit=False)
            result.test_assignment = test_assignment
            result.recorded_by = request.user
            result.source = "manual"
            result.recorded_at = result.recorded_at or timezone.now()
            result.save()

            # Environmental metadata
            TestEnvironment.objects.create(
                test_result=result,
                temperature=temperature,
                humidity=humidity
            )

            # Derived results logic
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

            # ✅ Mark assignment as completed
            test_assignment.status = "completed"
            test_assignment.save(update_fields=["status"])

            # ✅ Promote related samples if all assignments for parameter+client are done
            promote_samples_for_parameter_if_ready(parameter, sample.client)

            # Notify lab managers
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
