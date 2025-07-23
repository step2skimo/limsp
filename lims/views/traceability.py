from django.shortcuts import render, get_object_or_404
from lims.models import Equipment, TestEnvironment
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.db.models import Min, Max

@login_required
def equipment_usage_view(request, equipment_id):
    equipment = get_object_or_404(Equipment, id=equipment_id)

    # Group TestEnvironment by client + parameter
    usage_records = (
        TestEnvironment.objects
        .filter(instrument_id=equipment.id)
        .select_related('test_assignment__sample__client', 'test_assignment__parameter')
        .values(
            'test_assignment__sample__client__client_id',
            'test_assignment__sample__client__name',
            'test_assignment__parameter__id',
            'test_assignment__parameter__name'
        )
        .annotate(
            first_used=Min('recorded_at'),
            last_used=Max('recorded_at'),
            total_samples=Count('test_assignment', distinct=True),
        )
        .order_by('-last_used')
    )

    return render(request, 'lims/equipment_usage_batch.html', {
        'equipment': equipment,
        'usage_records': usage_records
    })

