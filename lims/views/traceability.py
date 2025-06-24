from django.shortcuts import render, get_object_or_404
from lims.models import Equipment, TestEnvironment
from django.contrib.auth.decorators import login_required

@login_required
def equipment_usage_view(request, equipment_id):
    equipment = get_object_or_404(Equipment, id=equipment_id)

    usage_records = TestEnvironment.objects.select_related('test_assignment__sample', 'recorded_by') \
        .filter(instrument_id=equipment.id) \
        .order_by('-recorded_at')

    return render(request, 'lims/equipment_usage.html', {
        'equipment': equipment,
        'usage_records': usage_records
    })
