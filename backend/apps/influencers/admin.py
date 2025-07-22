from django.contrib import admin
from .models import Influencer, SocialMediaAccount


@admin.register(Influencer)
class InfluencerAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_followers', 'avg_engagement_rate', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'user__email']


@admin.register(SocialMediaAccount)
class SocialMediaAccountAdmin(admin.ModelAdmin):
    list_display = ['influencer', 'platform', 'username', 'is_active', 'created_at']
    list_filter = ['platform', 'is_active', 'created_at']
    search_fields = ['influencer__user__username', 'username']