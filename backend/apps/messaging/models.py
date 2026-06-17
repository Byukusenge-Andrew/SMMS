import uuid

from django.contrib.auth.models import User
from django.db import models


class Message(models.Model):
    # Use UUID primary key to align with existing DB
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    """Model for individual messages"""

    PLATFORM_CHOICES = [
        ("instagram", "Instagram"),
        ("twitter", "Twitter"),
        ("facebook", "Facebook"),
        ("linkedin", "LinkedIn"),
        ("email", "Email"),
        ("sms", "SMS"),
    ]
    STATUS_CHOICES = [("pending", "Pending"), ("sent", "Sent"), ("failed", "Failed"), ("delivered", "Delivered")]
    TYPE_CHOICES = [("direct", "Direct"), ("automated", "Automated"), ("broadcast", "Broadcast")]
    PRIORITY_CHOICES = [("high", "High"), ("normal", "Normal"), ("low", "Low")]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="messages")
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    recipient = models.CharField(max_length=255)  # e.g., username, email, phone
    content = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    message_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="direct")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="normal")

    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "messages"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Message to {self.recipient} on {self.platform} ({self.status})"


class AutomatedMessage(models.Model):
    # Use UUID primary key to align with existing DB
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    """Model for automated message templates and triggers"""

    TRIGGER_CHOICES = [
        ("new_follower", "New Follower"),
        ("mention", "Mention"),
        ("comment", "Comment"),
        ("direct_message", "Direct Message"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="automated_messages")
    platform = models.CharField(max_length=20, choices=Message.PLATFORM_CHOICES)
    trigger = models.CharField(max_length=50, choices=TRIGGER_CHOICES, default="direct_message")
    content_template = models.TextField(
        default="Hello {username}! Thank you for your interaction.",
        help_text="Use placeholders like {username}, {follower_count}, etc."
    )
    delay_minutes = models.PositiveIntegerField(default=0, help_text="Delay in minutes before sending")
    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "automated_messages"
        ordering = ["-created_at"]
        unique_together = [["user", "platform", "trigger"]]

    def __str__(self):
        return f"Automated message for {self.trigger} on {self.platform}"
