from django.contrib.auth.models import User
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from apps.integrations.models import SocialMediaAccount


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
        ("gaming", "Gaming"),
        ("music", "Music"),
        ("sports", "Sports"),
        ("parenting", "Parenting"),
        ("health", "Health"),
    ]

    TIER_CHOICES = [
        ("nano", "Nano (1K-10K followers)"),
        ("micro", "Micro (10K-100K followers)"),
        ("macro", "Macro (100K-1M followers)"),
        ("mega", "Mega (1M+ followers)"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="influencer_profile")
    bio = models.TextField(blank=True, max_length=500)
    niche = models.CharField(max_length=20, choices=NICHE_CHOICES, blank=True)
    secondary_niches = models.JSONField(default=list, blank=True)
    website = models.URLField(blank=True)
    location = models.CharField(max_length=100, blank=True)
    languages = models.JSONField(default=list, blank=True)

    # Rates and pricing
    post_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    story_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    reel_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    video_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Verification and status
    is_verified = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    # Metrics
    total_followers = models.IntegerField(default=0)
    avg_engagement_rate = models.FloatField(default=0.0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    tier = models.CharField(max_length=10, choices=TIER_CHOICES, blank=True)

    # Contact preferences
    email_notifications = models.BooleanField(default=True)
    collaboration_types = models.JSONField(default=list, blank=True)  # ["sponsored", "gifted", "affiliate"]

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "influencers"
        indexes = [
            models.Index(fields=['niche', 'is_available']),
            models.Index(fields=['total_followers']),
            models.Index(fields=['tier']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.niche}"

    def calculate_tier(self):
        """Calculate influencer tier based on followers"""
        if self.total_followers >= 1000000:
            return "mega"
        elif self.total_followers >= 100000:
            return "macro"
        elif self.total_followers >= 10000:
            return "micro"
        else:
            return "nano"

    def save(self, *args, **kwargs):
        # Auto-calculate tier
        if self.total_followers:
            self.tier = self.calculate_tier()
        super().save(*args, **kwargs)


class Campaign(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("paused", "Paused"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    CAMPAIGN_TYPE_CHOICES = [
        ("sponsored_post", "Sponsored Post"),
        ("product_review", "Product Review"),
        ("brand_partnership", "Brand Partnership"),
        ("event_promotion", "Event Promotion"),
        ("giveaway", "Giveaway/Contest"),
        ("user_generated_content", "UGC Campaign"),
    ]

    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_campaigns")
    title = models.CharField(max_length=255)
    description = models.TextField()
    campaign_type = models.CharField(max_length=30, choices=CAMPAIGN_TYPE_CHOICES, default="sponsored_post")
    budget = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    # Requirements
    deliverables = models.JSONField(default=list, blank=True)  # ["1 Instagram post", "3 stories"]
    content_guidelines = models.TextField(blank=True)
    hashtags_required = models.JSONField(default=list, blank=True)

    # Target criteria
    target_niches = models.JSONField(default=list)
    min_followers = models.IntegerField(default=0)
    max_followers = models.IntegerField(null=True, blank=True)
    target_platforms = models.JSONField(default=list)
    target_locations = models.JSONField(default=list, blank=True)
    min_engagement_rate = models.FloatField(default=0.0)

    # Collaboration details
    application_deadline = models.DateTimeField(null=True, blank=True)
    max_participants = models.IntegerField(null=True, blank=True)
    is_paid = models.BooleanField(default=True)
    products_included = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "campaigns"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.creator.username}"

    @property
    def applications_count(self):
        return self.applications.count()

    @property
    def approved_applications_count(self):
        return self.applications.filter(status='approved').count()


class CampaignApplication(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("completed", "Completed"),
        ("withdrawn", "Withdrawn"),
    ]

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="applications")
    influencer = models.ForeignKey(Influencer, on_delete=models.CASCADE, related_name="applications")
    proposed_rate = models.DecimalField(max_digits=10, decimal_places=2)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    
    # Proposal details
    content_proposal = models.TextField(blank=True)
    timeline_proposal = models.TextField(blank=True)
    portfolio_links = models.JSONField(default=list, blank=True)

    # Campaign creator feedback
    feedback = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)

    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "campaign_applications"
        unique_together = ('campaign', 'influencer')
        ordering = ['-applied_at']

    def __str__(self):
        return f"{self.influencer.user.username} -> {self.campaign.title}"


class InfluencerCollaboration(models.Model):
    """Track ongoing collaborations between influencers and brands"""
    STATUS_CHOICES = [
        ("active", "Active"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("on_hold", "On Hold"),
    ]

    campaign_application = models.OneToOneField(
        CampaignApplication, 
        on_delete=models.CASCADE, 
        related_name="collaboration"
    )
    agreed_rate = models.DecimalField(max_digits=10, decimal_places=2)
    contract_signed = models.BooleanField(default=False)
    content_submitted = models.BooleanField(default=False)
    content_approved = models.BooleanField(default=False)
    payment_completed = models.BooleanField(default=False)
    
    # Deliverables tracking
    deliverables_completed = models.JSONField(default=list, blank=True)
    submission_date = models.DateTimeField(null=True, blank=True)
    approval_date = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "influencer_collaborations"

    def __str__(self):
        return f"Collaboration: {self.campaign_application}"


class InfluencerPortfolio(models.Model):
    """Portfolio items for influencers"""
    CONTENT_TYPE_CHOICES = [
        ("image", "Image"),
        ("video", "Video"),
        ("article", "Article"),
        ("campaign", "Campaign Results"),
    ]

    influencer = models.ForeignKey(Influencer, on_delete=models.CASCADE, related_name="portfolio")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES)
    media_url = models.URLField(blank=True)
    external_link = models.URLField(blank=True)
    
    # Metrics
    views = models.IntegerField(default=0)
    likes = models.IntegerField(default=0)
    comments = models.IntegerField(default=0)
    shares = models.IntegerField(default=0)
    
    # Collaboration info
    brand_name = models.CharField(max_length=255, blank=True)
    campaign_type = models.CharField(max_length=100, blank=True)
    
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "influencer_portfolio"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.influencer.user.username} - {self.title}"
        unique_together = ["campaign", "influencer"]

    def __str__(self):
        return f"{self.campaign.title} - {self.influencer.user.username}"
