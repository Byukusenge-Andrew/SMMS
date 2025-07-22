from django.contrib.auth.models import User
from django.db import models


class Notification(models.Model):
    TYPE_CHOICES = [
        ("post_published", "Post Published"),
        ("post_failed", "Post Failed"),
        ("campaign_application", "Campaign Application"),
        ("report_ready", "Report Ready"),
        ("analytics_alert", "Analytics Alert"),
        ("system", "System Notification"),
    ]

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="medium")

    # Metadata
    data = models.JSONField(default=dict, blank=True)

    # Status
    is_read = models.BooleanField(default=False)
    is_sent_email = models.BooleanField(default=False)
    is_sent_slack = models.BooleanField(default=False)

    # Action button
    action_url = models.URLField(blank=True)
    action_text = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.title}"


class NotificationPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="notification_preferences")

    # Email preferences
    email_post_updates = models.BooleanField(default=True)
    email_analytics_reports = models.BooleanField(default=True)
    email_campaign_updates = models.BooleanField(default=True)
    email_system_alerts = models.BooleanField(default=True)

    # Slack preferences
    slack_post_updates = models.BooleanField(default=False)
    slack_analytics_reports = models.BooleanField(default=False)
    slack_campaign_updates = models.BooleanField(default=False)
    slack_system_alerts = models.BooleanField(default=False)

    # In-app preferences
    app_notifications = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_preferences"

    def __str__(self):
        return f"{self.user.username} - Preferences"
