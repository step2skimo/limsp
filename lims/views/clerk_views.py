from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.timezone import now
from datetime import timedelta
from lims.models import Client, Sample, SampleStatus
from django.http import JsonResponse

from django.db.models import Count
from lims.models import Sample
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from lims.models import Sample


@login_required
def clerk_dashboard_view(request):
    if not request.user.is_clerk():
        return redirect("dashboard")

    return render(request, "lims/clerk_dashboard.html")

@login_required
def view_all_clients(request):
    clients = Client.objects.all()
    return render(request, "lims/client_list.html", {"clients": clients})

@login_required
def sample_list(request):
    samples = Sample.objects.select_related("client").order_by("-received_date")
    return render(request, "lims/sample_list.html", {"samples": samples})

@login_required
def search_sample_by_code(request):
    query = request.GET.get("code")
    sample = Sample.objects.filter(sample_code__iexact=query).first()
    return render(request, "lims/sample_search_result.html", {"sample": sample, "query": query})


@login_required
def sample_status_stats(request):
    status_counts = Sample.objects.values("status").annotate(total=Count("id"))

    status_map = dict(SampleStatus.choices)
    for s in status_counts:
        s["label"] = status_map.get(s["status"], s["status"])

    return render(request, "lims/sample_stats.html", {"status_counts": status_counts})

@login_required
def sample_status_json(request):
    status_counts = Sample.objects.values("status").annotate(total=Count("id"))
    status_map = dict(SampleStatus.choices)
    data = {
        "labels": [status_map.get(s["status"], s["status"]) for s in status_counts],
        "counts": [s["total"] for s in status_counts],
    }
    return JsonResponse(data)


@require_GET
def autocomplete_sample_codes(request):
    term = request.GET.get("term", "").strip()
    results = list(
        Sample.objects.filter(sample_code__icontains=term)
        .order_by("sample_code")
        .values_list("sample_code", flat=True)[:10]
    )
    return JsonResponse(results, safe=False)


@login_required
def clerk_activity_summary(request):
    today = now().date()
    start_of_week = today - timedelta(days=today.weekday())  # Monday
    start_of_month = today.replace(day=1)

    clients_today = Client.objects.filter(created__date=today).count()
    clients_week = Client.objects.filter(created__date__gte=start_of_week).count()
    clients_month = Client.objects.filter(created__date__gte=start_of_month).count()

    samples_today = Sample.objects.filter(received_date=today).count()
    samples_week = Sample.objects.filter(received_date__gte=start_of_week).count()
    samples_month = Sample.objects.filter(received_date__gte=start_of_month).count()

    context = {
        "clients_today": clients_today,
        "clients_week": clients_week,
        "clients_month": clients_month,
        "samples_today": samples_today,
        "samples_week": samples_week,
        "samples_month": samples_month,
    }

    return render(request, "lims/clerk_activity_summary.html", context)


