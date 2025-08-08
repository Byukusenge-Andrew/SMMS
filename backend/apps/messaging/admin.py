from django.contrib import admin
from .models import Message, AutomatedMessage


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'platform', 'status', 'message_type', 'created_at', 'sent_at')
    list_filter = ('platform', 'status', 'message_type')
    search_fields = ('recipient', 'content')
    readonly_fields = ('created_at', 'sent_at')
    fieldsets = (
        (None, {
            'fields': ('user', 'platform', 'recipient', 'content')
        }),
        ('Status & Type', {
            'fields': ('status', 'message_type', 'priority')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'sent_at')
        }),
    )


@admin.register(AutomatedMessage)
class AutomatedMessageAdmin(admin.ModelAdmin):
    list_display = ('user', 'platform', 'trigger', 'active', 'updated_at')
    list_filter = ('platform', 'trigger', 'active')
    search_fields = ('user__username', 'content_template')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('user', 'platform', 'trigger', 'active')
        }),
        ('Configuration', {
            'fields': ('content_template', 'delay_minutes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
