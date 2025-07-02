from django.contrib.auth.decorators import login_required, user_passes_test
from lims.models import TestAssignment
from django.shortcuts import render
from collections import defaultdict

from collections import defaultdict
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from lims.models import TestAssignment

from collections import defaultdict
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render

@login_required
@user_passes_test(lambda u: u.is_manager)
def test_assignment_list(request):
    assignments = TestAssignment.objects.select_related(
        "sample__client", "parameter", "analyst"
    ).order_by("-sample__received_date")  

    grouped_assignments = defaultdict(list)

    # group assignments by client_id
    for assignment in assignments:
        client = assignment.sample.client
        if client and client.client_id:
            grouped_assignments[client.client_id].append(assignment)

    grouped_data = {}
    for client_id, client_assignments in grouped_assignments.items():
        completed = [a for a in client_assignments if a.status == "completed"]
        grouped_data[client_id] = {
            "assignments": client_assignments,
            "completed_count": len(completed),
            "total_count": len(client_assignments),
        }

    return render(request, "lims/manager/test_assignments.html", {
        "grouped_assignments": grouped_data
    })

