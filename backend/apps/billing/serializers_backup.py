"""
Billing app serializers
"""

from rest_framework import serializers
from .models import PaymentMethod, Invoice
from apps.core.models.payment_models import SubscriptionTier, UserSubscription, PaymentHistory


class SubscriptionTierSerializer(serializers.ModelSerializer):
    """Subscription tier serializer"""
    features = serializers.SerializerMethodField()
    
    class Meta:
        model = SubscriptionTier
        fields = [
            'id', 'name', 'display_name', 'description',
            'price_monthly', 'price_yearly', 'features'
        ]
    
    def get_features(self, obj):
        return {
            'max_social_accounts': obj.max_social_accounts,
            'max_scheduled_posts': obj.max_scheduled_posts,
            'max_team_members': obj.max_team_members,
            'analytics_retention_days': obj.analytics_retention_days,
            'api_rate_limit': obj.api_rate_limit,
            'gohighlevel_integration': obj.gohighlevel_integration,
            'advanced_analytics': obj.advanced_analytics,
            'priority_support': obj.priority_support,
            'white_label': obj.white_label,
        }


class UserSubscriptionSerializer(serializers.ModelSerializer):
    """User subscription serializer"""
    tier = SubscriptionTierSerializer(read_only=True)
    current_price = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    
    class Meta:
        model = UserSubscription
        fields = [
            'id', 'tier', 'status', 'billing_period', 'start_date',
            'end_date', 'trial_end_date', 'last_payment_date',
            'next_payment_date', 'current_price', 'is_active'
        ]


class PaymentHistorySerializer(serializers.ModelSerializer):
    """Payment history serializer"""
    
    class Meta:
        model = PaymentHistory
        fields = [
            'id', 'amount', 'currency', 'status', 'description',
            'payment_date', 'created_at'
        ]


class InvoiceSerializer(serializers.ModelSerializer):
    """Invoice serializer"""
    amount_remaining = serializers.ReadOnlyField()
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'amount_due', 'amount_paid',
            'amount_remaining', 'currency', 'status', 'issue_date',
            'due_date', 'paid_date', 'description'
        ]


class UsageStatsSerializer(serializers.ModelSerializer):
    """Usage statistics serializer"""
    
    class Meta:
        model = UsageStats
        fields = [
            'posts_this_month', 'connected_accounts', 'team_members',
            'api_calls_this_month', 'month'
        ]


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Payment method serializer"""
    
    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'type', 'is_default', 'is_active', 'last_four',
            'brand', 'exp_month', 'exp_year', 'created_at'
        ]
