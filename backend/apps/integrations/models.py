"""
Models for social media integrations
"""
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class SocialMediaPlatform(models.TextChoices):
    """Supported social media platforms"""
    TWITTER = 'twitter', 'Twitter/X'
    FACEBOOK = 'facebook', 'Facebook'
    INSTAGRAM = 'instagram', 'Instagram'
    LINKEDIN = 'linkedin', 'LinkedIn'
    TIKTOK = 'tiktok', 'TikTok'
    YOUTUBE = 'youtube', 'YouTube'


class PostStatus(models.TextChoices):
    """Status of social media posts"""
    DRAFT = 'draft', 'Draft'
    SCHEDULED = 'scheduled', 'Scheduled' 
    PUBLISHING = 'publishing', 'Publishing'
    PUBLISHED = 'published', 'Published'
    FAILED = 'failed', 'Failed'
    DELETED = 'deleted', 'Deleted'


class SocialMediaAccount(models.Model):
    """Model to store connected social media accounts"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='connected_social_accounts')
    platform = models.CharField(max_length=20, choices=SocialMediaPlatform.choices)
    
    # Platform-specific account info
    platform_user_id = models.CharField(max_length=100)  # Platform's user ID
    username = models.CharField(max_length=100)
    display_name = models.CharField(max_length=200, blank=True)
    profile_image_url = models.URLField(blank=True)
    # Optional per-account signature appended to messages/posts (user-configurable)
    signature = models.CharField(max_length=120, blank=True, help_text="Optional signature to append to outbound content for this account")
    
    # Connection status
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    
    # Metrics (will be updated periodically)
    followers_count = models.IntegerField(default=0)
    following_count = models.IntegerField(default=0)
    posts_count = models.IntegerField(default=0)
    
    # Authentication tokens (encrypted in production)
    # For Twitter OAuth 1.0a: access_token=token, refresh_token=token_secret
    # For OAuth 2.0: access_token=bearer token, refresh_token=refresh token
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(null=True, blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    connected_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    last_sync = models.DateTimeField(null=True, blank=True)
    
    # Social Media Sets relationship
    social_sets = models.ManyToManyField(
        'SocialMediaSet',
        through='SocialMediaSetMembership',
        related_name='social_accounts',
        blank=True,
        help_text="Social media sets this account belongs to"
    )
    
    class Meta:
        unique_together = ['user', 'platform', 'platform_user_id']
        ordering = ['-connected_at']
    
    def __str__(self):
        return f"{self.username} ({self.platform})"
    
    @property
    def is_token_expired(self):
        """Check if access token is expired"""
        if not self.token_expires_at:
            return False
        return timezone.now() > self.token_expires_at

    def set_token_expiry_from_expires_in(self, expires_in_seconds: int | None):
        """Helper to set token_expires_at from expires_in seconds."""
        if expires_in_seconds:
            self.token_expires_at = timezone.now() + timezone.timedelta(seconds=expires_in_seconds)
    
    def get_primary_set(self):
        """Get the primary set for this account"""
        primary_membership = self.set_memberships.filter(is_primary_set=True).first()
        return primary_membership.social_set if primary_membership else None
    
    def add_to_set(self, social_set, is_primary=False, added_by=None, **membership_kwargs):
        """Add this account to a social media set"""
        membership, created = SocialMediaSetMembership.objects.get_or_create(
            social_set=social_set,
            social_account=self,
            defaults={
                'is_primary_set': is_primary,
                'added_by': added_by or self.user,
                **membership_kwargs
            }
        )
        
        # If setting as primary, unset other primary memberships
        if is_primary and created:
            self.set_memberships.exclude(id=membership.id).update(is_primary_set=False)
        
        return membership, created
    
    def remove_from_set(self, social_set):
        """Remove this account from a social media set"""
        return self.set_memberships.filter(social_set=social_set).delete()
    
    def get_all_sets(self):
        """Get all sets this account belongs to"""
        return SocialMediaSet.objects.filter(social_accounts=self)
    
    def auto_assign_to_sets(self):
        """Automatically assign this account to sets based on auto-assignment rules"""
        auto_assign_sets = SocialMediaSet.objects.filter(
            user=self.user,
            is_active=True,
            auto_assign_new_accounts=True
        )
        
        assigned_count = 0
        for social_set in auto_assign_sets:
            # Check if platform matches auto-assign rules
            if (not social_set.auto_assign_platforms or 
                self.platform in social_set.auto_assign_platforms):
                
                membership, created = self.add_to_set(
                    social_set,
                    is_primary=social_set.is_global,
                    added_by=self.user
                )
                if created:
                    assigned_count += 1
        
        return assigned_count


class SocialMediaPost(models.Model):
    """Model to store social media posts (both published and scheduled)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='social_posts')
    
    # Post content
    content = models.TextField()
    media_urls = models.JSONField(default=list, blank=True)  # URLs to media files
    hashtags = models.JSONField(default=list, blank=True)  # List of hashtags
    mentions = models.JSONField(default=list, blank=True)  # List of mentions
    
    # Scheduling
    scheduled_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=PostStatus.choices, default=PostStatus.DRAFT)
    
    # Platform-specific data
    platforms = models.JSONField(default=list)  # List of platforms to post to
    platform_posts = models.JSONField(default=dict, blank=True)  # Platform-specific post IDs
    
    # Analytics data
    total_likes = models.IntegerField(default=0)
    total_shares = models.IntegerField(default=0)
    total_comments = models.IntegerField(default=0)
    total_views = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.content[:50]}... ({self.status})"
    
    @property
    def is_scheduled(self):
        """Check if post is scheduled for future"""
        return (
            self.status == PostStatus.SCHEDULED and 
            self.scheduled_at and 
            self.scheduled_at > timezone.now()
        )


class TwitterPost(models.Model):
    """Model specifically for Twitter/X posts with platform-specific fields"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='twitter_posts')
    social_media_account = models.ForeignKey(
        SocialMediaAccount, 
        on_delete=models.CASCADE, 
        related_name='twitter_posts'
    )
    
    # Post content
    tweet_text = models.TextField(max_length=280)  # Twitter character limit
    media_paths = models.JSONField(default=list, blank=True)  # Local media file paths
    
    # Twitter-specific fields
    tweet_id = models.CharField(max_length=100, blank=True)  # Twitter's tweet ID
    in_reply_to_tweet_id = models.CharField(max_length=100, blank=True)
    is_retweet = models.BooleanField(default=False)
    is_quote_tweet = models.BooleanField(default=False)
    
    # Scheduling
    scheduled_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=PostStatus.choices, default=PostStatus.DRAFT)
    
    # Analytics (updated from Twitter API)
    retweet_count = models.IntegerField(default=0)
    like_count = models.IntegerField(default=0)
    reply_count = models.IntegerField(default=0)
    quote_count = models.IntegerField(default=0)
    impression_count = models.IntegerField(default=0)
    
    # Error handling
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    last_analytics_update = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"@{self.social_media_account.username}: {self.tweet_text[:50]}..."
    
    @property
    def twitter_url(self):
        """Get Twitter URL for this tweet"""
        if self.tweet_id:
            return f"https://twitter.com/i/web/status/{self.tweet_id}"
        return None
    
    @property
    def total_engagement(self):
        """Calculate total engagement"""
        return self.retweet_count + self.like_count + self.reply_count + self.quote_count


class SocialMediaAnalytics(models.Model):
    """Model to store analytics data for social media accounts"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    social_media_account = models.ForeignKey(
        SocialMediaAccount, 
        on_delete=models.CASCADE, 
        related_name='analytics'
    )
    
    # Date range for analytics
    date = models.DateField()
    
    # Metrics
    followers_gained = models.IntegerField(default=0)
    followers_lost = models.IntegerField(default=0)
    posts_created = models.IntegerField(default=0)
    total_likes = models.IntegerField(default=0)
    total_shares = models.IntegerField(default=0)
    total_comments = models.IntegerField(default=0)
    total_views = models.IntegerField(default=0)
    total_impressions = models.IntegerField(default=0)
    
    # Engagement metrics
    engagement_rate = models.FloatField(default=0.0)  # As percentage
    reach = models.IntegerField(default=0)
    
    # Platform-specific metrics (JSON for flexibility)
    platform_specific_metrics = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['social_media_account', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.social_media_account} - {self.date}"


class TikTokPost(models.Model):
    """Model specifically for TikTok posts with platform-specific fields"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tiktok_posts')
    social_media_account = models.ForeignKey(
        SocialMediaAccount, 
        on_delete=models.CASCADE, 
        related_name='tiktok_posts'
    )
    
    # Post content
    title = models.CharField(max_length=150, blank=True)  # TikTok video title
    description = models.TextField(max_length=2200, blank=True)  # TikTok description limit
    video_path = models.CharField(max_length=500)  # Local video file path
    
    # TikTok-specific fields
    tiktok_video_id = models.CharField(max_length=100, blank=True)  # TikTok's video ID
    upload_id = models.CharField(max_length=100, blank=True)  # Upload session ID
    publish_id = models.CharField(max_length=100, blank=True)  # Publish ID
    
    # Video metadata
    duration_ms = models.IntegerField(null=True, blank=True)  # Video duration in milliseconds
    video_width = models.IntegerField(null=True, blank=True)
    video_height = models.IntegerField(null=True, blank=True)
    file_size_bytes = models.BigIntegerField(null=True, blank=True)
    
    # Privacy and interaction settings
    privacy_level = models.CharField(
        max_length=30, 
        choices=[
            ('PUBLIC_TO_EVERYONE', 'Public to Everyone'),
            ('MUTUAL_FOLLOW_FRIEND', 'Friends'),
            ('SELF_ONLY', 'Private'),
        ],
        default='PUBLIC_TO_EVERYONE'
    )
    disable_duet = models.BooleanField(default=False)
    disable_comment = models.BooleanField(default=False)
    disable_stitch = models.BooleanField(default=False)
    
    # Brand content settings
    brand_content_toggle = models.BooleanField(default=False)
    brand_organic_toggle = models.BooleanField(default=False)
    
    # Video cover settings
    video_cover_timestamp_ms = models.IntegerField(default=1000)  # Thumbnail timestamp
    
    # Hashtags and mentions
    hashtags = models.JSONField(default=list, blank=True)  # List of hashtags
    mentions = models.JSONField(default=list, blank=True)  # List of mentions
    
    # Scheduling
    scheduled_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=PostStatus.choices, default=PostStatus.DRAFT)
    
    # Analytics (updated periodically)
    view_count = models.IntegerField(default=0)
    like_count = models.IntegerField(default=0)
    comment_count = models.IntegerField(default=0)
    share_count = models.IntegerField(default=0)
    
    # Error tracking
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        title = self.title or "Untitled"
        return f"{title[:30]}... ({self.status})"
    
    @property
    def is_scheduled(self):
        """Check if post is scheduled for future"""
        return (
            self.status == PostStatus.SCHEDULED and 
            self.scheduled_at and 
            self.scheduled_at > timezone.now()
        )
    
    @property
    def can_retry(self):
        """Check if post can be retried after failure"""
        return self.status == PostStatus.FAILED and self.retry_count < self.max_retries
    
    @property
    def engagement_rate(self):
        """Calculate engagement rate as percentage"""
        if self.view_count > 0:
            total_engagement = self.like_count + self.comment_count + self.share_count
            return round((total_engagement / self.view_count) * 100, 2)
        return 0.0


class ScheduledPostQueue(models.Model):
    """Queue for scheduled social media posts"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Reference to the specific post model
    content_type = models.CharField(max_length=50)  # e.g., 'twitter_post'
    object_id = models.UUIDField()
    
    # Scheduling details
    scheduled_at = models.DateTimeField()
    platform = models.CharField(max_length=20, choices=SocialMediaPlatform.choices)
    
    # Processing status
    is_processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # Error handling
    attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=3)
    error_message = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['scheduled_at']
        indexes = [
            models.Index(fields=['scheduled_at', 'is_processed']),
            models.Index(fields=['platform', 'is_processed']),
        ]
    
    def __str__(self):
        return f"{self.platform} post scheduled for {self.scheduled_at}"


class IntegrationProvider(models.TextChoices):
    """3rd-party non-social integration providers (file storage, design, automation, chat)."""
    GOOGLE_DRIVE = 'google_drive', 'Google Drive'
    DROPBOX = 'dropbox', 'Dropbox'
    CANVA = 'canva', 'Canva'
    ZAPIER = 'zapier', 'Zapier'
    SLACK = 'slack', 'Slack'


class IntegrationConnection(models.Model):
    """Per-user connection for generic integrations (distinct from social media account OAuth).

    Stores access / refresh tokens or API keys plus minimal metadata. Slack kept here to allow
    future per-user bot/user tokens while still supporting current global token fallback.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='integration_connections')
    provider = models.CharField(max_length=40, choices=IntegrationProvider.choices)
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    scopes = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    active = models.BooleanField(default=True)
    connected_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'provider']
        ordering = ['provider']

    def __str__(self):
        return f"{self.user.username} -> {self.provider} ({'active' if self.active else 'inactive'})"

    @property
    def is_token_expired(self):
        if not self.token_expires_at:
            return False
        return timezone.now() > self.token_expires_at


# Social Media Sets for organizing accounts (like Later.com)

class SocialMediaSet(models.Model):
    """Model for grouping social media accounts into sets"""
    
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
        from django.core.exceptions import ValidationError
        
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
        SocialMediaAccount,
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
        from django.core.exceptions import ValidationError
        
        # Ensure set and account belong to same user
        if self.social_set.user != self.social_account.user:
            raise ValidationError("Set and account must belong to the same user")
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class AIAgent(models.Model):
    """Custom AI Agent configurations for content generation"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_agents')
    name = models.CharField(max_length=100)
    persona = models.TextField(help_text="System instructions or persona prompt for the agent")
    platform = models.CharField(
        max_length=20, 
        default='all', 
        help_text="Default platform for this agent (e.g., twitter, linkedin, instagram, tiktok, all)"
    )
    tone = models.CharField(
        max_length=50, 
        default='professional', 
        help_text="Agent's writing tone/style (e.g., professional, humorous, educational, persuasive, witty)"
    )
    temperature = models.FloatField(default=0.7, help_text="Creativity temperature (0.0 to 1.0)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_agents"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.user.username})"

