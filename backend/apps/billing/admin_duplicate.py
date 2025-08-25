"""
Billing app admin configuration
Only register billing-specific models here.
Core payment models are registered in apps.core.admin
"""

from django.contrib import admin
from .models import PaymentMethod, Invoice


# Only register billing-specific models
# Core models (SubscriptionTier, UserSubscription, PaymentHistory) are registered in core.admin

@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
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
    list_display = ['invoice_number', 'user', 'total', 'status', 'invoice_date', 'due_date']
    list_filter = ['status', 'invoice_date']
    search_fields = ['invoice_number', 'user__username', 'user__email']
    readonly_fields = ['stripe_invoice_id', 'created_at', 'updated_at']
    date_hierarchy = 'invoice_date'


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['user', 'type', 'brand', 'last_four', 'is_default', 'created_at']
    list_filter = ['type', 'brand', 'is_default']
    search_fields = ['user__username', 'user__email', 'last_four']
    readonly_fields = ['stripe_payment_method_id', 'created_at', 'updated_at']
