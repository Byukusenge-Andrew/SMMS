from django.contrib import admin

from .models import IntegrationConnection, SocialMediaAccount


@admin.register(IntegrationConnection)
class IntegrationConnectionAdmin(admin.ModelAdmin):
    list_display = ("user", "provider", "active", "connected_at", "token_expires_at")
    list_filter = ("provider", "active")
    search_fields = ("user__username", "provider")
    readonly_fields = ("connected_at", "updated_at")


@admin.register(SocialMediaAccount)
class SocialMediaAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "platform", "username", "is_active", "is_verified", "connected_at")
    list_filter = ("platform", "is_active", "is_verified")
    search_fields = ("username", "user__username")
    readonly_fields = ("connected_at", "last_updated", "last_sync")
