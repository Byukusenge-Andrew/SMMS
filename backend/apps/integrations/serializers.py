"""
Serializers for social media API integrations
"""
from rest_framework import serializers
from django.utils import timezone
from .models import TwitterPost, TikTokPost, SocialMediaAccount, SocialMediaAnalytics


class TwitterPostCreateSerializer(serializers.Serializer):
    """Serializer for creating a new tweet"""
    
    tweet_text = serializers.CharField(
        max_length=280,
        help_text="The text content of the tweet (max 280 characters)"
    )
    
    media_paths = serializers.ListField(
        child=serializers.CharField(max_length=500),
        required=False,
        allow_empty=True,
        max_length=4,  # Twitter allows up to 4 media attachments
        help_text="List of media file paths to attach to the tweet (max 4 files)"
    )
    
    scheduled_at = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="Schedule the tweet to be posted at a specific time (ISO 8601 format)"
    )
    
    def validate_tweet_text(self, value):
        """Validate tweet text length and content"""
        if not value.strip():
            raise serializers.ValidationError("Tweet text cannot be empty")
        
        if len(value) > 280:
            raise serializers.ValidationError("Tweet text cannot exceed 280 characters")
        
        return value.strip()
    
    def validate_scheduled_at(self, value):
        """Validate scheduled time is in the future"""
        if value and value <= timezone.now():
            raise serializers.ValidationError("Scheduled time must be in the future")
        
        return value
    
    def validate_media_paths(self, value):
        """Validate media paths"""
        if value and len(value) > 4:
            raise serializers.ValidationError("Maximum 4 media files are allowed per tweet")
        
        # Additional validation for file types could be added here
        return value


class TwitterPostSerializer(serializers.ModelSerializer):
    """Serializer for TwitterPost model"""
    
    social_media_account = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = TwitterPost
        fields = [
            'id',
            'user',
            'social_media_account',
            'tweet_text',
            'tweet_id',
            'media_paths',
            'retweet_count',
            'like_count',
            'reply_count',
            'quote_count',
            'impression_count',
            'status',
            'scheduled_at',
            'published_at',
            'created_at',
            'updated_at',
            'error_message',
            'last_analytics_update'
        ]
        read_only_fields = [
            'id',
            'user',
            'tweet_id',
            'retweet_count',
            'like_count',
            'reply_count',
            'quote_count',
            'impression_count',
            'published_at',
            'created_at',
            'updated_at',
            'last_analytics_update'
        ]
    
    def to_representation(self, instance):
        """Custom representation with formatted data"""
        data = super().to_representation(instance)
        
        # Format timestamps
        for field in ['scheduled_at', 'published_at', 'created_at', 'updated_at', 'last_analytics_update']:
            if data.get(field):
                data[field] = instance.__dict__[field].isoformat() if instance.__dict__.get(field) else None
        
        # Add Twitter URL if tweet_id exists
        if data.get('tweet_id'):
            account_username = instance.social_media_account.username if instance.social_media_account else 'unknown'
            data['twitter_url'] = f"https://twitter.com/{account_username}/status/{data['tweet_id']}"
        
        # Add engagement rate calculation
        total_engagements = (
            (data.get('retweet_count') or 0) +
            (data.get('like_count') or 0) +
            (data.get('reply_count') or 0) +
            (data.get('quote_count') or 0)
        )
        impression_count = data.get('impression_count') or 0
        
        if impression_count > 0:
            data['engagement_rate'] = round((total_engagements / impression_count) * 100, 2)
        else:
            data['engagement_rate'] = 0.0
        
        data['total_engagements'] = total_engagements
        
        return data


class SocialMediaAccountSerializer(serializers.ModelSerializer):
    """Serializer for SocialMediaAccount model"""
    
    class Meta:
        model = SocialMediaAccount
        fields = [
            'id',
            'user',
            'platform',
            'platform_user_id',
            'username',
            'display_name',
            'profile_image_url',
            'followers_count',
            'following_count',
            'posts_count',
            'is_verified',
            'is_active',
            'created_at',
            'updated_at',
            'last_sync'
        ]
        read_only_fields = [
            'id',
            'user',
            'created_at',
            'updated_at'
        ]
    
    def to_representation(self, instance):
        """Custom representation with formatted data"""
        data = super().to_representation(instance)
        
        # Format timestamps
        for field in ['created_at', 'updated_at', 'last_sync']:
            if data.get(field):
                data[field] = instance.__dict__[field].isoformat() if instance.__dict__.get(field) else None
        
        # Add platform display name
        platform_display_names = {
            'twitter': 'Twitter/X',
            'facebook': 'Facebook',
            'instagram': 'Instagram',
            'linkedin': 'LinkedIn',
            'tiktok': 'TikTok'
        }
        
        data['platform_display_name'] = platform_display_names.get(data['platform'], data['platform'].title())
        
        return data


class SocialMediaAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for SocialMediaAnalytics model"""
    
    social_media_account = SocialMediaAccountSerializer(read_only=True)
    
    class Meta:
        model = SocialMediaAnalytics
        fields = [
            'id',
            'social_media_account',
            'date',
            'followers_gained',
            'followers_lost',
            'posts_published',
            'total_impressions',
            'total_engagements',
            'total_clicks',
            'engagement_rate',
            'custom_metrics',
            'created_at'
        ]
        read_only_fields = [
            'id',
            'created_at'
        ]
    
    def to_representation(self, instance):
        """Custom representation with calculated metrics"""
        data = super().to_representation(instance)
        
        # Format date
        if data.get('date'):
            data['date'] = instance.date.isoformat() if instance.date else None
        
        if data.get('created_at'):
            data['created_at'] = instance.created_at.isoformat()
        
        # Add calculated metrics
        if data.get('total_impressions') and data['total_impressions'] > 0:
            if not data.get('engagement_rate'):
                engagements = data.get('total_engagements', 0)
                data['engagement_rate'] = round((engagements / data['total_impressions']) * 100, 2)
        
        # Add growth metrics
        net_followers = (data.get('followers_gained', 0) - data.get('followers_lost', 0))
        data['net_followers_change'] = net_followers
        
        return data


class TwitterAnalyticsSerializer(serializers.Serializer):
    """Serializer for Twitter analytics response"""
    
    tweet_id = serializers.CharField()
    metrics = serializers.DictField()
    created_at = serializers.DateTimeField()
    
    class Meta:
        fields = ['tweet_id', 'metrics', 'created_at']


class TwitterRateLimitSerializer(serializers.Serializer):
    """Serializer for Twitter rate limit response"""
    
    endpoint = serializers.CharField()
    limit = serializers.IntegerField()
    remaining = serializers.IntegerField()
    reset_time = serializers.DateTimeField()
    
    class Meta:
        fields = ['endpoint', 'limit', 'remaining', 'reset_time']


class TwitterSearchSerializer(serializers.Serializer):
    """Serializer for Twitter search parameters"""
    
    query = serializers.CharField(
        max_length=500,
        help_text="Search query (keywords, hashtags, mentions, etc.)"
    )
    
    count = serializers.IntegerField(
        default=10,
        min_value=1,
        max_value=100,
        help_text="Number of tweets to retrieve (1-100)"
    )
    
    def validate_query(self, value):
        """Validate search query"""
        if not value.strip():
            raise serializers.ValidationError("Search query cannot be empty")
        
        return value.strip()


class TweetResponseSerializer(serializers.Serializer):
    """Serializer for individual tweet response"""
    
    id = serializers.CharField()
    text = serializers.CharField()
    author = serializers.DictField()
    created_at = serializers.DateTimeField()
    public_metrics = serializers.DictField()
    entities = serializers.DictField(required=False)
    
    class Meta:
        fields = ['id', 'text', 'author', 'created_at', 'public_metrics', 'entities']


# TikTok Serializers

class TikTokPostCreateSerializer(serializers.Serializer):
    """Serializer for creating a new TikTok post"""
    
    title = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
        help_text="Title of the TikTok video (max 150 characters)"
    )
    
    description = serializers.CharField(
        max_length=2200,
        required=False,
        allow_blank=True,
        help_text="Description/caption for the TikTok video (max 2200 characters)"
    )
    
    video_file = serializers.FileField(
        help_text="Video file to upload to TikTok (MP4, MOV, or WEBM format)"
    )
    
    privacy_level = serializers.ChoiceField(
        choices=[
            ('PUBLIC_TO_EVERYONE', 'Public to Everyone'),
            ('MUTUAL_FOLLOW_FRIEND', 'Friends'),
            ('SELF_ONLY', 'Private'),
        ],
        default='PUBLIC_TO_EVERYONE',
        help_text="Privacy level for the TikTok video"
    )
    
    disable_duet = serializers.BooleanField(
        default=False,
        help_text="Disable duet functionality for this video"
    )
    
    disable_comment = serializers.BooleanField(
        default=False,
        help_text="Disable comments for this video"
    )
    
    disable_stitch = serializers.BooleanField(
        default=False,
        help_text="Disable stitch functionality for this video"
    )
    
    brand_content_toggle = serializers.BooleanField(
        default=False,
        help_text="Mark as brand content"
    )
    
    brand_organic_toggle = serializers.BooleanField(
        default=False,
        help_text="Mark as organic brand content"
    )
    
    video_cover_timestamp_ms = serializers.IntegerField(
        default=1000,
        min_value=0,
        help_text="Timestamp in milliseconds for video thumbnail (default: 1000ms)"
    )
    
    hashtags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        allow_empty=True,
        help_text="List of hashtags for the video (without # symbol)"
    )
    
    mentions = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        allow_empty=True,
        help_text="List of user mentions for the video (without @ symbol)"
    )
    
    scheduled_at = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="Schedule the video to be posted at a specific time (ISO 8601 format)"
    )
    
    def validate_video_file(self, value):
        """Validate video file format and size"""
        # Check file extension
        valid_extensions = ['.mp4', '.mov', '.webm']
        if not any(value.name.lower().endswith(ext) for ext in valid_extensions):
            raise serializers.ValidationError(
                "Invalid file format. Supported formats: MP4, MOV, WEBM"
            )
        
        # Check file size (TikTok limit is typically 500MB)
        max_size = 500 * 1024 * 1024  # 500MB in bytes
        if value.size > max_size:
            raise serializers.ValidationError(
                "File size exceeds 500MB limit"
            )
        
        return value
    
    def validate_scheduled_at(self, value):
        """Validate scheduled time is in the future"""
        if value and value <= timezone.now():
            raise serializers.ValidationError("Scheduled time must be in the future")
        
        return value
    
    def validate_hashtags(self, value):
        """Validate hashtags format"""
        if value:
            for hashtag in value:
                if hashtag.startswith('#'):
                    raise serializers.ValidationError(
                        "Hashtags should not include the # symbol"
                    )
                if len(hashtag) > 50:
                    raise serializers.ValidationError(
                        f"Hashtag '{hashtag}' exceeds 50 character limit"
                    )
        return value
    
    def validate_mentions(self, value):
        """Validate mentions format"""
        if value:
            for mention in value:
                if mention.startswith('@'):
                    raise serializers.ValidationError(
                        "Mentions should not include the @ symbol"
                    )
                if len(mention) > 50:
                    raise serializers.ValidationError(
                        f"Mention '{mention}' exceeds 50 character limit"
                    )
        return value


class TikTokPostSerializer(serializers.ModelSerializer):
    """Serializer for TikTok post model"""
    
    engagement_rate = serializers.SerializerMethodField()
    is_scheduled = serializers.SerializerMethodField()
    can_retry = serializers.SerializerMethodField()
    
    class Meta:
        model = TikTokPost
        fields = [
            'id', 'title', 'description', 'video_path', 'tiktok_video_id',
            'privacy_level', 'disable_duet', 'disable_comment', 'disable_stitch',
            'brand_content_toggle', 'brand_organic_toggle', 'hashtags', 'mentions',
            'scheduled_at', 'status', 'view_count', 'like_count', 'comment_count', 
            'share_count', 'engagement_rate', 'is_scheduled', 'can_retry',
            'error_message', 'retry_count', 'created_at', 'updated_at', 'published_at'
        ]
        read_only_fields = [
            'id', 'tiktok_video_id', 'view_count', 'like_count', 'comment_count',
            'share_count', 'engagement_rate', 'is_scheduled', 'can_retry', 
            'error_message', 'retry_count', 'created_at', 'updated_at', 'published_at'
        ]
    
    def get_engagement_rate(self, obj):
        """Get engagement rate for the post"""
        return obj.engagement_rate
    
    def get_is_scheduled(self, obj):
        """Check if post is scheduled"""
        return obj.is_scheduled
    
    def get_can_retry(self, obj):
        """Check if post can be retried"""
        return obj.can_retry


class TikTokPostListSerializer(serializers.ModelSerializer):
    """Simplified serializer for TikTok post lists"""
    
    engagement_rate = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    
    class Meta:
        model = TikTokPost
        fields = [
            'id', 'title', 'description', 'status', 'status_display', 
            'view_count', 'like_count', 'engagement_rate', 'scheduled_at',
            'created_at', 'published_at'
        ]
    
    def get_engagement_rate(self, obj):
        """Get engagement rate for the post"""
        return obj.engagement_rate
    
    def get_status_display(self, obj):
        """Get human-readable status"""
        return obj.get_status_display()


class TikTokAnalyticsSerializer(serializers.Serializer):
    """Serializer for TikTok video analytics"""
    
    video_id = serializers.CharField()
    views = serializers.IntegerField()
    likes = serializers.IntegerField()
    comments = serializers.IntegerField()
    shares = serializers.IntegerField()
    engagement_rate = serializers.FloatField()
    
    class Meta:
        fields = ['video_id', 'views', 'likes', 'comments', 'shares', 'engagement_rate']


class TikTokVideoListSerializer(serializers.Serializer):
    """Serializer for TikTok video list response"""
    
    id = serializers.CharField()
    create_time = serializers.IntegerField()
    cover_image_url = serializers.URLField()
    share_url = serializers.URLField()
    video_description = serializers.CharField()
    duration = serializers.IntegerField()
    height = serializers.IntegerField()
    width = serializers.IntegerField()
    
    class Meta:
        fields = [
            'id', 'create_time', 'cover_image_url', 'share_url', 
            'video_description', 'duration', 'height', 'width'
        ]


class TikTokAuthSerializer(serializers.Serializer):
    """Serializer for TikTok authentication responses"""
    
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    expires_in = serializers.IntegerField()
    scope = serializers.CharField()
    
    class Meta:
        fields = ['access_token', 'refresh_token', 'expires_in', 'scope']
