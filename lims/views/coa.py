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
import copy



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

ACCREDITED_GROUPS = {
    "Gross Energy",
    "Vitamins & Contaminants",
    "Aflatoxin",
    "CHO",
    "ME",
    "Fiber",
    "Fiber Fractions",
    "Proximate",
}


def split_samples_by_accreditation(samples):
    """
    Split parameters of each sample into accredited and unaccredited lists.
    """
    accredited_groups = {
        "Gross Energy", "Vitamins & Contaminants", "Aflatoxin",
        "CHO", "ME", "Fiber Fractions", "Proximate"
    }

    accredited_samples = []
    unaccredited_samples = []

    for s in samples:
        s_accredited = copy.copy(s)
        s_unaccredited = copy.copy(s)

        s_accredited.filtered_assignments = []
        s_unaccredited.filtered_assignments = []

        for ta in s.testassignment_set.all():
            group_name = ta.parameter.group.name if ta.parameter.group else None
            if group_name in accredited_groups:
                s_accredited.filtered_assignments.append(ta)
            else:
                s_unaccredited.filtered_assignments.append(ta)

        if s_accredited.filtered_assignments:
            accredited_samples.append(s_accredited)
        if s_unaccredited.filtered_assignments:
            unaccredited_samples.append(s_unaccredited)

    return accredited_samples, unaccredited_samples



def render_coa_pdf(request, client, samples, accredited=True):
    """
    Render the PDF for either accredited or unaccredited samples.
    """
    accredited_groups = {
        "Gross Energy", "Vitamins & Contaminants", "Aflatoxin",
        "CHO", "ME", "Fiber", "Proximate"
    }
    parameters = {}

    for sample in samples:
        sample.results = []
        sample_environment = None
        param_values = {}

        # Get only assignments relevant for this COA
        assignments = getattr(sample, "filtered_assignments", sample.testassignment_set.all())
        for ta in assignments:
            group_name = ta.parameter.group.name if ta.parameter.group else None

            # Skip if not matching current COA type
            if accredited and group_name not in accredited_groups:
                continue
            if not accredited and group_name in accredited_groups:
                continue

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
                # Add parameter to parameter table
                parameters[param.name] = (param.unit, clean_method(param.method))

            env = getattr(ta, "testenvironment", None)
            if env and not sample_environment:
                sample_environment = f"{env.temperature}°C, {env.humidity}%RH"

        # Derived CHO & ME
        key_map = {
            "protein": "protein",
            "crude fat": "fat",
            "crude fibre": "fiber",
            "crude fiber": "fiber",
            "moisture": "moisture",
            "ash": "ash",
        }
        normalized = {norm: param_values[raw] for raw, norm in key_map.items() if raw in param_values}
        required = {"protein", "fat", "fiber", "moisture", "ash"}
        if required.issubset(normalized):
            cho = round(100 - sum(normalized[k] for k in required), 2)
            me = round(((normalized["protein"] * 4) + (normalized["fat"] * 9) + (cho * 4)) * 10, 2)
            sample.results.append({"parameter": "CHO", "method": "AOAC (by difference)", "value": cho, "unit": "%"})
            sample.results.append({"parameter": "ME", "method": "Calculated (Atwater factors)", "value": me, "unit": "kcal/kg"})
            parameters.setdefault("CHO", ("%", "AOAC (by difference)"))
            parameters.setdefault("ME", ("kcal/kg", "Calculated (Atwater factors)"))

        sample.environment = sample_environment or "Ambient 25°C 50%RH"

    # Prepare parameter table
    parameter_rows = [
        {"name": name, "unit": unit, "method": clean_method(method)}
        for name, (unit, method) in sorted(parameters.items(), key=lambda x: x[0].lower())
    ]

    # Summary
    interpretation = COAInterpretation.objects.filter(client=client).first()
    summary_text = interpretation.summary_text if interpretation else "Summary not available."

    # Weight display
    weights = [s.weight for s in samples if s.weight is not None]
    sample_weight_display = f"{min(weights)} g – {max(weights)} g" if len(weights) > 1 else (f"{weights[0]} g" if weights else "N/A")

    # Chunking
    chunk_size = int(request.GET.get("chunk", 20)) if request.GET.get("chunk", "").isdigit() else 8
    sample_chunks = [samples[i:i + chunk_size] for i in range(0, len(samples), chunk_size)]

    # Letterhead & signatures
    letterhead_url = abs_static(
        "letterheads/accredited_letterhead.png" if accredited else "letterheads/unaccredited_letterhead.jpg",
        pdf_mode=True
    )
    signature_1 = abs_static("images/signatures/hannah-sign.png", pdf_mode=True)
    signature_2 = abs_static("images/signatures/julius-sign.png", pdf_mode=True)

    context = {
        "client": client,
        "samples": samples,
        "sample_chunks": sample_chunks,
        "parameters": parameter_rows,
        "summary_text": summary_text,
        "sample_weight_display": sample_weight_display,
        "today": datetime.date.today(),
        "letterhead_url": letterhead_url,
        "signature_1": signature_1,
        "signature_2": signature_2,
    }

    html = render_to_string("lims/coa/coa_template.html", context)
    if request.GET.get("preview"):
        return HttpResponse(html)

    pdf = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()
    filename = f"COA_{client.client_id or client.id}_{'accredited' if accredited else 'unaccredited'}_{datetime.date.today().isoformat()}.pdf"
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename=\"{filename}\"'
    return response



@login_required
def generate_coa_pdf(request, client_id):
    """
    Generate the accredited COA PDF.
    """
    client = get_object_or_404(Client, client_id=client_id)
    samples = (
        Sample.objects
        .filter(client=client)
        .exclude(sample_type="qc")
        .prefetch_related("testassignment_set__parameter__group", "testassignment_set__testresult")
    )

    accredited_samples, _ = split_samples_by_accreditation(samples)
    return render_coa_pdf(request, client, accredited_samples, accredited=True)


@login_required
def generate_unaccredited_coa_pdf(request, client_id):
    """
    Generate the unaccredited COA PDF.
    """
    client = get_object_or_404(Client, client_id=client_id)
    samples = (
        Sample.objects
        .filter(client=client)
        .exclude(sample_type="qc")
        .prefetch_related("testassignment_set__parameter__group", "testassignment_set__testresult")
    )

    _, unaccredited_samples = split_samples_by_accreditation(samples)
    return render_coa_pdf(request, client, unaccredited_samples, accredited=False)




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
        .prefetch_related("testassignment_set__parameter")
        .order_by("-client__client_id", "-received_date")
    )

    # Group samples by client
    grouped = defaultdict(lambda: {
        "samples": [],
        "all_completed": True,
        "has_unaccredited": False
    })

    for sample in samples:
        client_entry = grouped[sample.client]
        client_entry["samples"].append(sample)

        # Add assignments (without touching testassignment_set)
        sample.assignments = [
            {
                "parameter": a.parameter.name,
                "method": a.parameter.method,
                "unit": a.parameter.unit,
            }
            for a in sample.testassignment_set.all()
        ]

        # Check completion status
        if sample.status != SampleStatus.APPROVED:
            client_entry["all_completed"] = False

    # Determine has_unaccredited for each client
    for client, data in grouped.items():
        accredited, unaccredited = split_samples_by_accreditation(data["samples"])
        data["has_unaccredited"] = bool(unaccredited)

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
    Generate official COA PDFs (accredited and unaccredited if available)
    and email them to the client.
    """
    if request.method != "POST":
        return HttpResponse("❌ Not a POST request", status=405)

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
            "testassignment_set__parameter__group",
            "testassignment_set__testresult",
            "testassignment_set__testenvironment",
        )
    )
    if not samples.exists():
        return HttpResponseNotFound("No samples found for this client.")

    # --- Split into accredited/unaccredited ---
    accredited_samples, unaccredited_samples = split_samples_by_accreditation(samples)

    # Function to generate PDF and return (filename, pdf_bytes)
    def generate_pdf(samples, accredited=True):
        # Prepare parameters and sample results
        parameters = {}
        for sample in samples:
            sample.results = []
            sample_environment = None
            param_values = {}

            for ta in sample.testassignment_set.all():
                group_name = ta.parameter.group.name if ta.parameter.group else None
                if accredited and group_name not in ACCREDITED_GROUPS:
                    continue
                if not accredited and group_name in ACCREDITED_GROUPS:
                    continue

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

        param_list = [
            {"name": n, "unit": u, "method": _clean_method(m)}
            for n, (u, m) in sorted(parameters.items(), key=lambda x: x[0].lower())
        ]

        # Weight display
        weights = [s.weight for s in samples if s.weight is not None]
        sample_weight_display = (
            f"{weights[0]} g" if len(weights) == 1 else
            f"{min(weights)} g – {max(weights)} g" if weights else "N/A"
        )

        # Letterhead and signatures
        letterhead_path = os.path.join(
            settings.STATIC_ROOT,
            "letterheads",
            "coa_letterhead.png" if accredited else "unaccredited_letterhead.jpg"
        )
        signature1_path = os.path.join(settings.STATIC_ROOT, "images/signatures/hannah-sign.png")
        signature2_path = os.path.join(settings.STATIC_ROOT, "images/signatures/julius-sign.png")

        # Build PDF context
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

        # Render to PDF
        html = render_to_string("lims/coa/coa_template.html", pdf_context)
        timestamp = timezone.now().strftime("%Y%m%d-%H%M%S")
        filename = f"COA_{client.client_id}_{'accredited' if accredited else 'unaccredited'}_{timestamp}.pdf"
        temp_path = os.path.join(tempfile.gettempdir(), filename)

        HTML(string=html, base_url=settings.STATIC_ROOT).write_pdf(target=temp_path)
        with open(temp_path, "rb") as f:
            pdf_bytes = f.read()

        storage_path = f"coa_reports/{filename}"
        default_storage.save(storage_path, ContentFile(pdf_bytes))

        try:
            os.remove(temp_path)
        except Exception:
            pass

        return filename, pdf_bytes

    # --- Generate PDFs ---
    attachments = []
    if accredited_samples:
        filename, pdf_bytes = generate_pdf(accredited_samples, accredited=True)
        attachments.append((filename, pdf_bytes))
    if unaccredited_samples:
        filename, pdf_bytes = generate_pdf(unaccredited_samples, accredited=False)
        attachments.append((filename, pdf_bytes))

    if not attachments:
        return HttpResponseNotFound("No accredited or unaccredited samples found.")

    # --- Mark released and send email ---
    with transaction.atomic():
        samples.update(coa_released=True)
        client.coa_released = True
        client.save(update_fields=["coa_released"])

        notify_client_on_coa_release(
            client=client,
            summary_text=summary_text,
            attachments=attachments,  # send both PDFs
        )

    messages.success(request, f"✅ COA(s) released and emailed to {client.name}.")
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
