"""
Enhanced social media models with account sets for organization
"""

import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError


class SocialMediaSet(models.Model):
    """Model for grouping social media accounts into sets (like Later.com)"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='social_media_sets')
    
    # Set information
    name = models.CharField(max_length=100, help_text="Name for this social media set")
    description = models.TextField(blank=True, help_text="Optional description for this set")
    color = models.CharField(
        max_length=7, 
        default='#3B82F6',
        help_text="Hex color code for UI representation"
    )
    icon = models.CharField(
        max_length=50,
        default='users',
        help_text="Icon name for UI representation"
    )
    
    # Set configuration
    is_global = models.BooleanField(
        default=False,
        help_text="Global set for all new accounts (only one per user)"
    )
    is_active = models.BooleanField(default=True)
    is_default_for_posting = models.BooleanField(
        default=False,
        help_text="Use this set as default when posting to multiple platforms"
    )
    
    # Auto-assignment rules
    auto_assign_new_accounts = models.BooleanField(
        default=False,
        help_text="Automatically assign new social accounts to this set"
    )
    auto_assign_platforms = models.JSONField(
        default=list,
        blank=True,
        help_text="List of platforms to auto-assign (empty means all platforms)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['is_global', '-is_default_for_posting', 'name']
        indexes = [
            models.Index(fields=['user', 'is_global']),
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['user', 'is_default_for_posting']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name'],
                name='unique_set_name_per_user'
            ),
        ]
    
    def __str__(self):
        global_indicator = " (Global)" if self.is_global else ""
        return f"{self.name}{global_indicator} - {self.user.username}"
    
    def clean(self):
        """Validate set data"""
        # Ensure only one global set per user
        if self.is_global:
            existing_global = SocialMediaSet.objects.filter(
                user=self.user,
                is_global=True
            ).exclude(id=self.id)
            
            if existing_global.exists():
                raise ValidationError("User can only have one global social media set")
        
        # Validate color format
        if self.color and not self.color.startswith('#'):
            self.color = f"#{self.color}"
        
        if self.color and len(self.color) != 7:
            raise ValidationError("Color must be a valid hex color code (#RRGGBB)")
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        
        # If this is set as default for posting, unset others
        if self.is_default_for_posting:
            SocialMediaSet.objects.filter(
                user=self.user,
                is_default_for_posting=True
            ).exclude(id=self.id).update(is_default_for_posting=False)
    
    @property
    def account_count(self):
        """Get number of accounts in this set"""
        return self.social_accounts.count()
    
    @property
    def platform_count(self):
        """Get number of unique platforms in this set"""
        return self.social_accounts.values('platform').distinct().count()
    
    @property
    def total_followers(self):
        """Get total followers across all accounts in set"""
        from django.db.models import Sum
        return self.social_accounts.aggregate(
            total=Sum('followers_count')
        )['total'] or 0
    
    def get_accounts_by_platform(self):
        """Get accounts grouped by platform"""
        accounts_by_platform = {}
        for account in self.social_accounts.filter(is_active=True):
            platform = account.platform
            if platform not in accounts_by_platform:
                accounts_by_platform[platform] = []
            accounts_by_platform[platform].append(account)
        return accounts_by_platform
    
    def can_post_to_platform(self, platform):
        """Check if this set has active accounts for a platform"""
        return self.social_accounts.filter(
            platform=platform,
            is_active=True
        ).exists()
    
    def get_active_accounts(self):
        """Get all active accounts in this set"""
        return self.social_accounts.filter(is_active=True)
    
    @classmethod
    def get_or_create_global_set(cls, user):
        """Get or create the global set for a user"""
        global_set, created = cls.objects.get_or_create(
            user=user,
            is_global=True,
            defaults={
                'name': 'All Social Accounts',
                'description': 'Global set containing all your social media accounts',
                'color': '#10B981',  # Green color for global set
                'icon': 'globe',
                'is_default_for_posting': True,
                'auto_assign_new_accounts': True,
            }
        )
        return global_set, created
    
    @classmethod
    def get_default_set_for_posting(cls, user):
        """Get the default set for posting for a user"""
        default_set = cls.objects.filter(
            user=user,
            is_active=True,
            is_default_for_posting=True
        ).first()
        
        if not default_set:
            # If no default set, return global set
            global_set, _ = cls.get_or_create_global_set(user)
            return global_set
        
        return default_set


class SocialMediaSetMembership(models.Model):
    """Many-to-many relationship between sets and accounts with metadata"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    social_set = models.ForeignKey(
        SocialMediaSet,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    social_account = models.ForeignKey(
        'integrations.SocialMediaAccount',
        on_delete=models.CASCADE,
        related_name='set_memberships'
    )
    
    # Membership metadata
    added_at = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who added this account to the set"
    )
    is_primary_set = models.BooleanField(
        default=False,
        help_text="Whether this is the primary set for this account"
    )
    
    # Account-specific settings within the set
    custom_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Custom name for this account within this set"
    )
    posting_enabled = models.BooleanField(
        default=True,
        help_text="Whether posting is enabled for this account in this set"
    )
    post_order = models.PositiveIntegerField(
        default=0,
        help_text="Order for posting when posting to multiple accounts"
    )
    
    class Meta:
        unique_together = ['social_set', 'social_account']
        ordering = ['post_order', 'added_at']
        indexes = [
            models.Index(fields=['social_set', 'posting_enabled']),
            models.Index(fields=['social_account', 'is_primary_set']),
        ]
    
    def __str__(self):
        return f"{self.social_account.username} in {self.social_set.name}"
    
    def clean(self):
        """Validate membership data"""
        # Ensure set and account belong to same user
        if self.social_set.user != self.social_account.user:
            raise ValidationError("Set and account must belong to the same user")
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


# Add this to the existing SocialMediaAccount model
def add_set_relationship_to_existing_model():
    """
    This function shows how to add the relationship to existing SocialMediaAccount model.
    The actual implementation should be done via a migration that adds the field.
    """
    # This is the field that should be added to SocialMediaAccount:
    # 
    # social_sets = models.ManyToManyField(
    #     SocialMediaSet,
    #     through='SocialMediaSetMembership',
    #     related_name='social_accounts',
    #     blank=True,
    #     help_text="Social media sets this account belongs to"
    # )
    pass