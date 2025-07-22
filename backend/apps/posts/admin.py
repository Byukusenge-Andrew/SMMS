from django.contrib import admin

from .models import Holiday, Post, PostSuggestion, PostTemplate, SocialSet


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["user", "platform", "post_type", "status", "scheduled_time", "is_locked"]
    list_filter = ["platform", "status", "post_type", "is_locked", "created_at"]
    search_fields = ["user__username", "content", "caption", "hashtags"]
    date_hierarchy = "scheduled_time"
    readonly_fields = ["external_post_id", "published_at", "created_at", "updated_at"]


@admin.register(PostTemplate)
class PostTemplateAdmin(admin.ModelAdmin):
    list_display = ["user", "name", "post_type", "created_at"]
    list_filter = ["post_type", "created_at"]
    search_fields = ["user__username", "name", "content"]


@admin.register(SocialSet)
class SocialSetAdmin(admin.ModelAdmin):
    list_display = ["user", "name", "is_active", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["user__username", "name"]


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ["name", "date", "country", "category", "is_active"]
    list_filter = ["country", "category", "is_active", "date"]
    search_fields = ["name", "description"]
    date_hierarchy = "date"


@admin.register(PostSuggestion)
class PostSuggestionAdmin(admin.ModelAdmin):
    list_display = ["user", "suggestion_type", "platform", "confidence_score", "is_used", "created_at"]
    list_filter = ["suggestion_type", "platform", "is_used", "created_at"]
    search_fields = ["user__username", "content"]
    readonly_fields = ["created_at"]
