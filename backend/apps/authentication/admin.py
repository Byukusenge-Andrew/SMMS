from django.contrib import admin

from .models import SocialMediaAccount, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "company_name", "subscription_type", "created_at", "is_active"]
    list_filter = ["subscription_type", "is_active", "created_at"]
    search_fields = ["user__username", "user__email", "company_name"]
    date_hierarchy = "created_at"


@admin.register(SocialMediaAccount)
class SocialMediaAccountAdmin(admin.ModelAdmin):
    list_display = ["user", "platform", "username", "is_active", "created_at"]
    list_filter = ["platform", "is_active", "created_at"]
    search_fields = ["user__username", "username", "platform"]
    date_hierarchy = "created_at"
