from django.contrib import admin

from .models import Influencer, Campaign, CampaignApplication


@admin.register(Influencer)
class InfluencerAdmin(admin.ModelAdmin):
    list_display = ["user", "niche", "total_followers", "avg_engagement_rate", "is_verified", "is_available", "created_at"]
    list_filter = ["niche", "is_verified", "is_available", "created_at"]
    search_fields = ["user__username", "user__email", "user__first_name", "user__last_name"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ["title", "creator", "budget", "status", "start_date", "end_date", "created_at"]
    list_filter = ["status", "start_date", "end_date", "created_at"]
    search_fields = ["title", "creator__username", "description"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(CampaignApplication)
class CampaignApplicationAdmin(admin.ModelAdmin):
    list_display = ["campaign", "influencer", "status", "proposed_rate", "applied_at"]
    list_filter = ["status", "applied_at"]
    search_fields = ["campaign__title", "influencer__user__username"]
    readonly_fields = ["applied_at", "updated_at"]
