"""
Django Admin interface for core functionality including rate limiting and payments
"""

from django.contrib import admin
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.html import format_html

# Explicit model imports
from .models.rate_limit_models import IPBlacklist, IPWhitelist, RateLimitLog, RateLimitRule, RateLimitStats
from .models.payment_models import SubscriptionTier, UserSubscription, PaymentHistory
from .models.crm_models import GoHighLevelIntegration, CRMContact


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
    list_display = ["timestamp", "block_type_colored", "endpoint", "ip_address", "user", "tokens_remaining"]
    list_filter = ["block_type", "timestamp"]
    search_fields = ["ip_address", "endpoint", "user__username"]
    readonly_fields = ["id", "timestamp"]
    date_hierarchy = "timestamp"

    def block_type_colored(self, obj):
        colors = {"token_bucket": "orange", "sliding_window": "blue", "both": "red"}
        color = colors.get(obj.block_type, "black")
        return format_html('<span style="color: {};">{}</span>', color, obj.get_block_type_display())

    block_type_colored.short_description = "Block Type"

    def has_add_permission(self, request):
        return False  # Logs are read-only

    def has_change_permission(self, request, obj=None):
        return False  # Logs are read-only


@admin.register(RateLimitStats)
class RateLimitStatsAdmin(admin.ModelAdmin):
    list_display = [
        "date",
        "hour",
        "period_type",
        "total_requests",
        "blocked_requests",
        "block_percentage",
        "unique_ips",
    ]
    list_filter = ["period_type", "date", "hour"]
    readonly_fields = ["id", "created_at", "updated_at"]
    date_hierarchy = "date"

    def block_percentage(self, obj):
        percentage = obj.block_percentage
        color = "red" if percentage > 10 else "orange" if percentage > 5 else "green"
        return format_html('<span style="color: {};">{:.1f}%</span>', color, percentage)

    block_percentage.short_description = "Block Rate"

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
    list_display = ["ip_address", "reason", "is_active", "blocked_until", "is_expired_display", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["ip_address", "reason"]
    readonly_fields = ["id", "created_at"]

    def is_expired_display(self, obj):
        if obj.blocked_until:
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
            "blocked_requests_24h": recent_logs.count(),
            "unique_ips_24h": recent_logs.values("ip_address").distinct().count(),
        }

        return super().changelist_view(request, extra_context)


# Payment and Subscription Admin Models

@admin.register(SubscriptionTier)
class SubscriptionTierAdmin(admin.ModelAdmin):
    list_display = ["name", "display_name", "price_monthly", "price_yearly", "max_social_accounts", "gohighlevel_integration", "is_active"]
    list_filter = ["is_active", "gohighlevel_integration", "advanced_analytics", "priority_support"]
    search_fields = ["name", "display_name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    
    fieldsets = (
        ("Basic Information", {
            "fields": ("name", "display_name", "description", "is_active")
        }),
        ("Pricing", {
            "fields": ("price_monthly", "price_yearly", "stripe_price_id_monthly", "stripe_price_id_yearly")
        }),
        ("Limits and Features", {
            "fields": (
                "max_social_accounts", "max_scheduled_posts", "max_team_members", 
                "analytics_retention_days", "api_rate_limit"
            )
        }),
        ("Feature Flags", {
            "fields": ("gohighlevel_integration", "advanced_analytics", "priority_support", "white_label")
        }),
        ("Metadata", {
            "fields": ("id", "created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ["user", "tier", "status", "billing_period", "start_date", "next_payment_date", "is_active"]
    list_filter = ["status", "billing_period", "tier__name", "start_date"]
    search_fields = ["user__username", "user__email", "stripe_customer_id", "stripe_subscription_id"]
    readonly_fields = ["id", "created_at", "updated_at", "is_active", "is_trial", "days_until_renewal"]
    raw_id_fields = ["user", "tier"]
    
    fieldsets = (
        ("User Information", {
            "fields": ("user", "tier")
        }),
        ("Subscription Details", {
            "fields": ("status", "billing_period", "start_date", "end_date", "trial_end_date")
        }),
        ("Stripe Integration", {
            "fields": ("stripe_customer_id", "stripe_subscription_id"),
            "classes": ("collapse",)
        }),
        ("Payment Tracking", {
            "fields": ("last_payment_date", "next_payment_date")
        }),
        ("Computed Fields", {
            "fields": ("is_active", "is_trial", "days_until_renewal"),
            "classes": ("collapse",)
        }),
        ("Metadata", {
            "fields": ("id", "created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'tier')


@admin.register(PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = ["user", "amount", "currency", "status_colored", "payment_date", "subscription_tier"]
    list_filter = ["status", "currency", "payment_date"]
    search_fields = ["user__username", "user__email", "stripe_payment_intent_id", "stripe_invoice_id"]
    readonly_fields = ["id", "created_at"]
    raw_id_fields = ["user", "subscription"]
    date_hierarchy = "payment_date"
    
    def status_colored(self, obj):
        colors = {"succeeded": "green", "failed": "red", "pending": "orange", "refunded": "blue"}
        color = colors.get(obj.status, "black")
        return format_html('<span style="color: {};">{}</span>', color, obj.get_status_display())
    
    status_colored.short_description = "Status"
    
    def subscription_tier(self, obj):
        return obj.subscription.tier.display_name if obj.subscription else "N/A"
    
    subscription_tier.short_description = "Tier"
    
    def has_add_permission(self, request):
        return False  # Payment history is managed by Stripe webhooks


# GoHighLevel CRM Admin Models

@admin.register(GoHighLevelIntegration)
class GoHighLevelIntegrationAdmin(admin.ModelAdmin):
    list_display = ["user", "location_id", "is_active", "sync_contacts", "last_sync_date"]
    list_filter = ["is_active", "sync_contacts", "sync_opportunities", "sync_campaigns"]
    search_fields = ["user__username", "user__email", "location_id"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["user"]
    
    fieldsets = (
        ("User Information", {
            "fields": ("user", "is_active")
        }),
        ("API Configuration", {
            "fields": ("api_key", "location_id"),
            "description": "Sensitive API credentials - handle with care"
        }),
        ("Sync Settings", {
            "fields": ("sync_contacts", "sync_opportunities", "sync_campaigns")
        }),
        ("Webhook Configuration", {
            "fields": ("webhook_url", "webhook_secret"),
            "classes": ("collapse",)
        }),
        ("Activity", {
            "fields": ("last_sync_date",)
        }),
        ("Metadata", {
            "fields": ("id", "created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )


@admin.register(CRMContact)
class CRMContactAdmin(admin.ModelAdmin):
    list_display = ["full_name", "email", "user", "status", "company", "last_synced_at"]
    list_filter = ["status", "user", "last_synced_at"]
    search_fields = ["first_name", "last_name", "email", "company", "ghl_contact_id"]
    readonly_fields = ["id", "ghl_contact_id", "created_at", "updated_at", "last_synced_at", "full_name"]
    raw_id_fields = ["user"]
    
    fieldsets = (
        ("Basic Information", {
            "fields": ("user", "ghl_contact_id", "status")
        }),
        ("Contact Details", {
            "fields": ("first_name", "last_name", "full_name", "email", "phone", "company")
        }),
        ("Tags and Custom Fields", {
            "fields": ("tags", "custom_fields"),
            "classes": ("collapse",)
        }),
        ("Social Media Profiles", {
            "fields": ("social_media_profiles",),
            "classes": ("collapse",)
        }),
        ("Activity Tracking", {
            "fields": ("last_contacted", "ghl_created_at", "ghl_updated_at")
        }),
        ("Sync Metadata", {
            "fields": ("last_synced_at", "created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


# Note: The admin classes for payment models are already registered above.
# This section was a duplicate and has been removed to prevent AlreadyRegistered errors.


# Monkey patch the RateLimitLog admin to include monitoring
RateLimitLogAdmin.__bases__ = (RateLimitMonitoringAdmin,)
