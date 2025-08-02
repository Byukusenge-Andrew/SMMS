import uuid

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.core.storage import SupabaseStorage

# Initialize Supabase storage
supabase_storage = SupabaseStorage()


class UserProfile(models.Model):
    """Extended user profile model"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    company_name = models.CharField(max_length=255, blank=True, default="")
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True, storage=supabase_storage)
    subscription_type = models.CharField(max_length=20, default="free")
    time_format = models.CharField(
        max_length=3,
        choices=[("12h", "12 Hour"), ("24h", "24 Hour")],
        default="12h",
    )
    timezone = models.CharField(max_length=50, default="UTC")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    email_notifications = models.BooleanField(default=True)
    slack_notifications = models.BooleanField(default=False)

    class Meta:
        db_table = "user_profiles"

    def __str__(self):
        return f"{self.user.username} - {self.company_name or 'Personal'}"


# Signal to create user profile when a new user is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.profile.save()
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=instance)


class SocialMediaAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    PLATFORM_CHOICES = [
        ("instagram", "Instagram"),
        ("facebook", "Facebook"),
        ("twitter", "Twitter/X"),
        ("linkedin", "LinkedIn"),
        ("tiktok", "TikTok"),
        ("youtube", "YouTube"),
        ("pinterest", "Pinterest"),
        ("snapchat", "Snapchat"),
        ("reddit", "Reddit"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="social_accounts")
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    username = models.CharField(max_length=255)
    access_token = models.TextField()
    refresh_token = models.TextField(blank=True)
    token_expires_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Platform-specific data
    platform_user_id = models.CharField(max_length=255, blank=True)
    follower_count = models.IntegerField(default=0)
    following_count = models.IntegerField(default=0)

    class Meta:
        unique_together = ["user", "platform", "username"]
        db_table = "social_media_accounts"

    def __str__(self):
        return f"{self.user.username} - {self.platform} ({self.username})"

    def is_token_expired(self):
        if not self.token_expires_at:
            return False
        return timezone.now() > self.token_expires_at


class Team(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(User, related_name="owned_teams", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class TeamMember(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ROLE_CHOICES = [
        ("owner", "Owner"),
        ("admin", "Admin"),
        ("editor", "Editor"),
        ("viewer", "Viewer"),
    ]

    team = models.ForeignKey(
        Team, related_name="members", on_delete=models.CASCADE, null=True, blank=True  # Temporarily nullable for migration
    )
    user = models.ForeignKey(User, related_name="team_memberships", on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="viewer")
    invited_email = models.EmailField(blank=True, null=True)
    is_active = models.BooleanField(default=False)
    invited_at = models.DateTimeField(auto_now_add=True)
    joined_at = models.DateTimeField(null=True, blank=True)  # Renamed from accepted_at

    class Meta:
        unique_together = ["team", "user"]

    def __str__(self):
        return f"{self.user.username} - {self.team.name} ({self.role})"


class EmailVerificationToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(hours=24)
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Email verification for {self.user.username}"
