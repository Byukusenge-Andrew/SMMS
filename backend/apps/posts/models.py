from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from apps.authentication.models import SocialMediaAccount


class SocialSet(models.Model):
    """Group of social media accounts for coordinated posting"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="social_sets")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    accounts = models.ManyToManyField(SocialMediaAccount, related_name="social_sets")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "social_sets"

    def __str__(self):
        return f"{self.user.username} - {self.name}"


class Post(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("scheduled", "Scheduled"),
        ("published", "Published"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    POST_TYPE_CHOICES = [
        ("post", "Post"),
        ("story", "Story"),
        ("reel", "Reel"),
        ("video", "Video"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    social_account = models.ForeignKey(
        SocialMediaAccount, on_delete=models.CASCADE, related_name="posts", null=True, blank=True
    )
    social_set = models.ForeignKey(SocialSet, on_delete=models.CASCADE, related_name="posts", null=True, blank=True)

    # Content
    content = models.TextField()
    caption = models.TextField(blank=True)
    hashtags = models.TextField(blank=True, help_text="Comma-separated hashtags")

    # Media
    image = models.ImageField(upload_to="posts/images/", blank=True, null=True)
    video = models.FileField(upload_to="posts/videos/", blank=True, null=True)
    media_url = models.URLField(blank=True, help_text="External media URL")

    # Scheduling
    scheduled_time = models.DateTimeField()
    timezone = models.CharField(max_length=50, default="UTC")

    # Post details
    post_type = models.CharField(max_length=20, choices=POST_TYPE_CHOICES, default="post")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    platform = models.CharField(max_length=20)

    # Location and tagging
    location = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    tagged_users = models.TextField(blank=True, help_text="Comma-separated usernames")

    # Settings
    is_locked = models.BooleanField(default=False, help_text="Prevent editing when locked")
    is_template = models.BooleanField(default=False, help_text="Save as reusable template")

    # Metadata
    external_post_id = models.CharField(max_length=255, blank=True, help_text="Platform-specific post ID")
    published_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "posts"
        ordering = ["-scheduled_time"]

    def __str__(self):
        return f"{self.user.username} - {self.platform} - {self.scheduled_time}"

    def get_hashtags_list(self):
        return [tag.strip() for tag in self.hashtags.split(",") if tag.strip()]

    def get_tagged_users_list(self):
        return [user.strip() for user in self.tagged_users.split(",") if user.strip()]

    def can_edit(self):
        return not self.is_locked and self.status in ["draft", "scheduled"]


class PostTemplate(models.Model):
    """Reusable post templates"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="post_templates")
    name = models.CharField(max_length=255)
    content = models.TextField()
    caption = models.TextField(blank=True)
    hashtags = models.TextField(blank=True)
    post_type = models.CharField(max_length=20, choices=Post.POST_TYPE_CHOICES, default="post")
    platforms = models.JSONField(default=list, help_text="List of platforms this template is for")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "post_templates"

    def __str__(self):
        return f"{self.user.username} - {self.name}"


class Holiday(models.Model):
    """Holiday calendar for post suggestions"""

    name = models.CharField(max_length=255)
    date = models.DateField()
    country = models.CharField(max_length=100, default="US")
    category = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "holidays"
        unique_together = ["name", "date", "country"]

    def __str__(self):
        return f"{self.name} - {self.date}"


class PostSuggestion(models.Model):
    """AI-generated post suggestions"""

    SUGGESTION_TYPE_CHOICES = [
        ("content", "Content Suggestion"),
        ("hashtag", "Hashtag Suggestion"),
        ("timing", "Timing Suggestion"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="post_suggestions")
    suggestion_type = models.CharField(max_length=20, choices=SUGGESTION_TYPE_CHOICES)
    platform = models.CharField(max_length=20)
    content = models.TextField()
    confidence_score = models.FloatField(default=0.0)
    is_used = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "post_suggestions"
        ordering = ["-confidence_score", "-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.suggestion_type} - {self.platform}"
