from django.shortcuts import render, get_object_or_404, redirect
from lims.models import Client, Sample  
from django.urls import reverse

def client_tracking_view(request, token):
    client = get_object_or_404(Client, token=token)
    samples = Sample.objects.filter(client=client).order_by("-received_date")
    return render(request, "lims/tracking.html", {"client": client, "samples": samples})


def enter_token_view(request):
    if request.method == "POST":
        token = request.POST.get("token")
        if token:
            return redirect("client_tracking", token=token)
    return render(request, "lims/token_entry.html")


