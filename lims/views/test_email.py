from django.core.mail import send_mail
from django.http import HttpResponse

def test_email(request):
    send_mail(
        subject="Test Email from LIMS",
        message="This is a test email. If you received it, SMTP is working.",
        from_email=None,  # uses DEFAULT_FROM_EMAIL
        recipient_list=["isnevisaac@gmail.com"],  # change to your inbox
        fail_silently=False,
    )
    return HttpResponse("Test email sent!")
