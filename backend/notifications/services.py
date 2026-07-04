from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

from .models import Notification


def send_notification_email(notification):

    # Edge case 1: recipient email missing
    if not notification.recipient.email:
        notification.status = "failed"
        notification.error_message = "Recipient email missing."
        notification.save()
        return False

    # Edge case 2: already sent notification
    if notification.status == "sent":
        notification.error_message = "Notification already sent."
        notification.save()
        return False

    # Edge case 3: retry limit exceeded
    if notification.retry_count >= 3:
        notification.status = "failed"
        notification.error_message = "Retry limit exceeded."
        notification.save()
        return False

    try:
        send_mail(
            subject=notification.subject,
            message=notification.message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[notification.recipient.email],
            fail_silently=False
        )

        notification.status = "sent"
        notification.sent_at = timezone.now()
        notification.error_message = None
        notification.save()

        return True

    except Exception as e:
        notification.status = "failed"
        notification.retry_count += 1
        notification.error_message = str(e)
        notification.save()

        return False