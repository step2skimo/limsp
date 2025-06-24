from django.contrib.auth.decorators import login_required, user_passes_test
from lims.models import TestAssignment
from django.shortcuts import render
from collections import defaultdict

from collections import defaultdict
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from lims.models import TestAssignment

@login_required
@user_passes_test(lambda u: u.is_manager)
def test_assignment_list(request):
    # Prefetch related objects for performance
    assignments = TestAssignment.objects.select_related(
        "sample__client", "parameter", "analyst"
    ).order_by("sample__client__client_id")

    grouped_assignments = defaultdict(list)

    for assignment in assignments:
        client = assignment.sample.client
        if client and client.client_id:  # Ensure client and client_id exist
            grouped_assignments[client.client_id].append(assignment)

    # Convert defaultdict to regular dict for template compatibility
    return render(request, "lims/manager/test_assignments.html", {
        "grouped_assignments": dict(grouped_assignments)
    })
