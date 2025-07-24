from django.contrib import admin
from .models import Message, AutomatedMessage


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["user", "platform", "recipient", "status", "priority", "scheduled_time", "sent_at", "created_at"]
    list_filter = ["platform", "status", "priority", "created_at", "sent_at"]
    search_fields = ["user__username", "recipient", "content"]
    readonly_fields = ["created_at", "updated_at", "sent_at"]
    date_hierarchy = "created_at"


@admin.register(AutomatedMessage)
class AutomatedMessageAdmin(admin.ModelAdmin):
    list_display = ["user", "trigger_type", "platform", "is_active", "created_at"]
    list_filter = ["trigger_type", "platform", "is_active", "created_at"]
    search_fields = ["user__username", "template_content"]
    readonly_fields = ["created_at", "updated_at"]
