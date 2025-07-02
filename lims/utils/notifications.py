from django.core.mail import send_mail
from django.conf import settings

def notify_lab_manager_on_submission(manager_email, num_samples, organization_name, client_id, clerk_name):
    subject = "New Samples Submitted"
    message = (
        f"Hello Lab Manager,\n\n"
        f"The clerk ({clerk_name}) has submitted {num_samples} samples from {organization_name}.\n"
        f"Client ID: {client_id}\n\n"
        f"Please log into the dashboard to assign tests.\n\n"
        f"Regards,\nJaaGee LIMS"
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [manager_email],
        fail_silently=False
    )



def notify_client_on_submission(client_email, client_id, token):
    subject = "We have received your samples"
    message = (
        f"Thank you for submitting your samples.\n"
        f"Your client token is: {token}\n"
        "Keep this safe — you will need it to access your results later."
    )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [client_email])

def notify_manager_on_analyst_submission(manager_email, param_name, client_id):
    subject = f"Analyst submitted results for Client ID {client_id}"
    message = (
        f"The analyst has submitted results for parameter '{param_name}' "
        f"for Client ID {client_id}. Please review."
    )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [manager_email])

def notify_client_on_approval(client_email, token, client_portal_link):
    subject = "Your results are ready"
    message = (
        "Your test results are ready for viewing.\n"
        f"Use this token to access your results: {token}\n"
        f"Access them here: {client_portal_link}"
    )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [client_email])
