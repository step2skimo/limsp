import io
import os
import re
import uuid
import logging
import tempfile
from collections import defaultdict
import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from pdfrw import PdfReader, PdfWriter, PageMerge
from weasyprint import HTML
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, HttpResponseNotFound, FileResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.utils import timezone
from lims.models import Client, Sample, SampleStatus, TestResult
from lims.models.coa import COAInterpretation
from lims.forms import COAInterpretationForm
from lims.utils.calculations import calculate_cho_and_me
from lims.utils.coa_summary_ai import generate_dynamic_summary
from lims.utils.notifications import notify_client_on_coa_release



logger = logging.getLogger(__name__)



def clean_method(method_str):
    """
    Extracts only the AOAC reference from a full method string.
    E.g., from 'Kjedahl (AOAC 984.13 2000)' it returns 'AOAC 984.13'
    """
    match = re.search(r"(AOAC\s+\d{3,4}\.\d{1,2})", method_str, re.IGNORECASE)
    return match.group(1) if match else method_str


def chunked_samples(samples, chunk_size=8):
    """Split the samples queryset/list into chunks of `chunk_size`."""
    for i in range(0, len(samples), chunk_size):
        yield samples[i:i + chunk_size]


def abs_static(path, pdf_mode=False, request=None):
    """
    Return a static file URL:
    - If pdf_mode=True, return file:// path from STATIC_ROOT.
    - Otherwise, return an absolute HTTP URL if request is provided.
    """
    if pdf_mode:
        return f"file://{os.path.join(settings.STATIC_ROOT, path)}"
    
    # If request is passed, build absolute URL, otherwise return relative static path
    return request.build_absolute_uri(static(path)) if request else static(path)

@login_required
def generate_coa_pdf(request, client_id):
    """
    Render Certificate of Analysis for ALL non-QC samples belonging to a client_id.
    Supports:
      - HTML preview (?preview=1)
      - Column chunking for many samples (default 8 per table; override with ?chunk=12)
    """
    # ---------------------------------------------------------------
    # Fetch samples
    # ---------------------------------------------------------------
    samples_qs = (
        Sample.objects
        .exclude(sample_type__istartswith="qc")
        .filter(client__client_id=client_id)
        .prefetch_related(
            "testassignment_set__parameter",
            "testassignment_set__testresult",
            # "testassignment_set__testenvironment",  # uncomment if relation exists
        )
        .select_related("client")
        .order_by("sample_code")  # stable ordering for reproducible PDFs
    )

    if not samples_qs.exists():
        return HttpResponseNotFound("No samples found for this client.")

    client = samples_qs.first().client

    # Materialize list early (we modify objects by attaching attributes)
    samples = list(samples_qs)

    # ---------------------------------------------------------------
    # Build per-sample results + global parameter registry
    # ---------------------------------------------------------------
    parameters = {}  # param_name -> (unit, method)

    for sample in samples:
        sample.results = []
        sample_environment = None
        param_values = {}

        for ta in sample.testassignment_set.all():
            param = ta.parameter
            res = getattr(ta, "testresult", None)

            if res and res.value is not None:
                value = float(res.value)
                param_values[param.name.lower()] = value
                sample.results.append({
                    "parameter": param.name,
                    "method": param.method,
                    "value": value,
                    "unit": param.unit,
                })
                parameters[param.name] = (param.unit, param.method)

            env = getattr(ta, "testenvironment", None)
            if env and not sample_environment:
                sample_environment = f"{env.temperature}°C, {env.humidity}%RH"

        # ---- Derived CHO & ME ----
        key_map = {
            "protein": "protein",
            "crude fat": "fat",
            "crude fibre": "fiber",
            "crude fiber": "fiber",
            "moisture": "moisture",
            "ash": "ash",
        }
        normalized = {}
        for raw, norm in key_map.items():
            if raw in param_values:
                normalized[norm] = param_values[raw]

        required = {"protein", "fat", "fiber", "moisture", "ash"}
        if required.issubset(normalized):
            cho = round(100 - sum(normalized[k] for k in required), 2)
            me = round(((normalized["protein"] * 4) + (normalized["fat"] * 9) + (cho * 4)) * 10, 2)
            sample.results.append({
                "parameter": "CHO",
                "method": "AOAC (by difference)",
                "value": cho,
                "unit": "%",
            })
            sample.results.append({
                "parameter": "ME",
                "method": "Calculated (Atwater factors)",
                "value": me,
                "unit": "kcal/kg",
            })
            parameters.setdefault("CHO", ("%", "AOAC (by difference)"))
            parameters.setdefault("ME", ("kcal/kg", "Calculated (Atwater factors)"))

        sample.environment = sample_environment or "Ambient 25°C 50%RH"

    # ---------------------------------------------------------------
    # Parameter rows (sorted for deterministic output)
    # ---------------------------------------------------------------
    parameter_rows = [
        {"name": name, "unit": unit, "method": clean_method(method)}
        for name, (unit, method) in sorted(parameters.items(), key=lambda x: x[0].lower())
    ]

    # ---------------------------------------------------------------
    # Summary text
    # ---------------------------------------------------------------
    interpretation = COAInterpretation.objects.filter(client=client).first()
    summary_text = interpretation.summary_text if interpretation else "Summary not available."

    # ---------------------------------------------------------------
    # Weight display
    # ---------------------------------------------------------------
    weights = [s.weight for s in samples if s.weight is not None]
    if len(weights) == 1:
        sample_weight_display = f"{weights[0]} g"
    elif weights:
        sample_weight_display = f"{min(weights)} g – {max(weights)} g"
    else:
        sample_weight_display = "N/A"

    # ---------------------------------------------------------------
    # Sample chunking
    # ---------------------------------------------------------------
    try:
        chunk_size = int(request.GET.get("chunk", 20))
        if chunk_size < 1:
            chunk_size = 8
    except ValueError:
        chunk_size = 8

    def chunk_list(seq, size):
        for i in range(0, len(seq), size):
            yield seq[i:i + size]

    sample_chunks = list(chunk_list(samples, chunk_size))

    #  If you want landscape automatically when many samples total:
    # if len(samples) > 8:
    #     force_landscape = True  # You'd then pass a flag and adjust @page in template.


    letterhead_url = abs_static("letterheads/coa_letterhead.png", pdf_mode=True)
    signature_1 = abs_static("images/signatures/hannah-sign.png", pdf_mode=True)
    signature_2 = abs_static("images/signatures/julius-sign.png", pdf_mode=True)


    # ---------------------------------------------------------------
    # Template context
    # ---------------------------------------------------------------
    context = {
        "client": client,
        "samples": samples,              # still used for metadata (samples.0...)
        "sample_chunks": sample_chunks,  # used for the multi-table section
        "parameters": parameter_rows,
        "summary_text": summary_text,
        "sample_weight_display": sample_weight_display,
        "today": datetime.date.today(),
        "letterhead_url": letterhead_url,
        "signature_1": signature_1,
        "signature_2": signature_2,
        # "force_landscape": True,  # if you decide to implement conditional orientation
    }

    html = render_to_string("lims/coa/coa_template.html", context)

    # ---------------------------------------------------------------
    # Preview mode
    # ---------------------------------------------------------------
    if request.GET.get("preview"):
        return HttpResponse(html)

    # ---------------------------------------------------------------
    # PDF generation
    # ---------------------------------------------------------------
    pdf = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()

    filename = f"COA_{client.client_id or client.id}_{datetime.date.today().isoformat()}.pdf"
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


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

    return render(request, "lims/coa/edit_summary.html", {
        "client": client,
        "form": form,
    })



@login_required
def coa_dashboard(request):
    # Get all samples except QC
    samples = (
        Sample.objects
        .exclude(sample_type="qc")
        .select_related("client")
        .order_by("-client__client_id", "-received_date")
    )

    # Group by client
    grouped = defaultdict(lambda: {"samples": [], "all_completed": True})

    for sample in samples:
        client_entry = grouped[sample.client]
        client_entry["samples"].append(sample)

        # If any sample is NOT approved -> all_completed = False
        if sample.status != SampleStatus.APPROVED:
            client_entry["all_completed"] = False

    context = {
        "grouped": dict(grouped),
    }
    return render(request, "lims/coa/coa_dashboard.html", context)



def _clean_method(txt):
    if not txt:
        return ""
    return " ".join(str(txt).split())



@login_required
def release_client_coa(request, client_id):
    """
    Generate the official COA PDF for this client and email it to them.
    - Uses the same template as the "Download COA" path (lims/coa_template.html).
    - Marks all non-QC samples as released.
    - Saves the generated PDF to storage (MEDIA).
    """
    if request.method != "POST":
        return HttpResponse("❌ Not a POST request", status=405)

    # Adjust lookup: using DB pk here. If you later switch to business ID, update accordingly.
    client = get_object_or_404(Client, pk=client_id)

    # Interpretation summary
    interpretation = COAInterpretation.objects.filter(client=client).first()
    summary_text = interpretation.summary_text if interpretation else "Summary not available."

    # Client samples (ignore QC)
    samples = (
        Sample.objects
        .exclude(sample_code__istartswith="qc-")
        .filter(client=client)
        .prefetch_related(
            "testassignment_set__parameter",
            "testassignment_set__testresult",
            "testassignment_set__testenvironment",
        )
    )
    if not samples.exists():
        return HttpResponseNotFound("No samples found for this client.")

    # --------------------------------------------------
    # Build results + parameter headers
    # --------------------------------------------------
    parameters = {}  # param_name -> (unit, method)
    for sample in samples:
        sample.results = []
        sample_environment = None
        param_values = {}  # raw name lowercase -> value

        for ta in sample.testassignment_set.all():
            param = ta.parameter
            res = getattr(ta, "testresult", None)

            if res and res.value is not None:
                val = float(res.value)
                param_values[param.name.lower()] = val
                sample.results.append({
                    "parameter": param.name,
                    "method": param.method,
                    "value": val,
                    "unit": param.unit,
                })
                parameters[param.name] = (param.unit, param.method)

            env = getattr(ta, "testenvironment", None)
            if env and sample_environment is None:
                sample_environment = f"{env.temperature}°C, {env.humidity}%RH"

        # Derived CHO & ME
        key_map = {
            "protein": "protein",
            "crude fat": "fat",
            "ash": "ash",
            "moisture": "moisture",
            "crude fibre": "fiber",
            "crude fiber": "fiber",
        }
        mapped = {v: param_values[k] for k, v in key_map.items() if k in param_values}
        if {"protein", "fat", "fiber", "moisture", "ash"}.issubset(mapped):
            cho = round(100 - sum(mapped[k] for k in ["protein", "fat", "fiber", "moisture", "ash"]), 2)
            me = round(((mapped["protein"] * 4) + (mapped["fat"] * 9) + (cho * 4)) * 10, 2)

            sample.results.append({
                "parameter": "CHO",
                "method": "AOAC by difference",
                "value": cho,
                "unit": "%",
            })
            sample.results.append({
                "parameter": "ME",
                "method": "Calculated using Atwater factors",
                "value": me,
                "unit": "kcal/kg",
            })
            parameters.setdefault("CHO", ("%", "AOAC by difference"))
            parameters.setdefault("ME", ("kcal/kg", "Calculated using Atwater factors"))

        sample.environment = sample_environment or "Ambient 25°C 50%RH"

    # Sorted parameter header
    param_list = [
        {"name": n, "unit": u, "method": _clean_method(m)}
        for n, (u, m) in sorted(parameters.items(), key=lambda x: x[0].lower())
    ]

    # Sample weight display
    weights = [s.weight for s in samples if s.weight is not None]
    if len(weights) == 1:
        sample_weight_display = f"{weights[0]} g"
    elif weights:
        sample_weight_display = f"{min(weights)} g – {max(weights)} g"
    else:
        sample_weight_display = "N/A"

    # --------------------------------------------------
    # Build PDF context (WeasyPrint needs file:// absolute paths)
    # --------------------------------------------------
    letterhead_path = os.path.join(settings.STATIC_ROOT, "letterheads", "coa_letterhead.png")
    signature1_path = os.path.join(settings.STATIC_ROOT, "images/signatures/hannah-sign.png")
    signature2_path = os.path.join(settings.STATIC_ROOT, "images/signatures/julius-sign.png")

    pdf_context = {
        "client": client,
        "samples": samples,
        "sample_chunks": list(chunked_samples(samples, 20)),
        "parameters": param_list,
        "summary_text": summary_text,
        "today": datetime.date.today(),
        "letterhead_url": f"file://{letterhead_path}",
        "signature_1": f"file://{signature1_path}",
        "signature_2": f"file://{signature2_path}",
        "sample_weight_display": sample_weight_display,
    }

    # Render HTML & generate PDF
    html = render_to_string("lims/coa/coa_template.html", pdf_context)
    timestamp = timezone.now().strftime("%Y%m%d-%H%M%S")
    filename = f"COA_{client.client_id}_{timestamp}.pdf"
    temp_path = os.path.join(tempfile.gettempdir(), filename)

    HTML(string=html, base_url=settings.STATIC_ROOT).write_pdf(target=temp_path)

    with open(temp_path, "rb") as f:
        pdf_bytes = f.read()

    # Save PDF to storage (MEDIA/…)
    storage_path = f"coa_reports/{filename}"
    default_storage.save(storage_path, ContentFile(pdf_bytes))

    try:
        os.remove(temp_path)
    except Exception:
        pass

    # --------------------------------------------------
    # Mark released + email
    # --------------------------------------------------
    with transaction.atomic():
        samples.update(coa_released=True)
        # remove client.latest_coa_file if field doesn't exist
        # if you later add one, uncomment:
        client.coa_released = True
        client.save(update_fields=["coa_released"])

        notify_client_on_coa_release(
            client=client,
            summary_text=summary_text,
            pdf_bytes=pdf_bytes,
            filename=filename,
        )

    messages.success(request, f"✅ COA released and emailed to {client.name}.")
    return redirect("coa_dashboard")






def _build_sample_data(samples_qs):
    """
    Mutates & returns a list of sample-like objects annotated with:
      .results = [{parameter, method, value, unit}, ...]
      .environment = string
    Also returns a sorted parameter list and a summary_input dict for summary generation.
    """
    parameters = {}  # name -> (unit, method)
    summary_input = defaultdict(list)

    samples = list(samples_qs)  # evaluate once

    for sample in samples:
        sample.results = []
        sample.environment = None

        param_values = {}  # for CHO / ME
        for ta in sample.testassignment_set.all():
            param = ta.parameter
            res = getattr(ta, "testresult", None)

            if res and res.value is not None:
                value = float(res.value)
                param_values[param.name.lower()] = value

                sample.results.append({
                    "parameter": param.name,
                    "method": param.method,
                    "value": value,
                    "unit": param.unit,
                })

                parameters[param.name] = (param.unit, param.method)
                summary_input[param.name].append(value)

            env = getattr(ta, "testenvironment", None)
            if env and sample.environment is None:
                sample.environment = f"{env.temperature}°C, {env.humidity}%RH"

        # derived CHO / ME
        key_map = {
            "protein": "protein",
            "crude fat": "fat",
            "crude fibre": "fiber",
            "crude fiber": "fiber",
            "moisture": "moisture",
            "ash": "ash",
        }
        mapped = {}
        for raw, norm in key_map.items():
            if raw in param_values:
                mapped[norm] = param_values[raw]

        required = {"protein", "fat", "fiber", "moisture", "ash"}
        if required.issubset(mapped.keys()):
            cho = round(100 - sum(mapped[k] for k in required), 2)
            me = round(((mapped["protein"] * 4) + (mapped["fat"] * 9) + (cho * 4)) * 10, 2)

            sample.results.append({
                "parameter": "CHO",
                "method": "AOAC by difference",
                "value": cho,
                "unit": "%",
            })
            sample.results.append({
                "parameter": "ME",
                "method": "Calculated using Atwater factors",
                "value": me,
                "unit": "kcal/kg",
            })

            parameters.setdefault("CHO", ("%", "AOAC by difference"))
            parameters.setdefault("ME", ("kcal/kg", "Calculated using Atwater factors"))
            summary_input["CHO"].append(cho)
            summary_input["ME"].append(me)

        if sample.environment is None:
            sample.environment = "Ambient 25°C 50%RH"

    # Sort param list
    param_rows = [
        {"name": name, "unit": unit, "method": clean_method(method)}
        for name, (unit, method) in sorted(parameters.items(), key=lambda x: x[0].lower())
    ]
    return samples, param_rows, summary_input


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
    summary_input = {}  # { "Protein": [34.1, 33.8], ... }

    for sample in samples:
        row_data = {
            "sample_code": sample.sample_code,
            "weight": getattr(sample, "weight", None),
            "environment": None,
            "results": [],
        }
        param_values = {}

        # Collect results for this sample
        for ta in sample.testassignment_set.all():
            res = getattr(ta, "testresult", None)
            param = ta.parameter
            parameter_set.add((param.name, param.unit, param.method))

            if res and res.value is not None:
                # normalize to float for summary calcs
                val = float(res.value)
                param_values[param.name.lower()] = val
                row_data["results"].append({
                    "parameter": param.name,
                    "method": param.method,
                    "value": val,
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
            cho = round(
                100 - sum(mapped_values[k] for k in ["protein", "fat", "ash", "moisture", "fiber"]),
                2
            )
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
                "unit": "%",  # by-difference proximate remainder
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
            # result["value"] already float
            summary_input.setdefault(result["parameter"], []).append(result["value"])

    # ✅ Auto-generate summary if empty (AI first, fallback to avg)
    if not interpretation.summary_text:
        # Build AI payload (single item, using first sample's sample_type)
        sample_type_name = getattr(samples.first(), "sample_type", None) or "Unknown"
        ai_payload = [{
            "sample_type": sample_type_name,
            "results": summary_input
        }]

        ai_text = generate_dynamic_summary(ai_payload)
        if ai_text and not ai_text.startswith("Summary generation failed"):
            interpretation.summary_text = ai_text.strip()
        else:
            # Fallback: avg lines
            summary_lines = []
            for pname, vals in summary_input.items():
                if vals:
                    avg_val = sum(vals) / len(vals)
                    summary_lines.append(f"{pname}: avg {avg_val:.2f}")
            interpretation.summary_text = "\n".join(summary_lines) or "Summary not available."

        interpretation.save()

    parameters = sorted(list(parameter_set))
    summary_text = interpretation.summary_text

    # Optional: include signatures & weight if your template needs them
    # weight aggregation (lightweight; based on table_data)
    weights = [row["weight"] for row in table_data if row["weight"] is not None]
    if len(weights) == 1:
        sample_weight_display = f"{weights[0]} g"
    elif weights:
        sample_weight_display = f"{min(weights)} g – {max(weights)} g"
    else:
        sample_weight_display = "N/A"

    context = {
        "client": client,
        "samples": table_data,
        "parameters": [
            {"name": p[0], "unit": p[1], "method": clean_method(p[2])}
            for p in parameters
        ],
        "summary_text": summary_text,
        "today": datetime.date.today(),
        "letterhead_url": request.build_absolute_uri('/static/letterheads/coa_letterhead.png'),

         "signature_1": request.build_absolute_uri('/static/images/signatures/hannah-sign.png'),
         "signature_2": request.build_absolute_uri('/static/images/signatures/julius-sign.png'),
         "sample_weight_display": sample_weight_display,
    }

    return render(request, "lims/coa/preview_coa.html", context)
