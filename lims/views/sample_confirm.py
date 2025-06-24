from django.shortcuts import render, get_object_or_404
from lims.models import Client, Sample, TestAssignment
from weasyprint import HTML
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.utils import timezone


def intake_confirmation_view(request, client_id):
    client = get_object_or_404(Client, client_id=client_id)
    samples = Sample.objects.filter(client=client).prefetch_related('testassignment_set__parameter')

    total_price = 0
    total_tests = 0

    # Loop through each sample and its assigned tests
    for sample in samples:
        for test in sample.testassignment_set.all():
            total_price += float(test.parameter.default_price)
            total_tests += 1

    
    return render(request, 'lims/intake_confirmation.html', {
        'client': client,
        'samples': samples,
        'total_price': total_price,
        'total_tests': total_tests
    })


def send_receipt_email(client, samples):
    # Prepare data
    total_price = 0
    total_tests = 0
    for sample in samples:
        for test in sample.testassignment_set.all():
            total_price += float(test.parameter.default_price)
            total_tests += 1

    # Render HTML
    html_string = render_to_string('lims/intake_receipt_pdf.html', {
        'client': client,
        'samples': samples,
        'total_price': total_price,
        'total_tests': total_tests,
        'now': timezone.now()
    })

    # Generate PDF
    pdf = HTML(string=html_string).write_pdf()

    # Compose email
    email_body = f"""
Dear {client.name},

Thank you for submitting your samples to JGL Labs.

Attached is your official receipt.

📌 Client Token: {client.token}

We appreciate your business and will notify you when your Certificate of Analysis is ready.

— JGL Labs Team
"""

    email = EmailMessage(
        subject="Your JGL Sample Submission Receipt",
        body=email_body,
        from_email="receipts@jgllabs.com",
        to=[client.email],
    )
    email.attach(f"JGL_Receipt_{client.client_id_code}.pdf", pdf, 'application/pdf')
    email.send()
