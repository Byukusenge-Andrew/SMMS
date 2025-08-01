"""
Models for rate limiting configuration and monitoring
"""

import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class RateLimitRule(models.Model):
    """
    Database-configurable rate limiting rules
    Allows dynamic adjustment of rate limits without code changes
    """

    ALGORITHM_CHOICES = [
        ("token_bucket", "Token Bucket"),
        ("sliding_window", "Sliding Window"),
        ("both", "Both Algorithms"),
    ]

    USER_TYPE_CHOICES = [
        ("anonymous", "Anonymous"),
        ("authenticated", "Authenticated"),
        ("premium", "Premium"),
        ("admin", "Admin"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, help_text="Rule name for identification")
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    algorithm = models.CharField(max_length=20, choices=ALGORITHM_CHOICES, default="both")

    # Token Bucket Configuration
    bucket_capacity = models.IntegerField(default=100, help_text="Maximum tokens in bucket")
    refill_rate = models.FloatField(default=1.0, help_text="Tokens per second refill rate")

    # Sliding Window Configuration
    max_requests = models.IntegerField(default=1000, help_text="Maximum requests in window")
    window_size = models.IntegerField(default=3600, help_text="Window size in seconds")

    # Rule Management
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        unique_together = ["user_type", "is_active"]
        ordering = ["user_type", "-created_at"]

    def __str__(self):
        return f"{self.name} ({self.user_type})"


class RateLimitLog(models.Model):
    """
    Log rate limiting events for monitoring and analysis
    """

    ACTION_CHOICES = [
        ("allowed", "Request Allowed"),
        ("denied", "Request Denied"),
        ("burst_protection", "Burst Protection Triggered"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(default=timezone.now)

    # Request Information
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    endpoint = models.CharField(max_length=255)
    method = models.CharField(max_length=10)

    # Rate Limiting Information
    user_type = models.CharField(max_length=20)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    algorithm_used = models.CharField(max_length=20)

    # Metadata
    tokens_remaining = models.IntegerField(null=True, blank=True)
    requests_remaining = models.IntegerField(null=True, blank=True)
    retry_after = models.IntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["timestamp", "action"]),
            models.Index(fields=["user", "timestamp"]),
            models.Index(fields=["ip_address", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.action} - {self.user_type} - {self.timestamp}"


class RateLimitStats(models.Model):
    """
    Aggregated statistics for rate limiting monitoring
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField()
    hour = models.IntegerField(help_text="Hour of the day (0-23)")

    # Counters
    total_requests = models.IntegerField(default=0)
    allowed_requests = models.IntegerField(default=0)
    denied_requests = models.IntegerField(default=0)
    burst_protections = models.IntegerField(default=0)

    # By User Type
    anonymous_requests = models.IntegerField(default=0)
    authenticated_requests = models.IntegerField(default=0)
    premium_requests = models.IntegerField(default=0)
    admin_requests = models.IntegerField(default=0)

    # Performance Metrics
    average_tokens_remaining = models.FloatField(default=0.0)
    average_requests_remaining = models.FloatField(default=0.0)
    peak_requests_per_minute = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["date", "hour"]
        ordering = ["-date", "-hour"]

    def __str__(self):
        return f"Stats for {self.date} {self.hour:02d}:00"


class IPWhitelist(models.Model):
    """
    IP addresses that bypass rate limiting
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ip_address = models.GenericIPAddressField(unique=True)
    description = models.CharField(max_length=255, help_text="Reason for whitelisting")
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        ordering = ["ip_address"]

    def __str__(self):
        return f"{self.ip_address} - {self.description}"


class IPBlacklist(models.Model):
    """
    IP addresses that are completely blocked
    """

    REASON_CHOICES = [
        ("abuse", "Abuse"),
        ("spam", "Spam"),
        ("security", "Security Threat"),
        ("manual", "Manual Block"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ip_address = models.GenericIPAddressField(unique=True)
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    # Auto-expiry
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Block expires at this time")

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.ip_address} - {self.reason}"

    @property
    def is_expired(self):
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
