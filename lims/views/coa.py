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

from lims.models import Sample
from lims.utils.calculations import calculate_cho_and_me
from lims.utils.coa_summary_ai import generate_dynamic_summary
from django.shortcuts import render
from lims.models import Client, Sample
from collections import defaultdict


@login_required
def generate_coa_pdf(request, client_id):

    samples = (
        Sample.objects
        .filter(client__client_id=client_id)
        .prefetch_related("parameter_tests", "client")
    )

    if not samples.exists():
        return HttpResponse("No samples found for this client.", status=404)

    client = samples.first().client
    all_params = set()

    for sample in samples:
        sample.results = {}
        for test in sample.parameter_tests.all():
            pname = test.parameter.name.lower()
            all_params.add(pname)
            sample.results[pname] = test.result

        # derived calculations
        sample.cho, sample.me = calculate_cho_and_me(
            sample.results.get("moisture", 0),
            sample.results.get("protein", 0),
            sample.results.get("fat", 0),
            sample.results.get("fiber", 0),
            sample.results.get("ash", 0),
        )

    sorted_params = sorted(all_params)
    include_cho = all(x in sorted_params for x in ["moisture", "protein", "fat", "fiber", "ash"])

    summary_text = generate_dynamic_summary(samples)

    # start PDF
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=A4)

    def draw_header():
        c.setFont("Helvetica-Bold", 10)
        c.drawString(80, 780, f"Client Name: {client.name}")
        c.drawString(80, 765, f"Organization: {client.organization}")
        c.drawString(80, 750, f"Address: {client.address}")
        c.drawString(80, 735, f"Phone: {client.phone}")
        c.drawString(80, 720, f"Email: {client.email}")

    def draw_table_header(y):
        c.setFont("Helvetica-Bold", 9)
        x = 80
        c.drawString(x, y, "Sample ID")
        x += 60
        for param in sorted_params:
            c.drawString(x, y, param.title())
            x += 55
        if include_cho:
            c.drawString(x, y, "CHO")
            x += 55
            c.drawString(x, y, "ME (kcal)")
        return y - 20

    draw_header()
    y_pos = 660
    y_pos = draw_table_header(y_pos)
    c.setFont("Helvetica", 9)
    row_spacing = 18

    for sample in samples:
        if y_pos < 100:
            c.showPage()
            draw_header()
            y_pos = 660
            y_pos = draw_table_header(y_pos)
            c.setFont("Helvetica", 9)

        x = 80
        c.drawString(x, y_pos, sample.sample_code)
        x += 60
        for param in sorted_params:
            val = sample.results.get(param, "—")
            c.drawString(x, y_pos, f"{val:.2f}" if isinstance(val, float) else str(val))
            x += 55
        if include_cho:
            c.drawString(x, y_pos, f"{sample.cho:.2f}" if sample.cho is not None else "—")
            x += 55
            c.drawString(x, y_pos, f"{sample.me:.2f}" if sample.me is not None else "—")
        y_pos -= row_spacing

    # Summary
    if y_pos < 140:
        c.showPage()
        draw_header()
        y_pos = 660

    c.setFont("Helvetica-Oblique", 9)
    y_pos -= 20
    c.drawString(80, y_pos, "Interpretation Summary")
    y_pos -= 14
    c.setFont("Helvetica", 9)
    summary_text = summary_text.replace("\n", " ").strip()
    summary_text = summary_text[:250].rstrip(".") + "." if len(summary_text) > 250 else summary_text
    c.drawString(80, y_pos, summary_text)

    # Footer
    c.setFont("Helvetica", 8)
    c.drawString(80, 65, "Methods: AOAC 930.15 (Moisture), 988.05 (Protein), 920.39 (Fat), 978.10 (Fiber), 942.05 (Ash)")
    c.drawString(80, 50, "Signed: Kehinde K. Hannah - Head of Laboratory | Julius Gbolade Famoriyo - FELLOW NISLT REG NO: F0256")

    c.save()
    packet.seek(0)
    overlay_pdf = PdfReader(packet)

    letterhead_path = os.path.join(settings.BASE_DIR, "static", "letterheads", "coa_letterhead.pdf")
    template_pdf = PdfReader(letterhead_path)

    for i, base_page in enumerate(template_pdf.pages):
        overlay_page = overlay_pdf.pages[i] if i < len(overlay_pdf.pages) else None
        if overlay_page:
            merger = PageMerge(base_page)
            merger.add(overlay_page).render()

    output = io.BytesIO()
    PdfWriter(output, trailer=template_pdf).write()
    output.seek(0)

    return HttpResponse(
        output,
        content_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="COA_{client_id}.pdf"'}
    )


@login_required
def manager_coa_dashboard(request):
    from collections import defaultdict

    samples_with_results = (
        Sample.objects
        .prefetch_related("testassignment_set")
        .filter(testassignment__testresult__isnull=False)
        .distinct()
        .order_by("client__name")
    )

    grouped_batches = defaultdict(list)

    for sample in samples_with_results:
        if sample.sample_code.startswith("QC-"):
            continue  # skip QC
        client = sample.client
        if client and client.client_id:
            grouped_batches[client.client_id].append((client.name, sample))

    return render(request, "lims/manager_coa_dashboard.html", {
        "grouped_batches": grouped_batches
    })




@login_required
def preview_coa(request, client_id):
    samples = (
        Sample.objects
        .filter(client__client_id=client_id)
        .prefetch_related("testassignment__testresult", "testassignment__parameter", "client")
    )

    if not samples.exists():
        return render(request, "lims/preview_coa.html", {"error": "No samples found for this client."})

    client = samples.first().client

    parameters_set = set()
    for sample in samples:
        sample.results = []
        for ta in sample.testassignment.all():
            if ta.is_control:
                continue
            res = getattr(ta, "testresult", None)
            if res:
                parameters_set.add(ta.parameter.name)
                sample.results.append({
                    "parameter": ta.parameter.name,
                    "value": res.value,
                    "unit": ta.parameter.unit,
                    "method": ta.parameter.method,
                    "specification": ta.parameter.ref_limit,
                })

    sorted_parameters = sorted(parameters_set)

    return render(request, "lims/preview_coa.html", {
        "samples": samples,
        "client": client,
        "parameters": sorted_parameters,
        "client_id": client_id
    })
