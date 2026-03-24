from django.contrib import admin
from .models import Contact, Pipeline, Deal, Activity


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ["first_name", "last_name", "email", "company", "status", "owner", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["first_name", "last_name", "email", "company"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(Pipeline)
class PipelineAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "created_at"]
    search_fields = ["name"]
    readonly_fields = ["id", "created_at"]


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ["title", "stage", "value", "currency", "contact", "pipeline", "owner", "created_at"]
    list_filter = ["stage", "currency"]
    search_fields = ["title"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ["title", "type", "completed", "contact", "deal", "owner", "created_at"]
    list_filter = ["type", "completed"]
    search_fields = ["title"]
    readonly_fields = ["id", "created_at"]
