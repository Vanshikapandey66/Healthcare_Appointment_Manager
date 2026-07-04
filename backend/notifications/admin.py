from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "recipient",
        "notification_type",
        "status",
        "channel",
        "created_at"
    )

    list_filter = (
        "notification_type",
        "status",
        "channel"
    )

    search_fields = (
        "recipient__email",
        "subject",
        "message"
    )