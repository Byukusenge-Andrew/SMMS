"""
Django Admin interface for rate limiting management
"""

from django.contrib import admin
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.html import format_html

from .models import IPBlacklist, IPWhitelist, RateLimitLog, RateLimitRule, RateLimitStats


@admin.register(RateLimitRule)
class RateLimitRuleAdmin(admin.ModelAdmin):
    list_display = ["name", "user_type", "algorithm", "bucket_capacity", "max_requests", "is_active", "created_at"]
    list_filter = ["user_type", "algorithm", "is_active", "created_at"]
    search_fields = ["name", "user_type"]
    readonly_fields = ["id", "created_at", "updated_at"]

    fieldsets = (
        ("Basic Information", {"fields": ("name", "user_type", "algorithm", "is_active")}),
        ("Token Bucket Configuration", {"fields": ("bucket_capacity", "refill_rate"), "classes": ("collapse",)}),
        ("Sliding Window Configuration", {"fields": ("max_requests", "window_size"), "classes": ("collapse",)}),
        ("Metadata", {"fields": ("id", "created_by", "created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(RateLimitLog)
class RateLimitLogAdmin(admin.ModelAdmin):
    list_display = ["timestamp", "action_colored", "user_type", "endpoint", "ip_address", "user", "algorithm_used"]
    list_filter = ["action", "user_type", "algorithm_used", "timestamp"]
    search_fields = ["ip_address", "endpoint", "user__username"]
    readonly_fields = ["id", "timestamp"]
    date_hierarchy = "timestamp"

    def action_colored(self, obj):
        colors = {"allowed": "green", "denied": "red", "burst_protection": "orange"}
        color = colors.get(obj.action, "black")
        return format_html('<span style="color: {};">{}</span>', color, obj.get_action_display())

    action_colored.short_description = "Action"

    def has_add_permission(self, request):
        return False  # Logs are read-only

    def has_change_permission(self, request, obj=None):
        return False  # Logs are read-only


@admin.register(RateLimitStats)
class RateLimitStatsAdmin(admin.ModelAdmin):
    list_display = [
        "date",
        "hour",
        "total_requests",
        "allowed_requests",
        "denied_requests",
        "denial_rate",
        "peak_requests_per_minute",
    ]
    list_filter = ["date", "hour"]
    readonly_fields = ["id", "created_at", "updated_at"]
    date_hierarchy = "date"

    def denial_rate(self, obj):
        if obj.total_requests > 0:
            rate = (obj.denied_requests / obj.total_requests) * 100
            color = "red" if rate > 10 else "orange" if rate > 5 else "green"
            return format_html('<span style="color: {};">{:.1f}%</span>', color, rate)
        return "0.0%"

    denial_rate.short_description = "Denial Rate"

    def has_add_permission(self, request):
        return False  # Stats are auto-generated

    def has_change_permission(self, request, obj=None):
        return False  # Stats are read-only


@admin.register(IPWhitelist)
class IPWhitelistAdmin(admin.ModelAdmin):
    list_display = ["ip_address", "description", "is_active", "created_at", "created_by"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["ip_address", "description"]
    readonly_fields = ["id", "created_at"]

    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(IPBlacklist)
class IPBlacklistAdmin(admin.ModelAdmin):
    list_display = ["ip_address", "reason", "description", "is_active", "expires_at", "is_expired_display", "created_at"]
    list_filter = ["reason", "is_active", "created_at"]
    search_fields = ["ip_address", "description"]
    readonly_fields = ["id", "created_at"]

    def is_expired_display(self, obj):
        if obj.expires_at:
            expired = obj.is_expired
            color = "red" if expired else "green"
            status = "Expired" if expired else "Active"
            return format_html('<span style="color: {};">{}</span>', color, status)
        return "Permanent"

    is_expired_display.short_description = "Status"

    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# Custom admin views for monitoring
class RateLimitMonitoringAdmin(admin.ModelAdmin):
    """Base class for monitoring views"""

    def changelist_view(self, request, extra_context=None):
        # Add summary statistics to context
        extra_context = extra_context or {}

        # Recent activity summary
        recent_logs = RateLimitLog.objects.filter(timestamp__gte=timezone.now() - timezone.timedelta(hours=24))

        extra_context["summary"] = {
            "total_requests_24h": recent_logs.count(),
            "denied_requests_24h": recent_logs.filter(action="denied").count(),
            "burst_protections_24h": recent_logs.filter(action="burst_protection").count(),
            "unique_ips_24h": recent_logs.values("ip_address").distinct().count(),
        }

        return super().changelist_view(request, extra_context)


# Monkey patch the RateLimitLog admin to include monitoring
RateLimitLogAdmin.__bases__ = (RateLimitMonitoringAdmin,)
