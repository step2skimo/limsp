from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from lims.models import TestAssignment, TestResult, TestEnvironment, Equipment, ControlSpec
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from collections import defaultdict
from lims.forms import ResultEntryForm, QCMetricsForm
from django.contrib import messages
from lims.forms import ResultEntryForm
from ..services.calculators import calculate_nfe_and_me
from collections import defaultdict
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from lims.models import TestAssignment
from django.utils.timezone import now
from datetime import timedelta

from django.utils.timezone import now
from datetime import timedelta
from collections import defaultdict

@login_required
def analyst_dashboard_view(request):
    assignments = TestAssignment.objects.select_related(
        'sample', 'sample__client', 'parameter'
    ).filter(status='pending', analyst=request.user)

    grouped = defaultdict(list)
    total_samples = 0
    total_controls = 0
    overdue_tests = 0
    now_time = now().date()
    one_week_ago = now_time - timedelta(days=7)

    for assignment in assignments:
        grouped[assignment.parameter.name].append(assignment)

        if assignment.is_control:
            total_controls += 1
        else:
            total_samples += 1

        if assignment.sample.received_date and (now_time - assignment.sample.received_date).days > 3:
            overdue_tests += 1

    completed_count = TestAssignment.objects.filter(
        analyst=request.user,
        status='completed',
        testresult__recorded_at__gte=one_week_ago
    ).count()

    return render(request, 'lims/analyst_dashboard.html', {
        'grouped_assignments': dict(grouped),
        'stats': {
            'samples': total_samples,
            'controls': total_controls,
            'overdue': overdue_tests,
            'completed_last_7_days': completed_count
        }
    })


@login_required
def enter_result_view(request, assignment_id):
    test = get_object_or_404(TestAssignment, pk=assignment_id)

    if test.is_control:
        qc_instance = getattr(test, 'qc_metrics', None)
        qc_initial = {}

        if hasattr(test.parameter, 'control_spec'):
            spec = test.parameter.control_spec
            qc_initial = {
                'min_acceptable': spec.min_acceptable,
                'max_acceptable': spec.max_acceptable
            }

        qc_form = QCMetricsForm(
            request.POST or None,
            instance=qc_instance,
            test_assignment=test,
            initial=qc_initial
        )
        form = None  # Skip sample form for control assignments

    else:
        result_instance = getattr(test, 'testresult', None)
        form = ResultEntryForm(request.POST or None, instance=result_instance)

        # Smart fallback: use default equipment or all active if none found
        equipment_qs = Equipment.objects.filter(
            parameters_supported=test.parameter,
            is_active=True
        )

        if not equipment_qs.exists():
            equipment_qs = Equipment.objects.filter(is_active=True)

        form.fields['equipment_used'].queryset = equipment_qs
        qc_form = None  # Skip QC form for normal samples

    if request.method == 'POST':
        form_valid = form.is_valid() if form else True
        qc_valid = qc_form.is_valid() if qc_form else True

        if form_valid and qc_valid:
            # Save sample result
            if form:
                result = form.save(commit=False)
                result.test_assignment = test
                result.recorded_by = request.user
                result.recorded_at = result.recorded_at or timezone.now()
                result.source = 'manual'
                result.save()

                TestEnvironment.objects.update_or_create(
                    test_assignment=test,
                    defaults={
                        'temperature': form.cleaned_data.get('temp'),
                        'humidity': form.cleaned_data.get('humidity'),
                        'pressure': form.cleaned_data.get('pressure'),
                        'instrument': form.cleaned_data.get('equipment_used'),
                        'recorded_by': request.user,
                    }
                )

                messages.success(request, "✅ Result submitted successfully.")

            # Save QC metrics
            if qc_form:
                qc = qc_form.save(commit=False)
                qc.test_assignment = test
                qc.save()

                if qc.status == 'pass':
                    messages.success(request, f"✅ QC PASSED for {test.parameter.name}")
                else:
                    messages.error(request, f"❌ QC FAILED for {test.parameter.name}")

            # Auto-calculate derived metrics for normal samples
            if not test.is_control:
                sample = test.sample
                results = TestResult.objects.filter(test_assignment__sample=sample)
                result_dict = {
                    r.test_assignment.parameter.name: float(r.value)
                    for r in results if r.value is not None
                }
                nfe, me = calculate_nfe_and_me(result_dict)
                if nfe is not None:
                    _inject_derived_result("Carbohydrate", nfe, sample, recorded_by=request.user)
                if me is not None:
                    _inject_derived_result("ME", me, sample, recorded_by=request.user)

            test.status = 'completed'
            test.save()
            return redirect('analyst_dashboard')
        else:
            messages.error(request, "❌ Please correct the errors below.")

    print(f"DEBUG: is_control = {test.is_control} | type = {type(test.is_control)}")

    return render(request, 'lims/enter_result.html', {
        'test_assignment': test,
        'form': form if not test.is_control else None,
        'qc_form': qc_form if test.is_control else None,
    })
