from django.shortcuts import render, get_object_or_404, redirect
from lims.models import *
from django.urls import reverse
import logging
from collections import defaultdict
from lims.models import Client, Sample, TestAssignment
from datetime import datetime
import logging


def client_tracking_view(request, token):
    normalized_token = token.strip().upper()
    logger = logging.getLogger(__name__)
    logger.info(f"Client portal accessed for token: {normalized_token}")

    # fetch one client to get its organization
    client = get_object_or_404(Client, token=normalized_token)
    organization_name = client.organization

    # get all clients under same organization
    clients = Client.objects.filter(organization=organization_name)

    client_data = []
    for c in clients:
        samples = (
            Sample.objects.filter(client=c)
            .exclude(sample_type="qc")
            .prefetch_related("testassignment_set__parameter")
            .order_by("-received_date")
        )
        for sample in samples:
            assignments = sample.testassignment_set.all()
            sample.assignments = [
                {
                    "parameter": a.parameter.name,
                    "method": a.parameter.method,
                    "unit": a.parameter.unit,
                }
                for a in assignments
            ]
            completed = sample.testassignment_set.filter(testresult__isnull=False).count()
            total = sample.testassignment_set.count()
            sample.progress = round((completed / total) * 100) if total > 0 else 0
            latest_result_time = sample.testassignment_set.aggregate(
                latest=models.Max("testresult__recorded_at")
            )["latest"]
            sample.turnaround = (
                (latest_result_time.date() - sample.received_date).days
                if latest_result_time and sample.received_date
                else None
            )
        client_data.append({
            "client": c,
            "samples": samples,
        })

    return render(request, "lims/client/tracking.html", {
        "client_data": client_data,
        "organization": organization_name,
    })



def enter_token_view(request):
    if request.method == "POST":
        token = request.POST.get("token", "").strip().upper()
        if token and Client.objects.filter(token=token).exists():
            return redirect("client_tracking", token=token)
        else:
            return render(request, "lims/token_invalid.html", {"token": token})
    return render(request, "lims/client/token_entry.html")
