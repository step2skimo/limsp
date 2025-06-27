from django.shortcuts import render, get_object_or_404, redirect
from lims.models import *
from django.urls import reverse
import logging
from collections import defaultdict
from django.shortcuts import render, get_object_or_404
from django.shortcuts import render, get_object_or_404
from lims.models import Client, Sample, TestAssignment
from datetime import datetime
from collections import defaultdict
import logging

def client_tracking_view(request, token):
    normalized_token = token.strip().upper()
    logger = logging.getLogger(__name__)
    logger.info(f"Client portal accessed for token: {normalized_token}")

    client = get_object_or_404(Client, token=normalized_token)
    samples = (
        Sample.objects.filter(client=client)
        .exclude(sample_type="QC")
        .prefetch_related(
            "testassignment_set__parameter",
            "testassignment_set__testresult"
        )
        .order_by("-received_date")
    )

    for sample in samples:
        assignments = sample.testassignment_set.all()
        sample.assignments = assignments

        completed = sum(1 for a in assignments if hasattr(a, "testresult") and a.testresult)
        total = len(assignments)
        sample.progress = round((completed / total) * 100) if total > 0 else 0

        latest_result_time = max(
            (a.testresult.recorded_at for a in assignments if hasattr(a, "testresult") and a.testresult and a.testresult.recorded_at),
            default=None
        )
        sample.turnaround = (
            (latest_result_time.date() - sample.received_date).days
            if latest_result_time and sample.received_date else None
        )

    return render(request, "lims/tracking.html", {
        "client": client,
        "samples": samples
    })



def enter_token_view(request):
    if request.method == "POST":
        token = request.POST.get("token", "").strip().upper()
        if token and Client.objects.filter(token=token).exists():
            return redirect("client_tracking", token=token)
        else:
            return render(request, "lims/token_invalid.html", {"token": token})
    return render(request, "lims/token_entry.html")
