from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification, NotificationPreference
from .serializers import (BulkMarkReadSerializer, NotificationCreateSerializer,
                          NotificationPreferenceSerializer,
                          NotificationSerializer, NotificationStatsSerializer)


class NotificationListView(generics.ListAPIView):
    """API view to list notifications for a user"""

    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        """Return notifications for the authenticated user"""
        return Notification.objects.filter(user=self.request.user).order_by("-created_at")

    def list(self, request, *args, **kwargs):
        """Return notifications with additional metadata"""
        queryset = self.filter_queryset(self.get_queryset())

        # Count unread notifications
        unread_count = queryset.filter(is_read=False).count()

        # Serialize notifications
        serializer = self.get_serializer(queryset, many=True)

        return Response({"notifications": serializer.data, "unread_count": unread_count, "total_count": queryset.count()})


class NotificationDetailView(generics.RetrieveUpdateAPIView):
    """API view to retrieve and update a specific notification"""

    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        """Return only notifications for the authenticated user"""
        return Notification.objects.filter(user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        """Mark notification as read when accessed"""
        notification = self.get_object()
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save()

        serializer = self.get_serializer(notification)
        return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_all_read(request):
    """Mark all notifications as read for the authenticated user"""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True, read_at=timezone.now())
    return Response({"status": "success", "message": "All notifications marked as read"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bulk_mark_read(request):
    """Mark multiple notifications as read"""
    serializer = BulkMarkReadSerializer(data=request.data)
    if serializer.is_valid():
        if serializer.validated_data.get("mark_all"):
            count = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True, read_at=timezone.now())
        else:
            notification_ids = serializer.validated_data.get("notification_ids", [])
            count = Notification.objects.filter(user=request.user, id__in=notification_ids, is_read=False).update(
                is_read=True, read_at=timezone.now()
            )

        return Response({"status": "success", "message": f"{count} notifications marked as read"})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def notification_stats(request):
    """Get notification statistics for the user"""
    user_notifications = Notification.objects.filter(user=request.user)

    today = timezone.now().date()
    week_ago = today - timedelta(days=7)

    stats = {
        "total_notifications": user_notifications.count(),
        "unread_count": user_notifications.filter(is_read=False).count(),
        "today_count": user_notifications.filter(created_at__date=today).count(),
        "this_week_count": user_notifications.filter(created_at__date__gte=week_ago).count(),
        "by_type": dict(user_notifications.values("type").annotate(count=Count("type")).values_list("type", "count")),
        "by_priority": dict(
            user_notifications.values("priority").annotate(count=Count("priority")).values_list("priority", "count")
        ),
    }

    serializer = NotificationStatsSerializer(stats)
    return Response(serializer.data)


@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def notification_preferences(request):
    """Get or update notification preferences"""
    preferences, created = NotificationPreference.objects.get_or_create(
        user=request.user,
        defaults={
            "notification_type": "all",
            "email_enabled": True,
            "push_enabled": True,
            "slack_enabled": False,
            "frequency": "instant",
            "timezone": "UTC",
        },
    )

    if request.method == "GET":
        serializer = NotificationPreferenceSerializer(preferences)
        return Response(serializer.data)

    # Update preferences
    serializer = NotificationPreferenceSerializer(preferences, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response({"status": "success", "message": "Notification preferences updated"})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def send_test_notification(request):
    """Create a test notification for the user"""
    notification = Notification.objects.create(
        user=request.user,
        type="system",
        title="Test Notification",
        message="This is a test notification from the system.",
        priority="medium",
        action_url="/dashboard/",
        action_text="View Dashboard",
    )

    return Response({"status": "success", "message": "Test notification sent", "notification_id": notification.id})


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def clear_all_notifications(request):
    """Clear all notifications for the user"""
    count = Notification.objects.filter(user=request.user).count()
    Notification.objects.filter(user=request.user).delete()

    return Response({"status": "success", "message": f"Cleared {count} notifications"})
