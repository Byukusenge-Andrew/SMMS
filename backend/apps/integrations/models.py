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
    refresh_token = models.TextField(blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    connected_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    last_sync = models.DateTimeField(null=True, blank=True)
    
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
