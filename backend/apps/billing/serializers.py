"""
Billing app serializers
"""

from rest_framework import serializers
from .models import PaymentMethod, Invoice
from apps.core.models.payment_models import SubscriptionTier, UserSubscription, PaymentHistory


class SubscriptionTierSerializer(serializers.ModelSerializer):
    """Subscription tier serializer"""
    
    class Meta:
        model = SubscriptionTier
        fields = [
            'id', 'name', 'display_name', 'description',
            'price_monthly', 'price_yearly', 'price_discount_yearly',
            'max_connected_accounts', 'max_posts_per_month', 'max_team_members',
            'advanced_analytics', 'custom_branding', 'api_access',
            'priority_support', 'gohighlevel_integration', 'is_active'
        ]
        read_only_fields = ['id']


class UserSubscriptionSerializer(serializers.ModelSerializer):
    """User subscription serializer"""
    tier = SubscriptionTierSerializer(read_only=True)
    tier_id = serializers.UUIDField(write_only=True, required=False)
    
    class Meta:
        model = UserSubscription
        fields = [
            'id', 'user', 'tier', 'tier_id', 'status', 'billing_period',
            'start_date', 'end_date', 'next_payment_date', 'cancel_at_period_end',
            'stripe_subscription_id', 'stripe_customer_id', 'trial_end_date',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class PaymentHistorySerializer(serializers.ModelSerializer):
    """Payment history serializer"""
    
    class Meta:
        model = PaymentHistory
        fields = [
            'id', 'user', 'amount', 'currency', 'status', 'payment_date',
            'stripe_payment_intent_id', 'description', 'metadata',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Payment method serializer"""
    
    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'user', 'type', 'is_default', 'last_four', 'brand',
            'exp_month', 'exp_year', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'stripe_payment_method_id', 'last_four', 'brand',
            'exp_month', 'exp_year', 'created_at', 'updated_at'
        ]


class InvoiceSerializer(serializers.ModelSerializer):
    """Invoice serializer"""
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'user', 'subscription', 'invoice_number', 'status',
            'subtotal', 'tax', 'total', 'amount_paid', 'amount_due',
            'currency', 'invoice_date', 'due_date', 'paid_at',
            'hosted_invoice_url', 'invoice_pdf_url', 'is_paid', 'is_overdue',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'stripe_invoice_id', 'invoice_number',
            'hosted_invoice_url', 'invoice_pdf_url', 'is_paid', 'is_overdue',
            'created_at', 'updated_at'
        ]


class BillingDashboardSerializer(serializers.Serializer):
    """Billing dashboard data serializer"""
    current_subscription = UserSubscriptionSerializer()
    payment_methods = PaymentMethodSerializer(many=True)
    recent_payments = PaymentHistorySerializer(many=True)
    upcoming_invoices = InvoiceSerializer(many=True)
    available_tiers = SubscriptionTierSerializer(many=True)


class SubscriptionChangeSerializer(serializers.Serializer):
    """Subscription change request serializer"""
    tier_id = serializers.UUIDField()
    billing_period = serializers.ChoiceField(choices=['monthly', 'yearly'])
    prorate = serializers.BooleanField(default=True)


class PaymentMethodCreateSerializer(serializers.Serializer):
    """Payment method creation serializer"""
    stripe_payment_method_id = serializers.CharField(max_length=255)
    is_default = serializers.BooleanField(default=False)
