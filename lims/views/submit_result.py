from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from lims.utils.derived import _inject_derived_result
from lims.models import TestAssignment, Equipment, TestResult, QCMetrics, SampleStatus, TestEnvironment, Client, Parameter
from lims.forms import ResultEntryForm, QCMetricsForm, TestEnvironmentForm
from django.contrib.auth import get_user_model
from lims.utils.notifications import notify_lab_manager_on_submission
from django.contrib.auth.models import User
from django.forms import modelform_factory
from django import forms
from django.db import transaction
from django.utils.timezone import now as timezone_now
User = get_user_model()


""" @login_required
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

    def promote_and_notify_if_all_submitted(parameter, client, analyst_name):
        assignments = TestAssignment.objects.filter(
            sample__client=client,
            parameter=parameter
        )
        if all(a.status == "completed" for a in assignments):
            samples = client.sample_set.all()
            for s in samples:
                if s.status != SampleStatus.UNDER_REVIEW:
                    s.status = SampleStatus.UNDER_REVIEW
                    s.save(update_fields=["status"])
                    print(f"🔁 Promoted {s.sample_code} to UNDER_REVIEW for {parameter.name}")

            managers = User.objects.filter(groups__name="Manager", is_active=True)
            for manager in managers:
                notify(
                    manager,
                    f"Hi {manager.first_name}, all results for Client ID CID-{client.client_id} "
                    f"({parameter.name}) have been submitted by Analyst {analyst_name}."
                )
                notify_manager_on_result_submission(
                    manager.email,
                    analyst_name,
                    client.client_id,
                    parameter.name
                )

    if request.method == "POST":
        form_valid = form.is_valid()
        qc_valid = qc_form.is_valid() if qc_form else True

        temperature = request.POST.get("temperature")
        humidity = request.POST.get("humidity")

        analyst_name = request.user.get_full_name()
        client = sample.client
        client_id = client.client_id
        param_name = parameter.name

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
            # Save the result
            result = form.save(commit=False)
            result.test_assignment = test_assignment
            result.recorded_by = request.user
            result.source = "manual"
            result.recorded_at = result.recorded_at or timezone.now()
            result.save()

            # Save environmental data
            TestEnvironment.objects.create(
                test_result=result,
                temperature=temperature,
                humidity=humidity
            )

            # Save QC metrics if applicable
            if test_assignment.is_control and qc_form:
                qc_metrics = qc_form.save(commit=False)
                qc_metrics.test_assignment = test_assignment
                qc_metrics.save()

            # Mark assignment as completed
            test_assignment.status = "completed"
            test_assignment.save(update_fields=["status"])

            # Promote + notify if all related assignments are completed
            promote_and_notify_if_all_submitted(parameter, client, analyst_name)

            messages.success(request, "✅ Result submitted successfully.")
            return redirect("result_success", assignment_id=test_assignment.id)

        else:
            messages.error(request, "❌ Please correct the errors below.")

    return render(request, "lims/enter_result.html", {
        "form": form,
        "qc_form": qc_form,
        "test_assignment": test_assignment,
        "equipment_list": equipment_qs,
    }) """


@login_required
def enter_batch_result(request, client_id, parameter_id):
    assignments = TestAssignment.objects.filter(
        sample__client__client_id=client_id,
        parameter_id=parameter_id
    ).select_related('sample', 'parameter')

    if not assignments.exists():
        messages.error(request, "❌ No assignments found for this client and parameter.")
        return redirect("analyst_dashboard")

    parameter = assignments[0].parameter
    client = assignments[0].sample.client

    # Split control and test samples
    control_assignment = next((a for a in assignments if a.is_control), None)
    test_assignments = [a for a in assignments if not a.is_control]

    # Result form for each test assignment
    ResultForm = modelform_factory(TestResult, fields=['value'])
    result_forms = []
    for assignment in test_assignments:
        instance = getattr(assignment, "testresult", None)
        prefix = f"result_{assignment.id}"
        form = ResultForm(request.POST or None, instance=instance, prefix=prefix)
        result_forms.append((assignment, form))

    # QC form
    qc_form = None
    if control_assignment:
        qc_instance = getattr(control_assignment, "qc_metrics", None)
        qc_form = QCMetricsForm(
            request.POST or None,
            instance=qc_instance,
            test_assignment=control_assignment
        )

    # Environment form
    env_form = TestEnvironmentForm(request.POST or None)

    def promote_if_complete(client, parameter, analyst_name):
        incomplete = TestAssignment.objects.filter(
            sample__client=client,
            parameter=parameter
        ).exclude(status="completed")
        if not incomplete.exists():
            for sample in client.sample_set.all():
                if sample.status != "under_review":
                    sample.status = "under_review"
                    sample.save(update_fields=["status"])
            managers = User.objects.filter(groups__name="Manager", is_active=True)
            for manager in managers:
                notify_manager_on_result_submission(manager.email, analyst_name, client.client_id, parameter.name)

    if request.method == "POST":
        all_valid = all(form.is_valid() for _, form in result_forms)
        qc_valid = qc_form.is_valid() if qc_form else True
        env_valid = env_form.is_valid()

        if not env_valid:
            print("🛑 Environment Form Errors:", env_form.errors)
            messages.error(request, "❌ Please correct environment input errors.")

        if not all_valid:
            for assignment, form in result_forms:
                if not form.is_valid():
                    print(f"🛑 Result Form Error for {assignment.sample.sample_code}:", form.errors)

        if qc_form and not qc_valid:
            print("🛑 QC Form Errors:", qc_form.errors)

        if env_valid and all_valid and qc_valid:
            with transaction.atomic():
                env_data = env_form.save(commit=False)

                for assignment, form in result_forms:
                    result = form.save(commit=False)
                    result.test_assignment = assignment
                    result.recorded_by = request.user
                    result.source = "manual"
                    result.recorded_at = timezone_now()
                    result.save()

                    env_obj, created = TestEnvironment.objects.update_or_create(
                        test_assignment=assignment,
                        defaults={
                            "temperature": env_data.temperature,
                            "humidity": env_data.humidity,
                            "pressure": env_data.pressure,
                            "instrument": env_data.instrument,
                            "recorded_by": request.user,
                            }
                        )


                    assignment.status = "completed"
                    assignment.equipment_used = env_data.instrument
                    assignment.save()

                if qc_form and control_assignment:
                    qc = qc_form.save(commit=False)
                    qc.test_assignment = control_assignment
                    qc.save()
                    control_assignment.status = "completed"
                    control_assignment.save()

                promote_if_complete(client, parameter, request.user.get_full_name())
                messages.success(request, "✅ Batch result submitted successfully.")
                return redirect("result_success_batch", client_id=client.client_id, parameter_id=parameter.id)


        else:
            messages.error(request, "❌ Please correct the errors below.")

    context = {
        "parameter": parameter,
        "client": client,
        "result_forms": result_forms,
        "qc_form": qc_form,
        "control_assignment": control_assignment,
        "equipment_qs": Equipment.objects.filter(parameters_supported=parameter, is_active=True),
        "env_form": env_form,
    }

    return render(request, "lims/batch_result_entry.html", context)


@login_required
def batch_result_success(request, client_id, parameter_id):
    client = get_object_or_404(Client, client_id=client_id)
    parameter = get_object_or_404(Parameter, id=parameter_id)
    return render(request, "lims/batch_result_success.html", {
        "client": client,
        "parameter": parameter,
    })
