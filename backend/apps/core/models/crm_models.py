"""
CRM integration models
"""

import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class GoHighLevelIntegration(models.Model):
    """GoHighLevel CRM integration settings"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="ghl_integration")
    
    # API credentials
    api_key = models.CharField(max_length=255, blank=True)
    location_id = models.CharField(max_length=255, blank=True)
    
    # Integration settings
    sync_contacts = models.BooleanField(default=True)
    sync_opportunities = models.BooleanField(default=True)
    sync_campaigns = models.BooleanField(default=True)
    
    # Webhook settings
    webhook_url = models.URLField(blank=True)
    webhook_secret = models.CharField(max_length=255, blank=True)
    
    is_active = models.BooleanField(default=True)
    last_sync_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gohighlevel_integrations"

    def __str__(self):
        return f"{self.user.username} - GoHighLevel"


class CRMContact(models.Model):
    """CRM contacts synchronized from GoHighLevel"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('prospect', 'Prospect'),
        ('customer', 'Customer'),
        ('unsubscribed', 'Unsubscribed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="crm_contacts")
    ghl_contact_id = models.CharField(max_length=255, unique=True)
    
    # Contact information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    company = models.CharField(max_length=255, blank=True)
    
    # Status and tags
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    tags = models.JSONField(default=list, blank=True)
    custom_fields = models.JSONField(default=dict, blank=True)
    
    # Social media info
    social_media_profiles = models.JSONField(default=dict, blank=True)
    
    # Tracking
    last_contacted = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Sync metadata
    ghl_created_at = models.DateTimeField(null=True, blank=True)
    ghl_updated_at = models.DateTimeField(null=True, blank=True)
    last_synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "crm_contacts"
        unique_together = ['user', 'ghl_contact_id']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['email']),
            models.Index(fields=['ghl_contact_id']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
