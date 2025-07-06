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

logger = logging.getLogger(__name__)


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

    summary_input = {}
    parameters = set()

    for sample in samples:
        sample.results = []
        param_values = {}
        sample_environment = None

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

                summary_input.setdefault(param_name, []).append(value)
                parameters.add((param_name, ta.parameter.unit, ta.parameter.method))

            env = getattr(ta, "testenvironment", None)
            if env and not sample_environment:
                sample_environment = f"{env.temperature}°C, {env.humidity}%RH"

        # Calculate CHO & ME if possible
        required = ["protein", "fat", "ash", "moisture", "fiber"]
        if all(k in param_values for k in required):
            cho = round(100 - sum(param_values[k] for k in required), 2)
            me = round(
                (param_values["protein"] * 4)
                + (param_values["fat"] * 9)
                + (cho * 4),
                2
            )
            sample.results.append({
                "parameter": "CHO",
                "method": "Calculated as: 100 – (Protein + Fat + Ash + Moisture + Fiber)",
                "value": cho,
                "unit": "%",
            })
            sample.results.append({
                "parameter": "ME",
                "method": "ME = (Protein × 4) + (Fat × 9) + (CHO × 4)",
                "value": me,
                "unit": "kcal/100g",
            })

            summary_input.setdefault("CHO", []).append(cho)
            summary_input.setdefault("ME", []).append(me)
            parameters.add(("CHO", "%", "Calculated as: 100 – (Protein + Fat + Ash + Moisture + Fiber)"))
            parameters.add(("ME", "kcal/100g", "ME = (Protein × 4) + (Fat × 9) + (CHO × 4)"))

        sample.environment = sample_environment or "Ambient 25°C 50%RH"

    parameters = sorted(parameters)

    # Generate AI summary
    summary_text = generate_dynamic_summary(summary_input)

    # Build letterhead path for WeasyPrint
    letterhead_path = os.path.join(settings.STATIC_ROOT, "letterheads", "coa_letterhead.png")
    letterhead_url = f"file://{letterhead_path}"

    # Render HTML
    html = render_to_string(
        "lims/coa_template.html",
        {
            "client": client,
            "samples": samples,
            "summary_text": summary_text,
            "parameters": [
                {"name": p[0], "unit": p[1], "method": p[2]} for p in parameters
            ],
            "today": datetime.date.today(),
            "letterhead_url": letterhead_url,
        }
    )

    # Generate PDF
    pdf_file = HTML(string=html, base_url=request.build_absolute_uri()).write_pdf()
    return HttpResponse(pdf_file, content_type="application/pdf")




@login_required
def coa_dashboard(request):
    # get ALL samples except QC samples
    samples = (
        Sample.objects
        .exclude(sample_type="QC")
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
    client = get_object_or_404(Client, id=client_id)
    client.coa_released = True
    client.save()
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

    table_data = []
    parameter_set = set()

    for sample in samples:
        row_data = {
            "sample_code": sample.sample_code,
            "weight": sample.weight,
            "environment": None,
            "results": [],
        }
        param_values = {}
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

            # environment
            env = getattr(ta, "testenvironment", None)
            if env and not row_data["environment"]:
                row_data["environment"] = f"{env.temperature}°C, {env.humidity}%RH"

        # CHO + ME if all proximate are there
        required = ["protein", "fat", "ash", "moisture", "fiber"]
        if all(k in param_values for k in required):
            cho = round(
                100 - (
                    param_values["protein"] +
                    param_values["fat"] +
                    param_values["ash"] +
                    param_values["moisture"] +
                    param_values["fiber"]
                ), 2
            )
            row_data["results"].append({
                "parameter": "CHO",
                "method": "Calculated as: 100 – (Protein + Fat + Ash + Moisture + Fiber)",
                "value": cho,
                "unit": "%",
            })
            parameter_set.add(("CHO", "%", "Calculated as: 100 – (Protein + Fat + Ash + Moisture + Fiber)"))

            me = round(
                (param_values["protein"] * 4)
                + (param_values["fat"] * 9)
                + (cho * 4),
                2
            )
            row_data["results"].append({
                "parameter": "ME",
                "method": "ME = (Protein × 4) + (Fat × 9) + (CHO × 4)",
                "value": me,
                "unit": "kcal/100g",
            })
            parameter_set.add(("ME", "kcal/100g", "ME = (Protein × 4) + (Fat × 9) + (CHO × 4)"))

        row_data["environment"] = row_data["environment"] or "Ambient 25°C 50%RH"
        table_data.append(row_data)

    parameters = sorted(list(parameter_set))

    # summary
    summary_input = {}
    for row in table_data:
        for result in row["results"]:
            summary_input.setdefault(result["parameter"], []).append(result["value"])

    summary_text = generate_dynamic_summary(summary_input)

    return render(
        request,
        "lims/coa_template.html",
        {
            "client": client,
            "samples": table_data,
            "parameters": [
                {"name": p[0], "unit": p[1], "method": p[2]} for p in parameters
            ],
            "summary_text": summary_text,
            "today": datetime.date.today(),
            "letterhead_url": request.build_absolute_uri('/static/letterheads/coa_letterhead.png')
        }
    )
