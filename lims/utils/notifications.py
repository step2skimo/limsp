from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.template.loader import render_to_string
from django.conf import settings
from weasyprint import HTML
from django.utils import timezone
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import tempfile, datetime, os, uuid

import uuid
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.templatetags.static import static

def notify_low_stock(manager_email, reagent_name, batch_number, number_of_bottles, threshold):
    subject = f"⚠️ Low Stock Alert: {reagent_name}"
    message_id = f"<{uuid.uuid4()}@jaageelab.com>"

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
        <h2 style="color:#d9534f;">⚠️ Low Stock Alert</h2>
        <p>Hello <strong>Lab Manager</strong>,</p>
        <p>
          The reagent <strong>{reagent_name}</strong> (Batch: <strong>{batch_number}</strong>)
          has dropped to <strong>{number_of_bottles} bottle(s)</strong>, which is below the threshold of <strong>{threshold}</strong>.
        </p>
        <p style="color:red;"><strong>Action Required: Please review and restock as necessary.</strong></p>
        <p>👉 <a href="https://jaagee-lab.onrender.com" style="color:#0073e6;">Go to Reagent Inventory</a></p>
        <p style="margin-top:20px;">Regards,<br><strong>JaaGee LIMS Team</strong></p>
        <hr style="border:0;height:1px;background:#ddd;">
        <p style="font-size:12px;color:#999;">This is an automated alert from JaaGee LIMS. Please do not reply.</p>
      </body>
    </html>
    """
    text_content = f"""
    Low Stock Alert:

    Reagent: {reagent_name}
    Batch: {batch_number}
    Current Stock: {number_of_bottles} bottle(s)
    Threshold: {threshold}

    Action Required: Please review and restock.
    Dashboard: https://jaagee-lab.onrender.com
    """

    email = EmailMultiAlternatives(
        subject, text_content, settings.DEFAULT_FROM_EMAIL, [manager_email],
        headers={'Reply-To': 'jaageelab@gmail.com', 'Message-ID': message_id}
    )
    email.attach_alternative(html_content, "text/html")
    email.send()





def notify_client_on_coa_release(*, client, summary_text, attachments=None, pdf_bytes=None, filename=None):
    """
    Email the client letting them know their COA is ready.
    Supports multiple PDF attachments (via 'attachments' list).
    If 'attachments' is not provided, falls back to a single (pdf_bytes, filename).
    """
    subject = "Your Certificate of Analysis (COA) is Now Available"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_list = [client.email]
    bcc_list = getattr(settings, "COA_INTERNAL_RECIPIENTS", [])
    message_id = f"<{uuid.uuid4()}@jaageelab.com>"

    # Fallback letterhead URL
    letterhead_url = static("letterheads/coa_letterhead.png")

    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color:#333; line-height:1.6;">
        <h2 style="color:#0073e6;">Certificate of Analysis Released</h2>
        <p>Dear <strong>{client.name}</strong>,</p>
        <p>The COA for your submitted samples (Client ID: <strong>{client.client_id}</strong>) is now available.</p>
        <hr>
        <p><strong>Summary Interpretation:</strong></p>
        <p>{summary_text}</p>
        <p style="margin-top:20px;">Thank you for choosing <strong>JaaGee Laboratory</strong>.</p>
        <p>Best regards,<br><strong>JaaGee LIMS Team</strong></p>
        <hr style="border:0;height:1px;background:#ddd;">
        <p style="font-size:12px;color:#999;">Confidential COA PDF attached.</p>
        <p style="font-size:11px;color:#bbb;">If you cannot open the attachment, please reply to this email.</p>
      </body>
    </html>
    """

    text_body = (
        f"Dear {client.name},\n\n"
        f"The Certificate of Analysis (COA) for your samples (Client ID: {client.client_id}) is ready.\n\n"
        f"Summary:\n{summary_text}\n\n"
        "The PDF(s) are attached.\n\n"
        "Thank you for choosing JaaGee Laboratory.\n"
    )

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=from_email,
        to=to_list,
        bcc=bcc_list,
        headers={'Reply-To': 'jaageelab@gmail.com', 'Message-ID': message_id}
    )
    msg.attach_alternative(html_body, "text/html")

    # Attach PDFs (multiple or single)
    if attachments:
        for file_name, content in attachments:
            msg.attach(file_name, content, "application/pdf")
    elif pdf_bytes and filename:
        msg.attach(filename, pdf_bytes, "application/pdf")

    msg.send()


def notify_lab_manager_on_submission(manager_email, num_samples, organization_name, client_id, clerk_name):
    subject = "New Samples Submitted"
    message_id = f"<{uuid.uuid4()}@jaageelab.com>"

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color:#333; line-height:1.6;">
        <h2 style="color:#0073e6;">New Sample Submission</h2>
        <p>Hello <strong>Lab Manager</strong>,</p>
        <p>The clerk <strong>{clerk_name}</strong> has submitted <strong>{num_samples}</strong> sample(s)
        from <strong>{organization_name}</strong>.</p>
        <p><strong>Client ID:</strong> {client_id}</p>
        <p>👉 <a href="https://jaagee-lab.onrender.com" style="color:#0073e6;">Assign Tests</a></p>
        <p style="margin-top:20px;">Regards,<br><strong>JaaGee LIMS Team</strong></p>
      </body>
    </html>
    """
    text_content = f"""
    New Sample Submission:

    Clerk: {clerk_name}
    Organization: {organization_name}
    Number of Samples: {num_samples}
    Client ID: {client_id}

    Assign tests here: https://jaagee-lab.onrender.com
    """

    msg = EmailMultiAlternatives(
        subject, text_content, settings.DEFAULT_FROM_EMAIL, [manager_email],
        headers={'Reply-To': 'jaageelab@gmail.com', 'Message-ID': message_id}
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()


def notify_client_on_submission(client_email, num_samples, parameter_list, client_id, client_token):
    subject = "Your Samples Have Been Received"
    message_id = f"<{uuid.uuid4()}@jaageelab.com>"
    parameter_str = ", ".join(parameter_list)

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color:#333; line-height:1.6;">
        <h2 style="color:#0073e6;">Sample Submission Confirmation</h2>
        <p>Dear <strong>Client</strong>,</p>
        <p>Thank you for submitting <strong>{num_samples}</strong> sample(s).</p>
        <p><strong>Tests:</strong> {parameter_str}<br>
        <strong>Client ID:</strong> {client_id}<br>
        <strong>Tracking Token:</strong> {client_token}</p>
        <p>Track your sample status <a href="https://jaagee-lab.onrender.com" style="color:#0073e6;">here</a>.</p>
        <p>Thank you for choosing JaaGee Laboratory.</p>
      </body>
    </html>
    """
    text_content = f"""
    Thank you for submitting {num_samples} sample(s).

    Tests: {parameter_str}
    Client ID: {client_id}
    Tracking Token: {client_token}

    Track your samples: https://jaagee-lab.onrender.com
    """

    msg = EmailMultiAlternatives(
        subject, text_content, settings.DEFAULT_FROM_EMAIL, [client_email],
        headers={'Reply-To': 'jaageelab@gmail.com', 'Message-ID': message_id}
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()


def notify_analyst_by_email(analyst_email, analyst_name, sample_count, client_id, parameter_name):
    subject = f"New Test Assignment: {parameter_name}"
    message_id = f"<{uuid.uuid4()}@jaageelab.com>"

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color:#333; line-height:1.6;">
        <p>Dear <strong>{analyst_name}</strong>,</p>
        <p>You have been assigned <strong>{sample_count}</strong> sample(s).</p>
        <p><strong>Parameter:</strong> {parameter_name}<br>
        <strong>Client ID:</strong> {client_id}</p>
        <p><a href="https://jaagee-lab.onrender.com" style="color:#0073e6;">View Assignments</a></p>
      </body>
    </html>
    """
    text_content = f"""
    You have been assigned {sample_count} sample(s).

    Parameter: {parameter_name}
    Client ID: {client_id}

    View your assignments: https://jaagee-lab.onrender.com
    """

    msg = EmailMultiAlternatives(
        subject, text_content, settings.DEFAULT_FROM_EMAIL, [analyst_email],
        headers={'Reply-To': 'jaageelab@gmail.com', 'Message-ID': message_id}
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()


def notify_manager_on_result_submission(manager_email, analyst_name, client_id, parameter_name):
    subject = f"Result Submission Complete - {parameter_name}"
    message_id = f"<{uuid.uuid4()}@jaageelab.com>"

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color:#333; line-height:1.6;">
        <p>Dear <strong>Lab Manager</strong>,</p>
        <p>Analyst <strong>{analyst_name}</strong> has completed results for parameter <strong>{parameter_name}</strong>
        under Client ID <strong>{client_id}</strong>.</p>
        <p><a href="https://jaagee-lab.onrender.com" style="color:#0073e6;">Review Results</a></p>
      </body>
    </html>
    """
    text_content = f"""
    Analyst {analyst_name} has completed results for parameter: {parameter_name}
    Client ID: {client_id}

    Review results: https://jaagee-lab.onrender.com
    """

    msg = EmailMultiAlternatives(
        subject, text_content, settings.DEFAULT_FROM_EMAIL, [manager_email],
        headers={'Reply-To': 'jaageelab@gmail.com', 'Message-ID': message_id}
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()
