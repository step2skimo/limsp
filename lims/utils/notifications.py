from django.core.mail import send_mail
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.template.loader import render_to_string
from weasyprint import HTML
import tempfile
import datetime
import os

import os
import tempfile
import datetime

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings

from weasyprint import HTML

from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags

def notify_low_stock(manager_email, reagent_name, batch_number, number_of_bottles, threshold):
    subject = f"⚠️ Low Stock Alert: {reagent_name}"

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <p>Hello <strong>Lab Manager</strong>,</p>

        <p>
          This is to notify you that the reagent <strong>{reagent_name}</strong> (Batch <strong>{batch_number}</strong>)
          has dropped to <strong>{number_of_bottles} bottle(s)</strong>, which is below the set threshold of <strong>{threshold}</strong>.
        </p>

        <p style="color: red;"><strong>Action may be required to restock this reagent.</strong></p>

        <p>
          👉 <a href="https://jaagee-lab.onrender.com/">Go to Reagent Inventory</a>
        </p>

        <p style="margin-top: 30px;">
          Regards,<br>
          <strong>JaaGee LIMS</strong>
        </p>
      </body>
    </html>
    """

    text_content = strip_tags(html_content)

    email = EmailMultiAlternatives(
        subject,
        text_content,
        from_email="lims@jaagee-lab.com",
        to=[manager_email]
    )
    email.attach_alternative(html_content, "text/html")
    email.send()



def notify_client_on_coa_release(client, samples, summary_text, parameters):
    subject = "Your Certificate of Analysis (COA) is Now Available"

    # ✅ Email body with summary included
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <p>Dear <strong>{client.name}</strong>,</p>

        <p>We are pleased to inform you that the Certificate of Analysis (COA) for your submitted samples (Client ID: <strong>{client.client_id}</strong>) has been released.</p>
        <hr>
        <p><strong>Summary Interpretation:</strong></p>
        <p>{summary_text}</p>

        <p style="margin-top: 30px;">Thank you for choosing <strong>JaaGee Laboratory</strong>.</p>

        <p>Best regards,<br>JaaGee LIMS</p>
      </body>
    </html>
    """
    text_body = strip_tags(html_body)

    # ✅ Generate COA PDF for attachment
    letterhead_path = os.path.join(settings.STATIC_ROOT, "letterheads", "coa_letterhead.png")
    letterhead_url = f"file://{letterhead_path}"

    coa_html = render_to_string(
        "lims/coa_template.html",
        {
            "client": client,
            "samples": samples,
            "summary_text": summary_text,
            "parameters": parameters,
            "today": datetime.date.today(),
            "letterhead_url": letterhead_url,
        }
    )

    # ✅ Save PDF to temporary location
    timestamp = timezone.now().strftime("%Y%m%d-%H%M%S")
    filename = f"COA_{client.client_id}_{timestamp}.pdf"
    path = f"coa_reports/{filename}"
    temp_path = os.path.join(tempfile.gettempdir(), filename)

    HTML(string=coa_html).write_pdf(target=temp_path)

    with open(temp_path, "rb") as f:
        pdf_bytes = f.read()
        default_storage.save(path, ContentFile(pdf_bytes))

    try:
        os.remove(temp_path)
    except Exception as e:
        print(f"Warning: Could not delete temp file: {e}")

    # ✅ Send Email
    msg = EmailMultiAlternatives(
        subject,
        text_body,
        settings.DEFAULT_FROM_EMAIL,
        [client.email],
        bcc=getattr(settings, "COA_INTERNAL_RECIPIENTS", [])
    )
    msg.attach_alternative(html_body, "text/html")
    msg.attach(filename, pdf_bytes, "application/pdf")
    msg.send()

    # ✅ Save path to client model
    if hasattr(client, "latest_coa_file"):
        client.latest_coa_file = path
        client.save(update_fields=["latest_coa_file"])



def notify_lab_manager_on_submission(manager_email, num_samples, organization_name, client_id, clerk_name):
    subject = "New Samples Submitted"

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <p>Hello <strong>Lab Manager</strong>,</p>

        <p>
          The clerk <strong>{clerk_name}</strong> has submitted <strong>{num_samples}</strong> sample(s)
          from <strong>{organization_name}</strong>.
        </p>

        <p><strong>Client ID:</strong> {client_id}</p>

        <p>
          👉 <a href="https://jaagee-lab.onrender.com/">Click here to assign tests</a>
        </p>

        <p>Thank you for your attention.</p>

        <p style="margin-top: 30px;">
          Regards,<br>
          <strong>JaaGee LIMS</strong>
        </p>
      </body>
    </html>
    """

    # Plain-text fallback
    text_content = strip_tags(html_content)

    msg = EmailMultiAlternatives(
        subject,
        text_content,
        settings.DEFAULT_FROM_EMAIL,
        [manager_email]
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()




def notify_client_on_submission(client_email, num_samples, parameter_list, client_id, client_token):
    subject = "Your Samples Have Been Received"

    parameter_str = ", ".join(parameter_list)

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <p>Dear <strong>Client</strong>,</p>

        <p>Thank you for submitting <strong>{num_samples}</strong> sample(s) to our laboratory.</p>

        <p><strong>Tests requested:</strong> {parameter_str}</p>
        <p><strong>Client ID:</strong> {client_id}<br>
           <strong>Tracking Token:</strong> {client_token}</p>

        <p>You can use this token to track your sample status and view your results once they are ready.</p>

        <p>
          👉 <a href="https://jaagee-lab.onrender.com/">Click here to track your samples</a>
        </p>

        <p>Our team will begin processing your samples, and we’ll keep you updated throughout.</p>

        <p>Thank you for choosing <strong>JaaGee Laboratory</strong>.</p>

        <p style="margin-top: 30px;">
          Best regards,<br>
          <strong>JaaGee LIMS</strong>
        </p>
      </body>
    </html>
    """

    # plain text fallback
    text_content = strip_tags(html_content)

    msg = EmailMultiAlternatives(
        subject,
        text_content,
        settings.DEFAULT_FROM_EMAIL,
        [client_email]
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()




def notify_analyst_by_email(analyst_email, analyst_name, sample_count, client_id, parameter_name):
    subject = f"New Test Assignment: {parameter_name}"

    html_content = f"""
    <html>
      <body>
        <p>Dear <strong>{analyst_name}</strong>,</p>

        <p>
          You have been assigned to analyze <strong>{sample_count} sample(s)</strong><br>
          <strong>Parameter:</strong> {parameter_name}<br>
          <strong>Client ID:</strong> {client_id}
        </p>

        <p>
          👉 <a href="https://jaagee-lab.onrender.com">Click here to view your assignments</a>
        </p>

        <p>
          Best regards,<br>
          <strong>JaaGee LIMS</strong>
        </p>
      </body>
    </html>
    """

    text_content = strip_tags(html_content)

    msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [analyst_email])
    msg.attach_alternative(html_content, "text/html")
    msg.send()

def notify_manager_on_result_submission(manager_email, analyst_name, client_id, parameter_name):
    subject = f"Result Submission Complete - {parameter_name}"

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <p>Dear <strong>Lab Manager</strong>,</p>

        <p>
          Analyst <strong>{analyst_name}</strong> has completed all test results for parameter
          <strong>{parameter_name}</strong> submitted under Client ID <strong>{client_id}</strong>.
        </p>

        <p>
          👉 <a href="https://jaagee-lab.onrender.com/">Click here to review the results</a>
        </p>

        <p style="margin-top: 30px;">
          Best regards,<br>
          <strong>JaaGee LIMS</strong>
        </p>
      </body>
    </html>
    """

    text_content = strip_tags(html_content)

    msg = EmailMultiAlternatives(
        subject,
        text_content,
        settings.DEFAULT_FROM_EMAIL,
        [manager_email]
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()
