from rest_framework import serializers
from django.utils import timezone
from .models import Notification


class NotificationListSerializer(serializers.ModelSerializer):
    recipient_email = serializers.CharField(
        source="recipient.email",
        read_only=True
    )

    class Meta:
        model = Notification
        fields = (
            "id",
            "recipient_email",
            "notification_type",
            "channel",
            "status",
            "scheduled_for",
            "sent_at",
            "created_at"
        )


class NotificationDetailSerializer(serializers.ModelSerializer):
    recipient_email = serializers.CharField(
        source="recipient.email",
        read_only=True
    )

    class Meta:
        model = Notification
        fields = "__all__"


class NotificationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = (
            "recipient",
            "appointment",
            "notification_type",
            "channel",
            "subject",
            "message",
            "scheduled_for"
        )

    def validate(self, attrs):
        scheduled_for = attrs.get("scheduled_for")
        appointment = attrs.get("appointment")
        recipient = attrs.get("recipient")

        # EC10
        if scheduled_for and scheduled_for < timezone.now():
            raise serializers.ValidationError(
                "Scheduled time cannot be in past."
            )

        # NEW FIX 1
        # appointment linked notification wrong user ko na jaaye
        if appointment:
            patient_user = appointment.patient.user
            doctor_user = appointment.slot.doctor.user

            if recipient not in [patient_user, doctor_user]:
                raise serializers.ValidationError(
                    "Recipient must be appointment patient or doctor."
                )

        return attrs


class NotificationStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = (
            "status",
            "sent_at",
            "error_message"
        )

    def validate(self, attrs):
        notification = self.instance
        new_status = attrs.get(
            "status",
            notification.status
        )

        old_status = notification.status

        if old_status == "sent":
            raise serializers.ValidationError(
                "Sent notification cannot be modified."
            )

        if (
            old_status == "failed"
            and new_status == "failed"
        ):
            raise serializers.ValidationError(
                "Already failed."
            )

        if (
            new_status == "sent"
            and not attrs.get("sent_at")
        ):
            raise serializers.ValidationError(
                "sent_at required when sent."
            )

        if (
            new_status == "failed"
            and not attrs.get("error_message")
        ):
            raise serializers.ValidationError(
                "error_message required."
            )

        return attrs