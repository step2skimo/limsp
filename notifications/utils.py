from .models import Notification

def notify(user, message):
    Notification.objects.create(recipient=user, message=message)
