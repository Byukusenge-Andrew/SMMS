"""
Serializers for payment and subscription management
"""

from rest_framework import serializers
from ..models.payment_models import SubscriptionTier, UserSubscription, PaymentHistory


class SubscriptionTierSerializer(serializers.ModelSerializer):
    """Serializer for subscription tiers"""
    
    features = serializers.SerializerMethodField()
    
    class Meta:
        model = SubscriptionTier
        fields = [
            'id',
            'name',
            'display_name',
            'description',
            'price_monthly',
            'price_yearly',
            'features',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_features(self, obj):
        """Get features as a structured object"""
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


class SubscriptionTierCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating subscription tiers"""
    
    # Feature fields
    max_social_accounts = serializers.IntegerField(min_value=1, default=1)
    max_scheduled_posts = serializers.IntegerField(min_value=1, default=10)
    max_team_members = serializers.IntegerField(min_value=1, default=1)
    analytics_retention_days = serializers.IntegerField(min_value=1, default=30)
    api_rate_limit = serializers.IntegerField(min_value=100, default=1000)
    gohighlevel_integration = serializers.BooleanField(default=False)
    advanced_analytics = serializers.BooleanField(default=False)
    priority_support = serializers.BooleanField(default=False)
    white_label = serializers.BooleanField(default=False)
    
    class Meta:
        model = SubscriptionTier
        fields = [
            'name',
            'display_name',
            'description',
            'price_monthly',
            'price_yearly',
            'max_social_accounts',
            'max_scheduled_posts',
            'max_team_members',
            'analytics_retention_days',
            'api_rate_limit',
            'gohighlevel_integration',
            'advanced_analytics',
            'priority_support',
            'white_label',
            'is_active',
        ]
    
    def validate_price_monthly(self, value):
        """Validate monthly price"""
        if value < 0:
            raise serializers.ValidationError("Monthly price cannot be negative")
        return value
    
    def validate_price_yearly(self, value):
        """Validate yearly price"""
        if value < 0:
            raise serializers.ValidationError("Yearly price cannot be negative")
        return value
    
    def validate(self, data):
        """Validate tier data"""
        if data.get('price_yearly', 0) > 0 and data.get('price_monthly', 0) > 0:
            yearly_equivalent = data['price_monthly'] * 12
            if data['price_yearly'] >= yearly_equivalent:
                raise serializers.ValidationError(
                    "Yearly price should be less than 12 times the monthly price to provide value"
                )
        return data


class UserSubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for user subscriptions"""
    
    tier = SubscriptionTierSerializer(read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    is_trial = serializers.SerializerMethodField()
    days_until_renewal = serializers.SerializerMethodField()
    
    class Meta:
        model = UserSubscription
        fields = [
            'id',
            'user',
            'user_username',
            'tier',
            'status',
            'billing_period',
            'start_date',
            'end_date',
            'trial_end_date',
            'last_payment_date',
            'next_payment_date',
            'stripe_customer_id',
            'stripe_subscription_id',
            'is_trial',
            'days_until_renewal',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'user', 'created_at', 'updated_at',
            'stripe_customer_id', 'stripe_subscription_id'
        ]
    
    def get_is_trial(self, obj):
        """Check if subscription is in trial period"""
        if obj.trial_end_date:
            from django.utils import timezone
            return timezone.now() < obj.trial_end_date
        return False
    
    def get_days_until_renewal(self, obj):
        """Calculate days until next renewal"""
        if obj.next_payment_date:
            from django.utils import timezone
            delta = obj.next_payment_date - timezone.now()
            return max(0, delta.days)
        return None


class PaymentHistorySerializer(serializers.ModelSerializer):
    """Serializer for payment history"""
    
    user_username = serializers.CharField(source='user.username', read_only=True)
    tier_name = serializers.CharField(source='subscription.tier.display_name', read_only=True)
    
    class Meta:
        model = PaymentHistory
        fields = [
            'id',
            'user',
            'user_username',
            'subscription',
            'tier_name',
            'amount',
            'currency',
            'status',
            'payment_date',
            'stripe_payment_intent_id',
            'failure_reason',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
