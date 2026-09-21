import uuid

from django.contrib.auth.models import User
from django.db import models
from django.conf import settings

from apps.authentication.models import SocialMediaAccount
from apps.core.storage import SupabaseStorage

# Initialize Supabase storage
supabase_storage = SupabaseStorage()


class SocialSet(models.Model):
    """Group of social media accounts for coordinated posting"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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


class PostingScheduleSlot(models.Model):
    """Predefined recurring posting time slots for automated queue scheduling"""

    DAY_OF_WEEK_CHOICES = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posting_schedule_slots")
    platform = models.CharField(max_length=50, blank=True, help_text="Specific platform or blank for all platforms")
    day_of_week = models.IntegerField(choices=DAY_OF_WEEK_CHOICES)
    time = models.TimeField(help_text="Time of day for this slot (e.g. 10:00:00)")
    timezone = models.CharField(max_length=50, default="UTC")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "posting_schedule_slots"
        ordering = ["day_of_week", "time"]
        unique_together = ["user", "platform", "day_of_week", "time"]

    def __str__(self):
        day_name = dict(self.DAY_OF_WEEK_CHOICES).get(self.day_of_week, str(self.day_of_week))
        plat = self.platform or "All"
        return f"{self.user.username} - {plat} - {day_name} {self.time}"

    @classmethod
    def get_next_available_slot(cls, user, platform=None, after_time=None):
        """
        Calculate the next available queue slot for a user/platform.
        Looks ahead up to 35 days. If no custom slots exist, uses default schedule
        (Daily at 10:00, 14:00, 18:00 UTC).
        Ensures slot is strictly in the future and doesn't conflict with existing scheduled posts.
        """
        from datetime import datetime, time, timedelta
        from django.utils import timezone
        import pytz

        now = timezone.now()
        start_time = max(after_time or now, now + timedelta(minutes=5))

        # Fetch active slots for user
        query = cls.objects.filter(user=user, is_active=True)
        if platform:
            query = query.filter(models.Q(platform__iexact=platform) | models.Q(platform=""))
        slots = list(query.order_by("day_of_week", "time"))

        # Default slots: Daily at 10:00, 14:00, 18:00
        default_times = [time(10, 0), time(14, 0), time(18, 0)]
        use_defaults = len(slots) == 0

        # Scan the next 35 days for the first vacant slot
        for day_offset in range(35):
            candidate_date = (start_time + timedelta(days=day_offset)).date()
            weekday = candidate_date.weekday()

            if use_defaults:
                day_slot_times = [(t, "UTC") for t in default_times]
            else:
                day_slot_times = [(s.time, s.timezone or "UTC") for s in slots if s.day_of_week == weekday]

            for slot_time, tz_name in day_slot_times:
                try:
                    slot_tz = pytz.timezone(tz_name)
                except Exception:
                    slot_tz = pytz.UTC

                naive_dt = datetime.combine(candidate_date, slot_time)
                try:
                    candidate_dt = slot_tz.localize(naive_dt)
                except Exception:
                    candidate_dt = naive_dt.replace(tzinfo=pytz.UTC)

                candidate_dt_utc = candidate_dt.astimezone(pytz.UTC)

                if candidate_dt_utc <= start_time:
                    continue

                # Check if a post is already scheduled in this slot (+/- 15 min window)
                window_start = candidate_dt_utc - timedelta(minutes=15)
                window_end = candidate_dt_utc + timedelta(minutes=15)

                post_exists = Post.objects.filter(
                    user=user,
                    status="scheduled",
                    scheduled_time__range=(window_start, window_end)
                ).exists()

                if not post_exists:
                    return candidate_dt_utc

        # Fallback if slots are congested: 2 hours after latest scheduled post or start_time
        latest_post = Post.objects.filter(user=user, status="scheduled").order_by("-scheduled_time").first()
        if latest_post and latest_post.scheduled_time > start_time:
            return latest_post.scheduled_time + timedelta(hours=2)

        return start_time + timedelta(hours=2)


class Post(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("pending_approval", "Pending Approval"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("scheduled", "Scheduled"),
        ("publishing", "Publishing"),
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
    image = models.ImageField(upload_to="posts/images/", blank=True, null=True, storage=supabase_storage)
    video = models.FileField(upload_to="posts/videos/", blank=True, null=True, storage=supabase_storage)
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

    # Evergreen content recycling
    is_evergreen = models.BooleanField(
        default=False, help_text="Automatically re-queue post after successful publication"
    )
    recycle_interval_days = models.IntegerField(
        default=30, null=True, blank=True, help_text="Days to wait before recycling this post"
    )
    recycle_count = models.IntegerField(
        default=0, help_text="Number of times this post has been recycled"
    )
    max_recycle_count = models.IntegerField(
        null=True, blank=True, help_text="Maximum recycles allowed (null for unlimited)"
    )
    last_recycled_at = models.DateTimeField(null=True, blank=True)
    original_post = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recycled_instances",
        help_text="Original post this instance was recycled from",
    )

    # Approval workflow
    approval_reviewer = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_posts"
    )
    approval_feedback = models.TextField(blank=True)
    submitted_for_approval_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

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
        return not self.is_locked and self.status in ["draft", "rejected", "scheduled"]

    def submit_for_approval(self):
        from django.utils import timezone
        self.status = "pending_approval"
        self.submitted_for_approval_at = timezone.now()
        self.save(update_fields=["status", "submitted_for_approval_at"])

    def approve(self, reviewer=None):
        from django.utils import timezone
        self.status = "approved"
        self.approval_reviewer = reviewer
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "approval_reviewer", "reviewed_at"])

    def reject(self, reviewer=None, feedback=""):
        from django.utils import timezone
        self.status = "rejected"
        self.approval_reviewer = reviewer
        self.approval_feedback = feedback
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "approval_reviewer", "approval_feedback", "reviewed_at"])

    def recycle(self):
        """
        Clones this evergreen post into a new scheduled post allocated
        at the next available queue slot after recycle_interval_days.
        """
        from datetime import timedelta
        from django.utils import timezone

        if not self.is_evergreen:
            return None

        if self.max_recycle_count is not None and self.recycle_count >= self.max_recycle_count:
            return None

        interval = self.recycle_interval_days or 30
        base_time = self.published_at or timezone.now()
        earliest_target = base_time + timedelta(days=interval)

        next_slot = PostingScheduleSlot.get_next_available_slot(
            user=self.user,
            platform=self.platform,
            after_time=earliest_target
        )

        cloned_post = Post.objects.create(
            user=self.user,
            social_account=self.social_account,
            social_set=self.social_set,
            content=self.content,
            caption=self.caption,
            hashtags=self.hashtags,
            image=self.image,
            video=self.video,
            media_url=self.media_url,
            scheduled_time=next_slot,
            timezone=self.timezone,
            post_type=self.post_type,
            status="scheduled",
            platform=self.platform,
            location=self.location,
            latitude=self.latitude,
            longitude=self.longitude,
            tagged_users=self.tagged_users,
            is_evergreen=True,
            recycle_interval_days=self.recycle_interval_days,
            recycle_count=self.recycle_count + 1,
            max_recycle_count=self.max_recycle_count,
            last_recycled_at=timezone.now(),
            original_post=self.original_post or self,
        )

        self.last_recycled_at = timezone.now()
        self.save(update_fields=["last_recycled_at"])

        return cloned_post


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


class AIGenerationLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_generations")
    prompt = models.TextField()
    platform = models.CharField(max_length=50, choices=[('twitter', 'Twitter/X'), ('facebook', 'Facebook'), ('linkedin', 'LinkedIn'), ('instagram', 'Instagram')])
    tone = models.CharField(max_length=50, default='professional')
    generated_text = models.TextField()
    tokens_used = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']