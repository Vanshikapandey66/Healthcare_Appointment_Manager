from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .services import send_notification_email
from .models import Notification
from .serializers import (
    NotificationListSerializer,
    NotificationDetailSerializer,
    NotificationCreateSerializer,
    NotificationStatusSerializer
)


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(
            recipient=request.user
        ).order_by("-created_at")

        serializer = NotificationListSerializer(
            notifications,
            many=True
        )

        return Response(serializer.data)


class NotificationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, notification_id):
        try:
            notification = Notification.objects.get(
                id=notification_id
            )
        except Notification.DoesNotExist:
            return Response(
                {"error": "Notification not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # User only own notification dekh sakta
        if (
            request.user.role != "admin"
            and notification.recipient != request.user
        ):
            return Response(
                {"error": "Unauthorized access."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = NotificationDetailSerializer(
            notification
        )

        return Response(serializer.data)


class NotificationCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Only admin create kar sakta
        if request.user.role != "admin":
            return Response(
                {"error": "Only admin allowed."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = NotificationCreateSerializer(
            data=request.data
        )

        if serializer.is_valid():
            notification = serializer.save()
            send_notification_email(notification)

            return Response(
                {
                    "message": "Notification created successfully.",
                    "data": serializer.data
                },
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class NotificationStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, notification_id):
        # Only admin status update kar sakta
        if request.user.role != "admin":
            return Response(
                {"error": "Only admin allowed."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            notification = Notification.objects.get(
                id=notification_id
            )
        except Notification.DoesNotExist:
            return Response(
                {"error": "Notification not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = NotificationStatusSerializer(
            notification,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()

            return Response(
                {
                    "message": "Notification updated successfully.",
                    "data": serializer.data
                }
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class NotificationRetryView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id):
        # Only admin retry kar sakta
        if request.user.role != "admin":
            return Response(
                {"error": "Only admin allowed."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            notification = Notification.objects.get(
                id=notification_id
            )
        except Notification.DoesNotExist:
            return Response(
                {"error": "Notification not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Sirf failed notifications retry hongi
        if notification.status != "failed":
            return Response(
                {
                    "error":
                    "Only failed notifications can be retried."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Retry limit
        if notification.retry_count >= 3:
            return Response(
                {"error": "Retry limit exceeded."},
                status=status.HTTP_400_BAD_REQUEST
            )

        notification.status = "pending"
        notification.error_message = None
        notification.sent_at = None
        notification.save()

        send_notification_email(notification)

        return Response(
            {"message": "Retry initiated successfully."}
        )


class NotificationDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, notification_id):
        # Only admin delete kar sakta
        if request.user.role != "admin":
            return Response(
                {"error": "Only admin allowed."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            notification = Notification.objects.get(
                id=notification_id
            )
        except Notification.DoesNotExist:
            return Response(
                {"error": "Notification not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        notification.delete()

        return Response(
            {"message": "Notification deleted successfully."}
        )