from django.urls import path
from .views import (
    NotificationListView,
    NotificationDetailView,
    NotificationCreateView,
    NotificationStatusUpdateView,
    NotificationRetryView,
    NotificationDeleteView
)

urlpatterns = [
    path(
        "",
        NotificationListView.as_view(),
        name="notification-list"
    ),

    path(
        "create/",
        NotificationCreateView.as_view(),
        name="notification-create"
    ),

    path(
        "<int:notification_id>/",
        NotificationDetailView.as_view(),
        name="notification-detail"
    ),

    path(
        "<int:notification_id>/status/",
        NotificationStatusUpdateView.as_view(),
        name="notification-status"
    ),

    path(
        "<int:notification_id>/retry/",
        NotificationRetryView.as_view(),
        name="notification-retry"
    ),

    path(
        "<int:notification_id>/delete/",
        NotificationDeleteView.as_view(),
        name="notification-delete"
    ),
]