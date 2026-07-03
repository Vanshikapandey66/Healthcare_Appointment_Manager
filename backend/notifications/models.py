from django.db import models
from users.models import User
from appointments.models import Appointment
from django.core.exceptions import ValidationError
from django.utils import timezone


class Notification(models.Model):
    TYPE_CHOICES = (
        ("booking_confirmation", "Booking Confirmation"),
        ("appointment_reminder", "Appointment Reminder"),
        ("appointment_cancelled", "Appointment Cancelled"),
        ("doctor_leave", "Doctor Leave"),
        ("medication_reminder", "Medication Reminder"),
    )

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("sent", "Sent"),
        ("failed", "Failed"),
    )

    CHANNEL_CHOICES = (
        ("email", "Email"),
        ("sms", "SMS"),
        ("push", "Push Notification"),
    )

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.SET_NULL,
        related_name="notifications",
        null=True,
        blank=True
    )

    notification_type = models.CharField(
        max_length=50,
        choices=TYPE_CHOICES
    )

    channel = models.CharField(
        max_length=20,
        choices=CHANNEL_CHOICES,
        default="email"
    )

    subject = models.CharField(
        max_length=255
    )

    message = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    retry_count = models.PositiveIntegerField(
        default=0
    )

    scheduled_for = models.DateTimeField(
        null=True,
        blank=True
    )

    sent_at = models.DateTimeField(
        null=True,
        blank=True
    )

    error_message = models.TextField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def clean(self):

        # Edge Case 1: Empty subject
        if not self.subject.strip():
            raise ValidationError(
                "Subject cannot be empty."
            )

        # Edge Case 2: Empty message
        if not self.message.strip():
            raise ValidationError(
                "Message cannot be empty."
            )

        # Edge Case 3: Retry overflow
        if self.retry_count > 3:
            raise ValidationError(
                "Retry count cannot exceed 3."
            )

        # Edge Case 4: sent_at only when sent
        if self.status != "sent" and self.sent_at:
            raise ValidationError(
                "sent_at should only be set when notification is sent."
            )

        # Edge Case 5: sent notification must have sent_at
        if self.status == "sent" and not self.sent_at:
            raise ValidationError(
                "Sent notifications must have sent_at."
            )

        # Edge Case 6: Failed notification must store error
        if self.status == "failed" and not self.error_message:
            raise ValidationError(
                "Failed notification must store error message."
            )

        # Edge Case 7: Pending scheduled time cannot be in past
        if (
            self.scheduled_for
            and self.scheduled_for < timezone.now()
            and self.status == "pending"
        ):
            raise ValidationError(
                "Scheduled time cannot be in the past."
            )

        # Edge Case 8: Prevent duplicate pending notifications
        duplicate_notifications = Notification.objects.filter(
            recipient=self.recipient,
            appointment=self.appointment,
            notification_type=self.notification_type,
            scheduled_for=self.scheduled_for,
            status="pending"
        ).exclude(id=self.id)

        if duplicate_notifications.exists():
            raise ValidationError(
                "Duplicate pending notification exists."
            )

        # Edge Case 9: sent_at cannot be before created_at
        if (
            self.sent_at
            and self.created_at
            and self.sent_at < self.created_at
        ):
            raise ValidationError(
                "sent_at cannot be earlier than created_at."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.recipient.email} - "
            f"{self.notification_type} - "
            f"{self.status}"
        )