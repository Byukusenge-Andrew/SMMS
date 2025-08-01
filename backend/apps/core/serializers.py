"""
Serializers for rate limiting API
"""

from django.utils import timezone

from rest_framework import serializers

from .models import IPBlacklist, IPWhitelist, RateLimitLog, RateLimitRule, RateLimitStats


class RateLimitRuleSerializer(serializers.ModelSerializer):
    """Serializer for rate limiting rules"""

    class Meta:
        model = RateLimitRule
        fields = [
            "id",
            "name",
            "user_type",
            "algorithm",
            "bucket_capacity",
            "refill_rate",
            "max_requests",
            "window_size",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class RateLimitLogSerializer(serializers.ModelSerializer):
    """Serializer for rate limiting logs"""

    user_username = serializers.CharField(source="user.username", read_only=True)
    action_display = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = RateLimitLog
        fields = [
            "id",
            "timestamp",
            "user",
            "user_username",
            "ip_address",
            "user_agent",
            "endpoint",
            "method",
            "user_type",
            "action",
            "action_display",
            "algorithm_used",
            "tokens_remaining",
            "requests_remaining",
            "retry_after",
            "metadata",
        ]
        read_only_fields = ["id", "timestamp"]


class RateLimitStatsSerializer(serializers.ModelSerializer):
    """Serializer for rate limiting statistics"""

    denial_rate = serializers.SerializerMethodField()
    total_user_requests = serializers.SerializerMethodField()

    class Meta:
        model = RateLimitStats
        fields = [
            "id",
            "date",
            "hour",
            "total_requests",
            "allowed_requests",
            "denied_requests",
            "burst_protections",
            "denial_rate",
            "anonymous_requests",
            "authenticated_requests",
            "premium_requests",
            "admin_requests",
            "total_user_requests",
            "average_tokens_remaining",
            "average_requests_remaining",
            "peak_requests_per_minute",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_denial_rate(self, obj):
        """Calculate denial rate percentage"""
        if obj.total_requests > 0:
            return round((obj.denied_requests / obj.total_requests) * 100, 2)
        return 0.0

    def get_total_user_requests(self, obj):
        """Get total requests by all user types"""
        return obj.anonymous_requests + obj.authenticated_requests + obj.premium_requests + obj.admin_requests


class IPWhitelistSerializer(serializers.ModelSerializer):
    """Serializer for IP whitelist"""

    created_by_username = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = IPWhitelist
        fields = ["id", "ip_address", "description", "is_active", "created_at", "created_by", "created_by_username"]
        read_only_fields = ["id", "created_at", "created_by"]

    def validate_ip_address(self, value):
        """Validate IP address format"""
        import ipaddress

        try:
            ipaddress.ip_address(value)
        except ValueError:
            raise serializers.ValidationError("Invalid IP address format")
        return value


class IPBlacklistSerializer(serializers.ModelSerializer):
    """Serializer for IP blacklist"""

    created_by_username = serializers.CharField(source="created_by.username", read_only=True)
    is_expired_display = serializers.CharField(source="is_expired", read_only=True)
    reason_display = serializers.CharField(source="get_reason_display", read_only=True)

    class Meta:
        model = IPBlacklist
        fields = [
            "id",
            "ip_address",
            "reason",
            "reason_display",
            "description",
            "is_active",
            "expires_at",
            "is_expired_display",
            "created_at",
            "created_by",
            "created_by_username",
        ]
        read_only_fields = ["id", "created_at", "created_by"]

    def validate_ip_address(self, value):
        """Validate IP address format"""
        import ipaddress

        try:
            ipaddress.ip_address(value)
        except ValueError:
            raise serializers.ValidationError("Invalid IP address format")
        return value

    def validate_expires_at(self, value):
        """Validate expiration date is in the future"""
        if value and value <= timezone.now():
            raise serializers.ValidationError("Expiration date must be in the future")
        return value


class RateLimitSummarySerializer(serializers.Serializer):
    """Serializer for rate limiting summary data"""

    current_hour = serializers.DictField()
    last_24_hours = serializers.DictField()
    last_7_days = serializers.DictField()
    top_blocked_ips = serializers.ListField()
    active_rules = serializers.DictField()
