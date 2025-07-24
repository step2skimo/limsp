from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from lims.models import *
from django.utils import timezone
from lims.forms import ResultEntryForm, QCMetricsForm
from django.contrib import messages
from lims.forms import ResultEntryForm
from collections import defaultdict, Counter
from django.utils.timezone import now
from datetime import timedelta
from lims.utils.derived import _inject_derived_result
from lims.models import User, ai
from lims.utils.calculations import calculate_nfe_and_me
from django.core.paginator import Paginator
from datetime import datetime
from lims.models import *
from lims.utils.ai_helpers import generate_efficiency_nudge
from lims.models.ai import EfficiencySnapshot
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from datetime import datetime
from django.core.paginator import Paginator
from django.utils.dateparse import parse_date
from collections import defaultdict
from datetime import datetime
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from lims.models import TestResult

User = get_user_model()


@login_required
def analyst_dashboard_view(request):
    assignments = TestAssignment.objects.select_related(
        'sample', 'sample__client', 'parameter'
    ).filter(status__in=['pending', 'rejected'], analyst=request.user)

    grouped = defaultdict(list)
    total_samples, total_controls, overdue_tests = 0, 0, 0
    now_time = now().date()
    one_week_ago = now_time - timedelta(days=7)

    for assignment in assignments:
        client_id = assignment.sample.client.client_id
        key = (client_id, assignment.parameter.name)
        grouped[key].append(assignment)

        if assignment.is_control:
            total_controls += 1
        else:
            total_samples += 1

        received_date = assignment.sample.received_date
        if received_date:
            days_since = (now_time - received_date).days
            assignment.days_since_received = days_since
            if days_since > 3:
                overdue_tests += 1
        else:
            assignment.days_since_received = None

    completed_count = TestAssignment.objects.filter(
        analyst=request.user,
        status='completed',
        testresult__recorded_at__gte=one_week_ago
    ).count()

    total_assigned = total_samples + total_controls
    completed_percent = int((completed_count / total_assigned) * 100) if total_assigned else 0

    # AI Efficiency Snapshot logic
    today = now_time
    this_week_start = today - timedelta(days=today.weekday())
    last_week_start = this_week_start - timedelta(days=7)
    last_week_end = this_week_start - timedelta(days=1)

    snapshots = EfficiencySnapshot.objects.filter(
        week_start=last_week_start,
        week_end=last_week_end
    )

    my_snapshot = snapshots.filter(analyst=request.user).first()
    nudge_message = ""

    if my_snapshot and my_snapshot.average_duration:
        durations = [s.average_duration.total_seconds() for s in snapshots if s.average_duration]
        my_avg = my_snapshot.average_duration.total_seconds()
        faster_than = sum(1 for d in durations if my_avg < d)
        percentile = round((faster_than / len(durations)) * 100) if durations else 0

        try:
            nudge_message = generate_efficiency_nudge(
                request.user.get_short_name() or request.user.username,
                my_avg,
                percentile,
                my_snapshot.total_tests
            )
        except Exception as e:
            nudge_message = f"⚠️ Couldn't generate nudge: {str(e)}"

    context = {
        'grouped_assignments': dict(grouped),
        'stats': {
            'samples': total_samples,
            'controls': total_controls,
            'overdue': overdue_tests,
            'completed_last_7_days': completed_count,
            'completed_percent': completed_percent,
            'total': total_assigned
        },
        'nudge_message': nudge_message,
        'today': today
    }

    return render(request, 'lims/analyst/analyst_dashboard.html', context)





@login_required
def result_history_view(request):
    client_id = request.GET.get('client_id')
    date_from = request.GET.get('from')
    date_to = request.GET.get('to')
    parameter = request.GET.get('parameter')

    results = TestResult.objects.select_related(
        'test_assignment__sample__client',
        'test_assignment__parameter'
    ).filter(recorded_by=request.user)

    if client_id:
        results = results.filter(test_assignment__sample__client__client_id=client_id)

    if parameter:
        results = results.filter(test_assignment__parameter__name__icontains=parameter)

    if date_from:
        results = results.filter(recorded_at__date__gte=datetime.strptime(date_from, "%Y-%m-%d").date())

    if date_to:
        results = results.filter(recorded_at__date__lte=datetime.strptime(date_to, "%Y-%m-%d").date())

    total_results = results.count()
    parameter_totals = Counter()
    grouped = defaultdict(lambda: defaultdict(list))

    # Enrich and group
    for r in results:
        assignment = r.test_assignment
        sample = assignment.sample
        r.sample_code = sample.sample_code
        r.parameter = assignment.parameter.name
        r.client_id = sample.client.client_id
        received = sample.received_date
        r.turnaround_days = (r.recorded_at.date() - received).days if received and r.recorded_at else None
        r.duration = str(r.recorded_at - r.started_at) if r.started_at and r.recorded_at else None

        parameter_totals[r.parameter] += 1
        grouped[r.client_id][r.parameter].append(r)

    client_groups = list(grouped.items())
    paginator = Paginator(client_groups, 3)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'lims/analyst/result_history.html', {
        'page_obj': page_obj,
        'filters': {
            'client_id': client_id or '',
            'from': date_from or '',
            'to': date_to or '',
            'parameter': parameter or '',
        },
        'total_results': total_results,
        'parameter_totals': dict(parameter_totals),
    })





@login_required
def begin_parameter_analysis(request, client_id, parameter_id):
    client = get_object_or_404(Client, client_id=client_id)
    parameter = get_object_or_404(Parameter, id=parameter_id)

    # find samples for this client that are still assigned
    assigned_samples = Sample.objects.filter(
        client=client,
        status=SampleStatus.ASSIGNED,
        testassignment__parameter=parameter
    ).distinct()

    if assigned_samples.exists():
        assigned_samples.update(status=SampleStatus.IN_PROGRESS)
        messages.success(
            request,
            f"✅ Started analysis for parameter '{parameter.name}' on {assigned_samples.count()} samples for client CID-{client.client_id}."
        )
    else:
        messages.warning(
            request,
            f"⚠️ No samples in 'assigned' status for parameter '{parameter.name}' on this client."
        )

    return redirect("analyst_dashboard")



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
        )
        form = None  # No regular form for control samples
    else:
        result_instance = getattr(test, 'testresult', None)
        form = ResultEntryForm(request.POST or None, instance=result_instance)

        # Assign available instruments
        equipment_qs = Equipment.objects.filter(
            parameters_supported=test.parameter,
            is_active=True
        )
        if not equipment_qs.exists():
            equipment_qs = Equipment.objects.filter(is_active=True)

        form.fields['equipment_used'].queryset = equipment_qs
        qc_form = None  # No QC form for normal samples

    if request.method == 'POST':
        form_valid = form.is_valid() if form else True
        qc_valid = qc_form.is_valid() if qc_form else True

        if form_valid and qc_valid:
            # Save result
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

            # Calculate derived results
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

            # Mark test assignment as completed
            test.status = 'completed'
            test.save()

            # 🚦 Update sample status if all its test assignments are now completed
            sample = test.sample
            all_done = sample.testassignment_set.exclude(status='completed').count() == 0
            if all_done and sample.status == SampleStatus.ASSIGNED:
                sample.status = SampleStatus.IN_PROGRESS
                sample.save(update_fields=['status'])

            return redirect('analyst_dashboard')
        else:
            messages.error(request, "❌ Please correct the errors below.")

    return render(request, 'lims/analyst/enter_result.html', {
        'test_assignment': test,
        'form': form if not test.is_control else None,
        'qc_form': qc_form if test.is_control else None,
    })
