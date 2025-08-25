"""
Billing app models - imports from core.models for payment-related models
"""

# Import models from core app to avoid duplication
from apps.core.models.payment_models import (
    SubscriptionTier,
    UserSubscription, 
    PaymentHistory
)

# Additional billing-specific models

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
