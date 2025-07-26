"""
Serializers for the notifications app
"""

from django.utils import timezone

from rest_framework import serializers

from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model"""

    class Meta:
        model = Notification
        fields = [
            "id",
            "user",
            "type",
            "title",
            "message",
            "priority",
            "data",
            "is_read",
            "is_sent_email",
            "is_sent_slack",
            "action_url",
            "action_text",
            "created_at",
            "read_at",
            "expires_at",
        ]
        read_only_fields = ["id", "user", "created_at", "read_at", "is_sent_email", "is_sent_slack"]

    def update(self, instance, validated_data):
        """Mark as read when updated"""
        if "is_read" in validated_data and validated_data["is_read"] and not instance.is_read:
            instance.read_at = timezone.now()
        return super().update(instance, validated_data)


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for NotificationPreference model"""

    class Meta:
        model = NotificationPreference
        fields = [
            "id",
            "user",
            "notification_type",
            "email_enabled",
            "push_enabled",
            "slack_enabled",
            "frequency",
            "quiet_hours_start",
            "quiet_hours_end",
            "timezone",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]


class NotificationStatsSerializer(serializers.Serializer):
    """Serializer for notification statistics"""

    total_notifications = serializers.IntegerField()
    unread_count = serializers.IntegerField()
    today_count = serializers.IntegerField()
    this_week_count = serializers.IntegerField()
    by_type = serializers.DictField()
    by_priority = serializers.DictField()


class BulkMarkReadSerializer(serializers.Serializer):
    """Serializer for bulk marking notifications as read"""

    notification_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=True, required=False)
    mark_all = serializers.BooleanField(default=False)

    def validate(self, data):
        """Validate that either notification_ids or mark_all is provided"""
        if not data.get("mark_all") and not data.get("notification_ids"):
            raise serializers.ValidationError("Either 'mark_all' must be True or 'notification_ids' must be provided")
        return data


class NotificationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating notifications (admin use)"""

    class Meta:
        model = Notification
        fields = ["type", "title", "message", "priority", "data", "action_url", "action_text", "expires_at"]
