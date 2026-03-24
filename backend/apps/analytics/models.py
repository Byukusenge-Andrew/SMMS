import uuid

from django.contrib.auth.models import User
from django.db import models

from apps.authentication.models import SocialMediaAccount
from apps.core.storage import SupabaseStorage
from apps.posts.models import Post

# Initialize Supabase storage
supabase_storage = SupabaseStorage()


class AnalyticsData(models.Model):
    """Store analytics data for posts and accounts"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    METRIC_TYPES = [
        ("impressions", "Impressions"),
        ("reach", "Reach"),
        ("engagement", "Engagement"),
        ("likes", "Likes"),
        ("shares", "Shares"),
        ("comments", "Comments"),
        ("saves", "Saves"),
        ("clicks", "Clicks"),
        ("followers", "Followers"),
        ("video_views", "Video Views"),
        ("profile_views", "Profile Views"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="analytics")
    social_account = models.ForeignKey(
        SocialMediaAccount, on_delete=models.CASCADE, related_name="analytics", null=True, blank=True
    )
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="analytics", null=True, blank=True)

    metric_type = models.CharField(max_length=20, choices=METRIC_TYPES)
    value = models.IntegerField(default=0)
    date = models.DateField()
    platform = models.CharField(max_length=20)

    # Location data for heat maps
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Demographic data
    age_group = models.CharField(max_length=20, blank=True)
    gender = models.CharField(max_length=20, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "analytics_data"
        unique_together = ["social_account", "post", "metric_type", "date", "country", "city"]
        indexes = [
            models.Index(fields=["user", "date"], name="analytics_user_date_idx"),
            models.Index(fields=["platform", "metric_type"], name="analytics_platform_metric_idx"),
            models.Index(fields=["post", "metric_type"], name="analytics_post_metric_idx"),
        ]

    def __str__(self):
        return f"{self.platform} - {self.metric_type}: {self.value}"


class CommentAnalytics(models.Model):
    """Store comment analytics and sentiment analysis"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    SENTIMENT_CHOICES = [
        ("positive", "Positive"),
        ("negative", "Negative"),
        ("neutral", "Neutral"),
    ]

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comment_analytics")
    comment_id = models.CharField(max_length=255)  # Platform-specific comment ID
    comment_text = models.TextField()
    author_username = models.CharField(max_length=255)

    # Sentiment analysis
    sentiment = models.CharField(max_length=20, choices=SENTIMENT_CHOICES)
    sentiment_score = models.FloatField(default=0.0)  # -1 to 1 scale
    confidence_score = models.FloatField(default=0.0)

    # Comment metadata
    likes_count = models.IntegerField(default=0)
    replies_count = models.IntegerField(default=0)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "comment_analytics"
        unique_together = ["post", "comment_id"]

    def __str__(self):
        return f"{self.post.platform} - {self.sentiment} ({self.sentiment_score})"


class PerformanceReport(models.Model):
    """Generated performance reports"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    REPORT_TYPES = [
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
        ("yearly", "Yearly"),
        ("custom", "Custom"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reports")
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    title = models.CharField(max_length=255)

    # Date range
    start_date = models.DateField()
    end_date = models.DateField()

    # Report data (JSON)
    data = models.JSONField(default=dict)

    # File attachments
    pdf_file = models.FileField(upload_to="reports/pdf/", blank=True, null=True, storage=supabase_storage)
    csv_file = models.FileField(upload_to="reports/csv/", blank=True, null=True, storage=supabase_storage)

    # Status
    is_generated = models.BooleanField(default=False)
    generated_at = models.DateTimeField(null=True, blank=True)

    # Email/Slack settings
    sent_via_email = models.BooleanField(default=False)
    sent_via_slack = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    slack_sent_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "performance_reports"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.title}"


class BestPerformingPost(models.Model):
    """Track best performing posts"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    PERFORMANCE_METRICS = [
        ("engagement_rate", "Engagement Rate"),
        ("reach", "Reach"),
        ("impressions", "Impressions"),
        ("likes", "Likes"),
        ("shares", "Shares"),
        ("comments", "Comments"),
        ("saves", "Saves"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="best_posts")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="performance_records")
    platform = models.CharField(max_length=20)

    metric_type = models.CharField(max_length=20, choices=PERFORMANCE_METRICS)
    metric_value = models.FloatField()

    # Time period for this record
    period_start = models.DateField()
    period_end = models.DateField()
    period_type = models.CharField(max_length=20)  # weekly, monthly, yearly

    rank = models.IntegerField(default=1)  # 1 = best performing

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "best_performing_posts"
        unique_together = ["user", "platform", "metric_type", "period_start", "period_end", "rank"]
        ordering = ["rank"]

    def __str__(self):
        return f"{self.platform} - {self.metric_type} - Rank {self.rank}"


class PlatformAverage(models.Model):
    """Store platform and overall averages"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="platform_averages")
    platform = models.CharField(max_length=20, blank=True)  # Empty for overall averages

    # Average metrics
    avg_impressions = models.FloatField(default=0.0)
    avg_reach = models.FloatField(default=0.0)
    avg_engagement_rate = models.FloatField(default=0.0)
    avg_likes = models.FloatField(default=0.0)
    avg_shares = models.FloatField(default=0.0)
    avg_comments = models.FloatField(default=0.0)
    avg_saves = models.FloatField(default=0.0)

    # Follower metrics
    avg_follower_growth = models.FloatField(default=0.0)
    total_followers = models.IntegerField(default=0)

    # Time period
    period_start = models.DateField()
    period_end = models.DateField()
    period_type = models.CharField(max_length=20, default="monthly")  # weekly, monthly, yearly

    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "platform_averages"
        unique_together = ["user", "platform", "period_start", "period_end"]

    def __str__(self):
        platform_name = self.platform or "Overall"
        return f"{self.user.username} - {platform_name} - {self.period_type}"


class AnalyticsInsight(models.Model):
    """AI-generated insights from analytics data"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    INSIGHT_TYPES = [
        ("trend", "Trend Analysis"),
        ("anomaly", "Anomaly Detection"),
        ("recommendation", "Recommendation"),
        ("prediction", "Prediction"),
        ("comparison", "Comparison"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="insights")
    insight_type = models.CharField(max_length=20, choices=INSIGHT_TYPES)
    title = models.CharField(max_length=255)
    description = models.TextField()

    # Associated data
    platform = models.CharField(max_length=20, blank=True)
    metric_type = models.CharField(max_length=20, blank=True)
    confidence_score = models.FloatField(default=0.0)

    # Actionable recommendations
    action_items = models.JSONField(default=list)

    # Associated data stored as JSON
    data = models.JSONField(default=dict)

    # Metadata
    is_read = models.BooleanField(default=False)
    priority = models.CharField(
        max_length=20,
        choices=[
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("critical", "Critical"),
        ],
        default="medium",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "analytics_insights"
        ordering = ["-priority", "-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.title}"
