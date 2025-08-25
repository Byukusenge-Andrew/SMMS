"""
Billing app admin configuration
"""

from django.contrib import admin
from .models import PaymentMethod, Invoice
# Import models from core
from apps.core.models.payment_models import SubscriptionTier, UserSubscription, PaymentHistory


@admin.register(SubscriptionTier)
class SubscriptionTierAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'name', 'price_monthly', 'price_yearly', 'is_active']
    list_filter = ['is_active', 'gohighlevel_integration', 'advanced_analytics']
    search_fields = ['name', 'display_name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'tier', 'status', 'billing_period', 'start_date', 'next_payment_date']
    list_filter = ['status', 'billing_period', 'tier']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'currency', 'status', 'payment_date']
    list_filter = ['status', 'currency', 'payment_date']
    search_fields = ['user__username', 'user__email', 'stripe_payment_intent_id']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'user', 'amount_due', 'status', 'issue_date', 'due_date']
    list_filter = ['status', 'issue_date']
    search_fields = ['invoice_number', 'user__username', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(UsageStats)
class UsageStatsAdmin(admin.ModelAdmin):
    list_display = ['user', 'month', 'posts_this_month', 'connected_accounts', 'team_members']
    list_filter = ['month']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['user', 'type', 'brand', 'last_four', 'is_default', 'is_active']
    list_filter = ['type', 'brand', 'is_default', 'is_active']
    search_fields = ['user__username', 'user__email', 'last_four']
    readonly_fields = ['id', 'created_at', 'updated_at']
