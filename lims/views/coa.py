import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from django.http import FileResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from lims.models import Sample, TestResult
from lims.utils.calculations import calculate_cho_and_me
from lims.utils.coa_summary_ai import generate_dynamic_summary
from datetime import datetime

import io, os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from pdfrw import PdfReader, PdfWriter, PageMerge
from django.http import HttpResponse
from django.conf import settings

from lims.models import Sample
from lims.utils.calculations import calculate_cho_and_me
from lims.utils.coa_summary_ai import generate_dynamic_summary

import io, os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from pdfrw import PdfReader, PdfWriter, PageMerge
from django.http import HttpResponse
from django.conf import settings
import datetime
from django.shortcuts import redirect
from lims.models import Sample, SampleStatus
from lims.utils.calculations import calculate_cho_and_me
from lims.utils.coa_summary_ai import generate_dynamic_summary
from django.shortcuts import render
from lims.models import Client, Sample
from collections import defaultdict
from django.http import HttpResponse
from weasyprint import HTML
import datetime
from django.shortcuts import get_object_or_404

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML
import datetime
from django.templatetags.static import static
from collections import defaultdict
import logging
import os
from django.conf import settings
from django.contrib import messages
from lims.utils.notifications import notify_client_on_coa_release
from lims.forms import COAInterpretationForm
from lims.models.coa import COAInterpretation
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
import re

logger = logging.getLogger(__name__)



def clean_method(method_str):
    """
    Extracts only the AOAC reference from a full method string.
    E.g., from 'Kjedahl (AOAC 984.13 2000)' it returns 'AOAC 984.13'
    """
    match = re.search(r"(AOAC\s+\d{3,4}\.\d{1,2})", method_str, re.IGNORECASE)
    return match.group(1) if match else method_str


@login_required
def generate_coa_pdf(request, client_id):
    samples = (
        Sample.objects
        .exclude(sample_code__startswith="QC-")
        .filter(client__client_id=client_id)
        .prefetch_related(
            "testassignment_set__parameter",
            "testassignment_set__testresult",
            "testassignment_set__testenvironment",
        )
    )

    if not samples.exists():
        return HttpResponse("No samples found for this client.", status=404)

    client = samples.first().client
    parameters = set()
    grouped_summary = defaultdict(lambda: {"sample_type": "", "results": defaultdict(list)})

    for sample in samples:
        sample.results = []
        param_values = {}
        sample_environment = None
        sample_type = sample.sample_type or "Unknown"

        for ta in sample.testassignment_set.all():
            res = getattr(ta, "testresult", None)
            param_name = ta.parameter.name

            if res:
                value = res.value
                param_values[param_name.lower()] = value

                sample.results.append({
                    "parameter": param_name,
                    "method": ta.parameter.method,
                    "value": value,
                    "unit": ta.parameter.unit,
                })

                grouped_summary[sample_type]["sample_type"] = sample_type
                grouped_summary[sample_type]["results"][param_name].append(value)
                parameters.add((param_name, ta.parameter.unit, ta.parameter.method))

            env = getattr(ta, "testenvironment", None)
            if env and not sample_environment:
                sample_environment = f"{env.temperature}°C, {env.humidity}%RH"

        # CHO & ME (kcal/kg)
        calc_map = {"protein": "protein", "crude fat": "fat", "ash": "ash", "moisture": "moisture", "crude fibre": "fiber"}
        mapped_values = {alias: param_values[key] for key, alias in calc_map.items() if key in param_values}

        if all(alias in mapped_values for alias in ["protein", "fat", "ash", "moisture", "fiber"]):
            cho = round(100 - sum(mapped_values[k] for k in ["protein", "fat", "ash", "moisture", "fiber"]), 2)
            me = round(((mapped_values["protein"] * 4) + (mapped_values["fat"] * 9) + (cho * 4)) * 10, 2)

            sample.results.append({"parameter": "CHO", "method": "AOAC by difference", "value": cho, "unit": "%"})
            sample.results.append({"parameter": "ME", "method": "Calculated using Atwater factors", "value": me, "unit": "kcal/kg"})

            grouped_summary[sample_type]["results"]["CHO"].append(cho)
            grouped_summary[sample_type]["results"]["ME"].append(me)
            parameters.add(("CHO", "%", "AOAC by difference"))
            parameters.add(("ME", "kcal/kg", ""))

        sample.environment = sample_environment or "Ambient 25°C 50%RH"

    parameters = sorted(parameters)

    # Summary text
    interpretation = COAInterpretation.objects.filter(client=client).first()
    summary_text = interpretation.summary_text if interpretation else "Summary not available."

    # Sample weight display
    weights = [s.weight for s in samples if s.weight is not None]
    if len(weights) == 1:
        sample_weight_display = f"{weights[0]} g"
    elif weights:
        sample_weight_display = f"{min(weights)} g – {max(weights)} g"
    else:
        sample_weight_display = "N/A"

    # Paths for images
    letterhead_path = os.path.join(settings.STATIC_ROOT, "letterheads", "coa_letterhead.png")
    signature1_path = os.path.join(settings.STATIC_ROOT, "images/signatures/hannah-sign.png")
    signature2_path = os.path.join(settings.STATIC_ROOT, "images/signatures/julius-sign.png")

    # Convert to file:// URLs
    letterhead_url = f"file://{letterhead_path}"
    signature_1 = f"file://{signature1_path}"
    signature_2 = f"file://{signature2_path}"

    # Render HTML
    html = render_to_string("lims/coa_template.html", {
        "client": client,
        "samples": samples,
        "sample_weight_display": sample_weight_display,
        "summary_text": summary_text,
        "parameters": [{"name": p[0], "unit": p[1], "method": clean_method(p[2])} for p in parameters],
        "today": datetime.date.today(),
        "letterhead_url": letterhead_url,
        "signature_1": signature_1,
        "signature_2": signature_2,
    })

    # Generate PDF
    pdf_file = HTML(string=html, base_url=settings.STATIC_ROOT).write_pdf()
    return HttpResponse(pdf_file, content_type="application/pdf")


@login_required
def edit_summary(request, client_id):
    client = get_object_or_404(Client, client_id=client_id)
    interpretation, created = COAInterpretation.objects.get_or_create(client=client)

    if request.method == 'POST':
        form = COAInterpretationForm(request.POST, instance=interpretation)
        if form.is_valid():
            form.save()

            # ✅ Confirm the summary so COA can be released
            client.summary_confirmed = True
            client.save()

            messages.success(request, "Summary updated and confirmed successfully.")
            return redirect('preview_coa', client_id=client_id)
    else:
        form = COAInterpretationForm(instance=interpretation)

    return render(request, "lims/edit_summary.html", {
        "client": client,
        "form": form,
    })


@login_required
def coa_dashboard(request):
    # get ALL samples except QC samples
    samples = (
        Sample.objects
        .exclude(sample_type="qc")
        .select_related("client")
        .order_by("-client__client_id", "-received_date")
    )

    # group them by client and check if they have approved samples
    grouped = defaultdict(lambda: {"samples": [], "has_approved": False})

    for sample in samples:
        client_entry = grouped[sample.client]
        client_entry["samples"].append(sample)
        if sample.status == SampleStatus.APPROVED:
            client_entry["has_approved"] = True

    context = {
        "grouped": dict(grouped),
    }
    return render(request, "lims/coa_dashboard.html", context)


@login_required
def release_client_coa(request, client_id):
    print("✅ Release view triggered.")

    if request.method != "POST":
        return HttpResponse("❌ Not a POST request", status=405)

    client = get_object_or_404(Client, id=client_id)

    # ✅ Fetch interpretation summary
    interpretation = COAInterpretation.objects.filter(client=client).first()
    summary_text = interpretation.summary_text if interpretation else "Summary not available"

    samples = (
        Sample.objects
        .exclude(sample_code__startswith="QC-")
        .filter(client=client)
        .prefetch_related(
            "testassignment_set__parameter",
            "testassignment_set__testresult",
            "testassignment_set__testenvironment"
        )
    )

    parameters = set()

    for sample in samples:
        sample.results = []
        param_values = {}

        for ta in sample.testassignment_set.all():
            res = getattr(ta, "testresult", None)
            if res:
                value = res.value
                param_values[ta.parameter.name.lower()] = value
                parameters.add((ta.parameter.name, ta.parameter.unit, ta.parameter.method))

                sample.results.append({
                    "parameter": ta.parameter.name,
                    "method": ta.parameter.method,
                    "value": value,
                    "unit": ta.parameter.unit,
                })

        # ✅ Calculate CHO & ME
        calc_map = {
            "protein": "protein",
            "crude fat": "fat",
            "ash": "ash",
            "moisture": "moisture",
            "crude fibre": "fiber",
        }

        mapped_values = {alias: param_values[key] for key, alias in calc_map.items() if key in param_values}

        if all(k in mapped_values for k in ["protein", "fat", "ash", "moisture", "fiber"]):
            cho = round(100 - sum(mapped_values[k] for k in ["protein", "fat", "ash", "moisture", "fiber"]), 2)
            me = round(((mapped_values["protein"] * 4) + (mapped_values["fat"] * 9) + (cho * 4)) * 10, 2)

            sample.results.append({"parameter": "CHO", "method": "AOAC by difference", "value": cho, "unit": "%"})
            sample.results.append({"parameter": "ME", "method": "Calculated using Atwater factors", "value": me, "unit": "kcal/kg"})

            parameters.add(("CHO", "%", "AOAC by difference"))
            parameters.add(("ME", "kcal/kg", ""))

    # ✅ Compute sample weight display
    weights = [s.weight for s in samples if s.weight is not None]
    if len(weights) == 1:
        sample_weight_display = f"{weights[0]} g"
    elif weights:
        sample_weight_display = f"{min(weights)} g – {max(weights)} g"
    else:
        sample_weight_display = "N/A"

    # ✅ Prepare parameter list for template
    param_list = [{"name": p[0], "unit": p[1], "method": clean_method(p[2])} for p in parameters]

    # ✅ Mark COA as released
    client.coa_released = True
    client.save()

    # ✅ Send email with signed PDF
    notify_client_on_coa_release(
        client=client,
        samples=samples,
        summary_text=summary_text,
        parameters=param_list,
        sample_weight_display=sample_weight_display
    )

    messages.success(request, f"✅ COA released and emailed to {client.name}.")
    return redirect("coa_dashboard")



@login_required
def preview_coa(request, client_id):
    samples = (
        Sample.objects
        .exclude(sample_code__startswith="QC-")
        .filter(client__client_id=client_id)
        .prefetch_related(
            "testassignment_set__parameter",
            "testassignment_set__testresult",
            "testassignment_set__testenvironment",
            "client"
        )
    )

    if not samples.exists():
        return HttpResponse("No samples found for this client.", status=404)

    client = samples.first().client

    # ✅ Get or create interpretation
    interpretation, _ = COAInterpretation.objects.get_or_create(client=client)

    # ✅ Handle POST (Save Summary)
    if request.method == "POST":
        summary_text = request.POST.get("summary_text", "").strip()
        interpretation.summary_text = summary_text
        interpretation.save()
        messages.success(request, "Summary updated successfully.")
        return redirect("preview_coa", client_id=client_id)

    # ✅ Prepare table data
    table_data = []
    parameter_set = set()
    summary_input = {}

    for sample in samples:
        row_data = {
            "sample_code": sample.sample_code,
            "weight": sample.weight,
            "environment": None,
            "results": [],
        }
        param_values = {}

        # Collect results for this sample
        for ta in sample.testassignment_set.all():
            res = getattr(ta, "testresult", None)
            param = ta.parameter
            parameter_set.add((param.name, param.unit, param.method))

            if res:
                param_values[param.name.lower()] = res.value
                row_data["results"].append({
                    "parameter": param.name,
                    "method": param.method,
                    "value": res.value,
                    "unit": param.unit,
                })

            env = getattr(ta, "testenvironment", None)
            if env and not row_data["environment"]:
                row_data["environment"] = f"{env.temperature}°C, {env.humidity}%RH"

        # ✅ CHO and ME calculations (kcal/kg)
        calc_map = {
            "protein": "protein",
            "crude fat": "fat",
            "ash": "ash",
            "moisture": "moisture",
            "crude fibre": "fiber",
        }

        mapped_values = {}
        for key, alias in calc_map.items():
            if key in param_values:
                mapped_values[alias] = param_values[key]

        if all(alias in mapped_values for alias in ["protein", "fat", "ash", "moisture", "fiber"]):
            cho = round(100 - sum(mapped_values[k] for k in ["protein", "fat", "ash", "moisture", "fiber"]), 2)
            me = round(
                ((mapped_values["protein"] * 4)
                 + (mapped_values["fat"] * 9)
                 + (cho * 4)) * 10,
                2
            )

            row_data["results"].append({
                "parameter": "CHO",
                "method": "AOAC by difference",
                "value": cho,
                "unit": "%",
            })
            row_data["results"].append({
                "parameter": "ME",
                "method": "Calculated using Atwater factors",
                "value": me,
                "unit": "kcal/kg",
            })

            parameter_set.add(("CHO", "%", "AOAC by difference"))
            parameter_set.add(("ME", "kcal/kg", "Calculated using Atwater factors"))

        row_data["environment"] = row_data["environment"] or "Ambient 25°C 50%RH"
        table_data.append(row_data)

        # ✅ Collect for summary generation
        for result in row_data["results"]:
            summary_input.setdefault(result["parameter"], []).append(result["value"])

    # ✅ Auto-generate summary if empty
    if not interpretation.summary_text:
        interpretation.summary_text = generate_dynamic_summary([{
            "sample_type": samples.first().sample_type or "Unknown",
            "results": summary_input
        }])
        interpretation.save()

    parameters = sorted(list(parameter_set))
    summary_text = interpretation.summary_text

    return render(
        request,
        "lims/preview_coa.html",
        {
            "client": client,
            "samples": table_data,
            "parameters": [
                {"name": p[0], "unit": p[1], "method": clean_method(p[2])} for p in parameters
            ],
            "summary_text": summary_text,
            "today": datetime.date.today(),
            "letterhead_url": request.build_absolute_uri('/static/letterheads/coa_letterhead.png')
        }
    )
