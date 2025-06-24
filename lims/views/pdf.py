from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from lims.models import Client, Sample
from django.utils import timezone

def intake_pdf_download(request, client_id):
    client = Client.objects.get(id=client_id)
    samples = Sample.objects.filter(client=client).prefetch_related('testassignment_set__parameter')

    total_price = 0
    total_tests = 0
    for sample in samples:
        for test in sample.testassignment_set.all():
            total_price += float(test.parameter.default_price)
            total_tests += 1

    html = render_to_string('lims/intake_receipt_pdf.html', {
        'client': client,
        'samples': samples,
        'total_price': total_price,
        'total_tests': total_tests,
        'now': timezone.now()
    })

    pdf_file = HTML(string=html).write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="JGL_Receipt_{client.client_id_code}.pdf"'
    return response
