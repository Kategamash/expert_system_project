from .models import Notification

def notify(user, message: str, link: str = "", process=None):
    if user is None:
        return
    Notification.objects.create(user=user, message=message, link=link, process=process)