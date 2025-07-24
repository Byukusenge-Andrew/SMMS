import uuid

from django.contrib.auth.models import User
from django.db import models


class Message(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("sent", "Sent"),
        ("failed", "Failed"),
        ("delivered", "Delivered"),
        ("read", "Read"),
    ]

    PRIORITY_CHOICES = [("low", "Low"), ("normal", "Normal"), ("high", "High"), ("urgent", "Urgent")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="messages")
    platform = models.CharField(max_length=50)
    recipient = models.CharField(max_length=255)  # username, email, or ID
    content = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="normal")

    # Scheduling
    scheduled_time = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    # Response tracking
    response_received = models.BooleanField(default=False)
    response_content = models.TextField(blank=True)
    response_time = models.DateTimeField(null=True, blank=True)

    # Metadata
    message_type = models.CharField(max_length=50, default="direct")  # direct, automated, broadcast
    campaign_id = models.UUIDField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "messages"
        ordering = ["-created_at"]


class AutomatedMessage(models.Model):
    TRIGGER_CHOICES = [
        ("new_follower", "New Follower"),
        ("mention", "Mention"),
        ("comment", "Comment"),
        ("dm", "Direct Message"),
        ("scheduled", "Scheduled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="automated_messages")
    name = models.CharField(max_length=255)
    trigger_type = models.CharField(max_length=20, choices=TRIGGER_CHOICES)
    platform = models.CharField(max_length=50)
    template_content = models.TextField()

    # Conditions
    conditions = models.JSONField(default=dict)  # follower count, keywords, etc.

    # Timing
    delay_minutes = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "automated_messages"
