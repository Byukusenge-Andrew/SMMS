import uuid

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.core.storage import SupabaseStorage
from apps.core.models.payment_models import SubscriptionTier

# Initialize Supabase storage
supabase_storage = SupabaseStorage()


class UserProfile(models.Model):
    """Extended user profile model"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    company_name = models.CharField(max_length=255, blank=True, null=True)
    role = models.CharField(max_length=100, blank=True, null=True)  # User's role in the company
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True, storage=supabase_storage)
    # Link to subscription tier instead of simple string
    subscription_tier = models.ForeignKey(
        SubscriptionTier, 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True,
        related_name="user_profiles"
    )
    # Trial period management
    trial_start_date = models.DateTimeField(null=True, blank=True)
    trial_end_date = models.DateTimeField(null=True, blank=True)
    is_trial_active = models.BooleanField(default=False)
    trial_expired_notified = models.BooleanField(default=False)
    
    # Match 0002 migration width
    timezone = models.CharField(max_length=50, default="UTC")
    # Added to match migrations and serializer
    time_format = models.CharField(
        max_length=3,
        choices=(("12h", "12 Hour"), ("24h", "24 Hour")),
        default="12h",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    email_notifications = models.BooleanField(default=True)
    slack_notifications = models.BooleanField(default=False)

    class Meta:
        db_table = "user_profiles"

    def __str__(self):
        return f"{self.user.username} - {self.company_name or 'Personal'}"
    
    def is_trial_expired(self):
        """Check if trial period has expired"""
        if not self.is_trial_active or not self.trial_end_date:
            return False
        return timezone.now() > self.trial_end_date
    
    def days_left_in_trial(self):
        """Get number of days left in trial period"""
        if not self.is_trial_active or not self.trial_end_date:
            return 0
        delta = self.trial_end_date - timezone.now()
        return max(0, delta.days)
    
    def start_trial(self, trial_days=14):
        """Start trial period for paid tier"""
        if self.subscription_tier and self.subscription_tier.price_monthly > 0:
            self.trial_start_date = timezone.now()
            self.trial_end_date = timezone.now() + timezone.timedelta(days=trial_days)
            self.is_trial_active = True
            self.trial_expired_notified = False
            self.save()
    
    def end_trial_and_downgrade(self):
        """End trial and downgrade to free tier"""
        free_tier = SubscriptionTier.objects.filter(name="free", is_active=True).first()
        if free_tier:
            self.subscription_tier = free_tier
            self.is_trial_active = False
            self.trial_expired_notified = True
            self.save()
    
    def get_effective_subscription_tier(self):
        """Get the effective subscription tier considering trial status"""
        if self.is_trial_expired() and not self.has_paid_subscription():
            # If trial expired and no payment, return free tier
            return SubscriptionTier.objects.filter(name="free", is_active=True).first()
        return self.subscription_tier
    
    def has_paid_subscription(self):
        """Check if user has an active paid subscription"""
        try:
            from apps.core.models.payment_models import UserSubscription
            subscription = UserSubscription.objects.filter(
                user=self.user, 
                status__in=['active', 'trialing']
            ).first()
            
            if subscription and subscription.stripe_subscription_id:
                # Verify with Stripe that subscription is actually active
                try:
                    import stripe
                    from django.conf import settings
                    stripe.api_key = settings.STRIPE_SECRET_KEY
                    
                    stripe_subscription = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
                    return stripe_subscription.status in ['active', 'trialing']
                except:
                    # If Stripe call fails, fall back to local status
                    return subscription.status == 'active'
            
            return False
        except:
            return False


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



# Scheduled post model for calendar and post scheduling
class ScheduledPost(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("scheduled", "Scheduled"),
        ("published", "Published"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="scheduled_posts")
    social_account = models.ForeignKey('SocialMediaAccount', on_delete=models.CASCADE, related_name="scheduled_posts")
    content = models.TextField()
    media_url = models.URLField(blank=True, null=True)
    scheduled_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    platform_post_id = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ["-scheduled_time"]
        db_table = "scheduled_posts"

    def __str__(self):
        return f"{self.user.username} - {self.social_account.platform} - {self.status} @ {self.scheduled_time}"

class Team(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(User, related_name="owned_teams", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class TeamMember(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ROLE_CHOICES = (
        ("owner", "Owner"),
        ("admin", "Admin"),
        ("editor", "Editor"),
        ("viewer", "Viewer"),
    )
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="team_memberships", null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="viewer")
    invited_email = models.EmailField(null=True, blank=True)
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
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Email verification for {self.user.username}"
