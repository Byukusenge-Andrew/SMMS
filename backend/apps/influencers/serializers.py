from django.contrib.auth.models import User
from rest_framework import serializers

from apps.authentication.models import SocialMediaAccount

from .models import Campaign, CampaignApplication, Influencer


class InfluencerSerializer(serializers.ModelSerializer):
    """Serializer for Influencer model"""

    user_info = serializers.SerializerMethodField()
    social_accounts_count = serializers.SerializerMethodField()

    class Meta:
        model = Influencer
        fields = [
            "id",
            "user",
            "user_info",
            "bio",
            "niche",
            "website",
            "post_rate",
            "story_rate",
            "reel_rate",
            "is_verified",
            "is_available",
            "total_followers",
            "avg_engagement_rate",
            "social_accounts_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "user_info", "social_accounts_count", "created_at", "updated_at"]

    def get_user_info(self, obj):
        """Get basic user information"""
        return {
            "username": obj.user.username,
            "email": obj.user.email,
            "first_name": obj.user.first_name,
            "last_name": obj.user.last_name,
            "full_name": f"{obj.user.first_name} {obj.user.last_name}".strip(),
        }

    def get_social_accounts_count(self, obj):
        """Get count of connected social media accounts"""
        return obj.social_accounts.filter(is_active=True).count()


class CampaignSerializer(serializers.ModelSerializer):
    """Serializer for Campaign model"""

    creator_info = serializers.SerializerMethodField()
    applications_count = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = [
            "id",
            "creator",
            "creator_info",
            "title",
            "description",
            "budget",
            "start_date",
            "end_date",
            "status",
            "target_niches",
            "min_followers",
            "max_followers",
            "target_platforms",
            "applications_count",
            "days_remaining",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "creator",
            "creator_info",
            "applications_count",
            "days_remaining",
            "created_at",
            "updated_at",
        ]

    def get_creator_info(self, obj):
        """Get campaign creator information"""
        return {"username": obj.creator.username, "first_name": obj.creator.first_name, "last_name": obj.creator.last_name}

    def get_applications_count(self, obj):
        """Get number of applications for this campaign"""
        return obj.applications.count()

    def get_days_remaining(self, obj):
        """Calculate days remaining until campaign end"""
        from django.utils import timezone

        if obj.end_date:
            remaining = (obj.end_date - timezone.now().date()).days
            return max(0, remaining)
        return None

    def validate(self, attrs):
        """Validate campaign data"""
        if attrs.get("start_date") and attrs.get("end_date"):
            if attrs["start_date"] >= attrs["end_date"]:
                raise serializers.ValidationError("End date must be after start date")

        if attrs.get("min_followers") and attrs.get("max_followers"):
            if attrs["min_followers"] > attrs["max_followers"]:
                raise serializers.ValidationError("Minimum followers cannot be greater than maximum followers")

        return attrs


class CampaignApplicationSerializer(serializers.ModelSerializer):
    """Serializer for Campaign Application model"""

    campaign_info = serializers.SerializerMethodField()
    influencer_info = serializers.SerializerMethodField()

    class Meta:
        model = CampaignApplication
        fields = [
            "id",
            "campaign",
            "campaign_info",
            "influencer",
            "influencer_info",
            "proposed_rate",
            "message",
            "status",
            "applied_at",
            "updated_at",
        ]
        read_only_fields = ["id", "campaign_info", "influencer", "influencer_info", "applied_at", "updated_at"]

    def get_campaign_info(self, obj):
        """Get basic campaign information"""
        return {
            "title": obj.campaign.title,
            "budget": obj.campaign.budget,
            "status": obj.campaign.status,
            "end_date": obj.campaign.end_date,
        }

    def get_influencer_info(self, obj):
        """Get basic influencer information"""
        return {
            "username": obj.influencer.user.username,
            "total_followers": obj.influencer.total_followers,
            "avg_engagement_rate": obj.influencer.avg_engagement_rate,
            "niche": obj.influencer.niche,
        }

    def validate_proposed_rate(self, value):
        """Validate proposed rate"""
        if value <= 0:
            raise serializers.ValidationError("Proposed rate must be greater than 0")
        return value


class SocialMediaAccountInfluencerSerializer(serializers.ModelSerializer):
    """Serializer for Social Media Account model (for influencers)"""

    class Meta:
        model = SocialMediaAccount
        fields = ["id", "platform", "username", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class InfluencerCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating influencer profiles"""

    class Meta:
        model = Influencer
        fields = ["bio", "niche", "website", "post_rate", "story_rate", "reel_rate", "total_followers", "avg_engagement_rate"]

    def create(self, validated_data):
        """Create influencer profile"""
        user = self.context["request"].user
        validated_data["user"] = user
        return super().create(validated_data)


class InfluencerListSerializer(serializers.ModelSerializer):
    """Simplified serializer for influencer lists"""

    user_username = serializers.CharField(source="user.username", read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Influencer
        fields = [
            "id",
            "user_username",
            "full_name",
            "niche",
            "total_followers",
            "avg_engagement_rate",
            "is_verified",
            "is_available",
        ]

    def get_full_name(self, obj):
        """Get full name of the influencer"""
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username


class CampaignListSerializer(serializers.ModelSerializer):
    """Simplified serializer for campaign lists"""

    creator_username = serializers.CharField(source="creator.username", read_only=True)
    applications_count = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = [
            "id",
            "title",
            "budget",
            "status",
            "start_date",
            "end_date",
            "creator_username",
            "applications_count",
            "min_followers",
            "max_followers",
            "target_platforms",
        ]

    def get_applications_count(self, obj):
        """Get number of applications"""
        return obj.applications.count()


class InfluencerImportSerializer(serializers.Serializer):
    """Serializer for influencer import operations"""

    source = serializers.ChoiceField(choices=["csv", "manual", "upfluence"])
    file = serializers.FileField(required=False, help_text="Required for CSV import")
    influencers = serializers.ListField(child=serializers.DictField(), required=False, help_text="Required for manual import")
    api_key = serializers.CharField(required=False, help_text="Required for Upfluence import")

    def validate(self, attrs):
        """Validate import data based on source"""
        source = attrs.get("source")

        if source == "csv" and not attrs.get("file"):
            raise serializers.ValidationError("File is required for CSV import")

        if source == "manual" and not attrs.get("influencers"):
            raise serializers.ValidationError("Influencers data is required for manual import")

        if source == "upfluence" and not attrs.get("api_key"):
            raise serializers.ValidationError("API key is required for Upfluence import")

        return attrs


class InfluencerAnalyticsSerializer(serializers.Serializer):
    """Serializer for influencer analytics data"""

    influencer_id = serializers.UUIDField(required=False)
    username = serializers.CharField()
    platform = serializers.CharField()
    mention_count = serializers.IntegerField()
    priority_level = serializers.CharField()
    total_likes = serializers.IntegerField(default=0)
    total_comments = serializers.IntegerField(default=0)
    total_shares = serializers.IntegerField(default=0)
    engagement_rate = serializers.FloatField(default=0.0)


class InfluencerDashboardSerializer(serializers.Serializer):
    """Serializer for influencer dashboard data"""

    influencer_profile = InfluencerSerializer()
    stats = serializers.DictField()
    recent_applications = CampaignApplicationSerializer(many=True)
    available_campaigns = CampaignListSerializer(many=True)
