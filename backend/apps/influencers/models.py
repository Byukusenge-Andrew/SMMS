from django.contrib.auth.models import User
from django.db import models

from apps.authentication.models import SocialMediaAccount


class Influencer(models.Model):
    NICHE_CHOICES = [
        ("fashion", "Fashion"),
        ("beauty", "Beauty"),
        ("fitness", "Fitness"),
        ("food", "Food"),
        ("travel", "Travel"),
        ("tech", "Technology"),
        ("lifestyle", "Lifestyle"),
        ("business", "Business"),
        ("education", "Education"),
        ("entertainment", "Entertainment"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="influencer_profile")
    bio = models.TextField(blank=True)
    niche = models.CharField(max_length=20, choices=NICHE_CHOICES, blank=True)
    website = models.URLField(blank=True)

    # Rates and pricing
    post_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    story_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    reel_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Verification and status
    is_verified = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)

    # Metrics
    total_followers = models.IntegerField(default=0)
    avg_engagement_rate = models.FloatField(default=0.0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "influencers"

    def __str__(self):
        return f"{self.user.username} - {self.niche}"


class Campaign(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("paused", "Paused"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_campaigns")
    title = models.CharField(max_length=255)
    description = models.TextField()
    budget = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    # Target criteria
    target_niches = models.JSONField(default=list)
    min_followers = models.IntegerField(default=0)
    max_followers = models.IntegerField(null=True, blank=True)
    target_platforms = models.JSONField(default=list)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "campaigns"

    def __str__(self):
        return f"{self.title} - {self.creator.username}"


class CampaignApplication(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("completed", "Completed"),
    ]

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="applications")
    influencer = models.ForeignKey(Influencer, on_delete=models.CASCADE, related_name="applications")
    proposed_rate = models.DecimalField(max_digits=10, decimal_places=2)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "campaign_applications"
        unique_together = ["campaign", "influencer"]

    def __str__(self):
        return f"{self.campaign.title} - {self.influencer.user.username}"
