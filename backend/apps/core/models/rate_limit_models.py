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
        verbose_name = "Rate Limit Rule"
        verbose_name_plural = "Rate Limit Rules"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.user_type})"

    def clean(self):
        """Validate rule parameters"""
        from django.core.exceptions import ValidationError

        if self.bucket_capacity <= 0:
            raise ValidationError("Bucket capacity must be positive")

        if self.refill_rate <= 0:
            raise ValidationError("Refill rate must be positive")

        if self.max_requests <= 0:
            raise ValidationError("Max requests must be positive")

        if self.window_size <= 0:
            raise ValidationError("Window size must be positive")


class RateLimitLog(models.Model):
    """
    Logs rate limiting events for monitoring and analysis
    """

    BLOCK_TYPE_CHOICES = [
        ("token_bucket", "Token Bucket"),
        ("sliding_window", "Sliding Window"),
        ("both", "Both"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    endpoint = models.CharField(max_length=200)
    method = models.CharField(max_length=10)

    # Rate Limiting Details
    rule_applied = models.ForeignKey(RateLimitRule, on_delete=models.SET_NULL, null=True)
    block_type = models.CharField(max_length=20, choices=BLOCK_TYPE_CHOICES, default="both")
    tokens_remaining = models.IntegerField(null=True, blank=True)
    requests_in_window = models.IntegerField(null=True, blank=True)

    # Timestamps
    timestamp = models.DateTimeField(default=timezone.now)
    blocked_at = models.DateTimeField(null=True, blank=True, help_text="Specific time of block if applicable")
    retry_after = models.DateTimeField(null=True, blank=True)

    # Added fields for monitoring
    user_type = models.CharField(max_length=20, blank=True)
    action = models.CharField(max_length=20, default="denied")
    algorithm_used = models.CharField(max_length=50, blank=True)
    requests_remaining = models.IntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Rate Limit Log"
        verbose_name_plural = "Rate Limit Logs"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["ip_address", "-timestamp"]),
            models.Index(fields=["user", "-timestamp"]),
            models.Index(fields=["endpoint", "-timestamp"]),
        ]

    def __str__(self):
        user_info = self.user.username if self.user else self.ip_address
        return f"{user_info} - {self.endpoint} ({self.timestamp})"


class RateLimitStats(models.Model):
    """
    Aggregated statistics for rate limiting monitoring
    """

    PERIOD_CHOICES = [
        ("hourly", "Hourly"),
        ("daily", "Daily"),
        ("weekly", "Weekly"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Provide default to simplify future migrations / data creation
    period_type = models.CharField(max_length=10, choices=PERIOD_CHOICES, default="hourly")
    date = models.DateField(default=timezone.now)
    hour = models.IntegerField(default=0)
    
    # Statistics
    total_requests = models.BigIntegerField(default=0)
    allowed_requests = models.BigIntegerField(default=0)
    denied_requests = models.BigIntegerField(default=0)
    blocked_requests = models.BigIntegerField(default=0)
    burst_protections = models.BigIntegerField(default=0)
    
    # User types
    anonymous_requests = models.BigIntegerField(default=0)
    authenticated_requests = models.BigIntegerField(default=0)
    premium_requests = models.BigIntegerField(default=0)
    admin_requests = models.BigIntegerField(default=0)
    
    # Performance
    average_tokens_remaining = models.FloatField(default=0.0)
    average_requests_remaining = models.FloatField(default=0.0)
    peak_requests_per_minute = models.IntegerField(default=0)

    unique_ips = models.IntegerField(default=0)
    unique_users = models.IntegerField(default=0)

    # Top endpoints by blocks
    top_blocked_endpoints = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Rate Limit Stats"
        verbose_name_plural = "Rate Limit Stats"
        unique_together = ["date", "hour"]
        ordering = ["-date", "-hour"]

    def __str__(self):
        return f"{self.period_type.title()} Stats ({self.date})"

    @property
    def block_percentage(self):
        """Calculate percentage of blocked requests"""
        if self.total_requests == 0:
            return 0
        return round((self.blocked_requests / self.total_requests) * 100, 2)


class IPWhitelist(models.Model):
    """
    IP addresses exempt from rate limiting
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ip_address = models.GenericIPAddressField(unique=True)
    description = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "IP Whitelist"
        verbose_name_plural = "IP Whitelists"
        ordering = ["ip_address"]

    def __str__(self):
        return f"{self.ip_address} - {self.description}"


class IPBlacklist(models.Model):
    """
    IP addresses completely blocked from accessing the API
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ip_address = models.GenericIPAddressField(unique=True)
    reason = models.CharField(max_length=200)
    blocked_until = models.DateTimeField(null=True, blank=True, help_text="Leave blank for permanent block")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "IP Blacklist"
        verbose_name_plural = "IP Blacklists"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.ip_address} - {self.reason}"

    @property
    def is_expired(self):
        """Check if the block has expired"""
        if not self.blocked_until:
            return False
        return timezone.now() > self.blocked_until

    def save(self, *args, **kwargs):
        # Auto-deactivate expired blocks
        if self.is_expired:
            self.is_active = False
        super().save(*args, **kwargs)
