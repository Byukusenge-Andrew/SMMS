"""
Payment and subscription models
"""

import uuid
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class SubscriptionTier(models.Model):
    """Subscription tier definitions"""
    
    TIER_CHOICES = [
        ('free', 'Free'),
        ('professional', 'Professional'),
        ('enterprise', 'Enterprise'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, choices=TIER_CHOICES, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField()
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    stripe_price_id_monthly = models.CharField(max_length=255, blank=True)
    stripe_price_id_yearly = models.CharField(max_length=255, blank=True)
    
    # Features and limits
    max_social_accounts = models.IntegerField(default=1)
    max_scheduled_posts = models.IntegerField(default=10)
    max_team_members = models.IntegerField(default=1)
    analytics_retention_days = models.IntegerField(default=30)
    api_rate_limit = models.IntegerField(default=1000)  # requests per hour
    
    # Feature flags
    gohighlevel_integration = models.BooleanField(default=False)
    advanced_analytics = models.BooleanField(default=False)
    priority_support = models.BooleanField(default=False)
    white_label = models.BooleanField(default=False)
    custom_branding = models.BooleanField(default=False)
    bulk_upload_scheduling = models.BooleanField(default=False)
    hashtag_suggestions = models.BooleanField(default=False)
    best_time_insights = models.BooleanField(default=False)
    approval_workflows = models.BooleanField(default=False)
    sso_support = models.BooleanField(default=False)
    two_factor_auth = models.BooleanField(default=False)
    custom_integrations = models.BooleanField(default=False)
    phone_support = models.BooleanField(default=False)
    dedicated_account_manager = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "subscription_tiers"
        ordering = ['price_monthly']

    def __str__(self):
        return f"{self.display_name} - ${self.price_monthly}/month"


class UserSubscription(models.Model):
    """User subscription details"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('past_due', 'Past Due'),
        ('canceled', 'Canceled'),
        ('unpaid', 'Unpaid'),
        ('trialing', 'Trialing'),
    ]
    
    BILLING_PERIOD_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="subscription")
    tier = models.ForeignKey(SubscriptionTier, on_delete=models.PROTECT, related_name="subscriptions")
    
    # Stripe integration fields
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='inactive')
    billing_period = models.CharField(max_length=10, choices=BILLING_PERIOD_CHOICES, default='monthly')
    
    # Subscription dates
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    trial_end_date = models.DateTimeField(null=True, blank=True)
    
    # Payment tracking
    last_payment_date = models.DateTimeField(null=True, blank=True)
    next_payment_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_subscriptions"

    def __str__(self):
        return f"{self.user.username} - {self.tier.display_name} ({self.status})"

    @property
    def is_active(self):
        """Check if subscription is active"""
        return self.status == 'active'

    @property
    def is_trial(self):
        """Check if subscription is in trial period"""
        return (self.status == 'trialing' and 
                self.trial_end_date and 
                timezone.now() < self.trial_end_date)

    @property
    def days_until_renewal(self):
        """Get days until next payment"""
        if self.next_payment_date:
            delta = self.next_payment_date - timezone.now()
            return max(0, delta.days)
        return None


class PaymentHistory(models.Model):
    """Payment transaction history"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payments")
    subscription = models.ForeignKey(UserSubscription, on_delete=models.CASCADE, related_name="payments")
    
    stripe_payment_intent_id = models.CharField(max_length=255)
    stripe_invoice_id = models.CharField(max_length=255, blank=True)
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    
    payment_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "payment_history"
        ordering = ['-payment_date']

    def __str__(self):
        return f"{self.user.username} - ${self.amount} ({self.status})"