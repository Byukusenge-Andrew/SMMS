"""
Billing app models - imports from core.models for payment-related models
"""

# Import models from core app to avoid duplication
from apps.core.models.payment_models import (
    SubscriptionTier,
    UserSubscription, 
    PaymentHistory
)

# Additional billing-specific models can be added here if needed

# Invoice model (not in core, so we define it here)
import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class PaymentMethod(models.Model):
    """User payment methods"""
    
    TYPE_CHOICES = [
        ('card', 'Credit/Debit Card'),
        ('bank_account', 'Bank Account'),
        ('paypal', 'PayPal'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payment_methods")
    stripe_payment_method_id = models.CharField(max_length=255)
    
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    is_default = models.BooleanField(default=False)
    
    # Card details (for display purposes only)
    last_four = models.CharField(max_length=4, blank=True)
    brand = models.CharField(max_length=20, blank=True)
    exp_month = models.IntegerField(null=True, blank=True)
    exp_year = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payment_methods"
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        if self.type == 'card':
            return f"{self.brand} ****{self.last_four}"
        return f"{self.type}"


class Invoice(models.Model):
    """Billing invoices"""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('paid', 'Paid'),
        ('uncollectible', 'Uncollectible'),
        ('void', 'Void'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="invoices")
    subscription = models.ForeignKey('core.UserSubscription', on_delete=models.CASCADE, related_name="invoices")
    
    stripe_invoice_id = models.CharField(max_length=255, unique=True)
    invoice_number = models.CharField(max_length=100)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    
    # Amounts
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    
    currency = models.CharField(max_length=3, default='USD')
    
    # Dates
    invoice_date = models.DateTimeField()
    due_date = models.DateTimeField()
    paid_at = models.DateTimeField(null=True, blank=True)
    
    # URLs
    hosted_invoice_url = models.URLField(blank=True)
    invoice_pdf_url = models.URLField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "invoices"
        ordering = ['-invoice_date']

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.user.username}"

    @property
    def is_paid(self):
        return self.status == 'paid'

    @property
    def is_overdue(self):
        return self.status == 'open' and timezone.now().date() > self.due_date.date()
        ordering = ['price_monthly']
    
    def __str__(self):
        return self.display_name


class UserSubscription(models.Model):
    """User subscription model"""
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
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    tier = models.ForeignKey(SubscriptionTier, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='inactive')
    billing_period = models.CharField(max_length=10, choices=BILLING_PERIOD_CHOICES, default='monthly')
    
    # Dates
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    trial_end_date = models.DateTimeField(null=True, blank=True)
    last_payment_date = models.DateTimeField(null=True, blank=True)
    next_payment_date = models.DateTimeField(null=True, blank=True)
    
    # Stripe data
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_subscriptions'
    
    def __str__(self):
        return f"{self.user.username} - {self.tier.display_name}"
    
    @property
    def is_active(self):
        return self.status in ['active', 'trialing']
    
    @property
    def current_price(self):
        if self.billing_period == 'yearly':
            return self.tier.price_yearly
        return self.tier.price_monthly


class PaymentHistory(models.Model):
    """Payment history model"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('canceled', 'Canceled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_history')
    subscription = models.ForeignKey(UserSubscription, on_delete=models.CASCADE, related_name='payments')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    
    # Stripe data
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    stripe_invoice_id = models.CharField(max_length=255, blank=True)
    
    # Description
    description = models.TextField(blank=True)
    
    # Dates
    payment_date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payment_history'
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"{self.user.username} - ${self.amount} - {self.status}"


class Invoice(models.Model):
    """Invoice model"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('paid', 'Paid'),
        ('void', 'Void'),
        ('uncollectible', 'Uncollectible'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invoices')
    subscription = models.ForeignKey(UserSubscription, on_delete=models.CASCADE, related_name='invoices')
    
    invoice_number = models.CharField(max_length=50, unique=True)
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Stripe data
    stripe_invoice_id = models.CharField(max_length=255, blank=True)
    
    # Dates
    issue_date = models.DateTimeField(default=timezone.now)
    due_date = models.DateTimeField()
    paid_date = models.DateTimeField(null=True, blank=True)
    
    # Invoice details
    description = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'invoices'
        ordering = ['-issue_date']
    
    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.user.username}"
    
    @property
    def amount_remaining(self):
        return self.amount_due - self.amount_paid


class UsageStats(models.Model):
    """Usage statistics model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='usage_stats')
    
    # Current month stats
    posts_this_month = models.IntegerField(default=0)
    connected_accounts = models.IntegerField(default=0)
    team_members = models.IntegerField(default=0)
    api_calls_this_month = models.IntegerField(default=0)
    
    # Dates
    month = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'usage_stats'
        unique_together = ['user', 'month']
        ordering = ['-month']
    
    def __str__(self):
        return f"{self.user.username} - {self.month}"


class PaymentMethod(models.Model):
    """Payment method model"""
    TYPE_CHOICES = [
        ('card', 'Credit/Debit Card'),
        ('bank_account', 'Bank Account'),
        ('paypal', 'PayPal'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_methods')
    
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Card details (masked)
    last_four = models.CharField(max_length=4, blank=True)
    brand = models.CharField(max_length=20, blank=True)  # visa, mastercard, etc.
    exp_month = models.IntegerField(null=True, blank=True)
    exp_year = models.IntegerField(null=True, blank=True)
    
    # Stripe data
    stripe_payment_method_id = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payment_methods'
        ordering = ['-is_default', '-created_at']
    
    def __str__(self):
        if self.type == 'card':
            return f"{self.brand.title() if self.brand else 'Card'} ending in {self.last_four}"
        return f"{self.get_type_display()}"
