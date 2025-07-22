from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification, NotificationPreference


class NotificationListView(generics.ListAPIView):
    """API view to list notifications for a user"""

    permission_classes = [IsAuthenticated]
    # serializer_class = NotificationSerializer  # You'll need to create this

    def get_queryset(self):
        """Return notifications for the authenticated user"""
        return Notification.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        """Return notifications with additional metadata"""
        queryset = self.filter_queryset(self.get_queryset())

        # Count unread notifications
        unread_count = queryset.filter(is_read=False).count()

        # Serialize notifications
        # serializer = self.get_serializer(queryset, many=True)

        # For simplicity, returning just basic data until serializer is created
        notifications = []
        for notification in queryset:
            notifications.append(
                {
                    "id": notification.id,
                    "type": notification.type,
                    "title": notification.title,
                    "message": notification.message,
                    "is_read": notification.is_read,
                    "created_at": notification.created_at.isoformat(),
                    "priority": notification.priority,
                }
            )

        return Response({"notifications": notifications, "unread_count": unread_count, "total_count": len(notifications)})


class NotificationDetailView(generics.RetrieveUpdateAPIView):
    """API view to retrieve and update a specific notification"""

    permission_classes = [IsAuthenticated]
    # serializer_class = NotificationSerializer

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

        # For simplicity, returning basic data until serializer is created
        notification_data = {
            "id": notification.id,
            "type": notification.type,
            "title": notification.title,
            "message": notification.message,
            "is_read": notification.is_read,
            "created_at": notification.created_at.isoformat(),
            "read_at": notification.read_at.isoformat() if notification.read_at else None,
            "priority": notification.priority,
            "data": notification.data,
            "action_url": notification.action_url,
            "action_text": notification.action_text,
        }

        return Response(notification_data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_all_read(request):
    """Mark all notifications as read for the authenticated user"""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True, read_at=timezone.now())

    return Response({"status": "success", "message": "All notifications marked as read"})


@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def notification_preferences(request):
    """Get or update notification preferences"""
    # Get or create preferences for this user
    preferences, created = NotificationPreference.objects.get_or_create(user=request.user)

    if request.method == "GET":
        # Return current preferences
        return Response(
            {
                "email_preferences": {
                    "post_updates": preferences.email_post_updates,
                    "analytics_reports": preferences.email_analytics_reports,
                    "campaign_updates": preferences.email_campaign_updates,
                    "system_alerts": preferences.email_system_alerts,
                },
                "slack_preferences": {
                    "post_updates": preferences.slack_post_updates,
                    "analytics_reports": preferences.slack_analytics_reports,
                    "campaign_updates": preferences.slack_campaign_updates,
                    "system_alerts": preferences.slack_system_alerts,
                },
                "app_notifications": preferences.app_notifications,
            }
        )

    # Update preferences
    if "email_preferences" in request.data:
        email_prefs = request.data["email_preferences"]
        if "post_updates" in email_prefs:
            preferences.email_post_updates = email_prefs["post_updates"]
        if "analytics_reports" in email_prefs:
            preferences.email_analytics_reports = email_prefs["analytics_reports"]
        if "campaign_updates" in email_prefs:
            preferences.email_campaign_updates = email_prefs["campaign_updates"]
        if "system_alerts" in email_prefs:
            preferences.email_system_alerts = email_prefs["system_alerts"]

    if "slack_preferences" in request.data:
        slack_prefs = request.data["slack_preferences"]
        if "post_updates" in slack_prefs:
            preferences.slack_post_updates = slack_prefs["post_updates"]
        if "analytics_reports" in slack_prefs:
            preferences.slack_analytics_reports = slack_prefs["analytics_reports"]
        if "campaign_updates" in slack_prefs:
            preferences.slack_campaign_updates = slack_prefs["campaign_updates"]
        if "system_alerts" in slack_prefs:
            preferences.slack_system_alerts = slack_prefs["system_alerts"]

    if "app_notifications" in request.data:
        preferences.app_notifications = request.data["app_notifications"]

    preferences.save()

    return Response({"status": "success", "message": "Notification preferences updated"})


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
