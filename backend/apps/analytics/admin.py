from django.contrib import admin
from .models import AnalyticsData, PerformanceReport, BestPerformingPost, CommentAnalytics, PlatformAverage

@admin.register(AnalyticsData)
class AnalyticsDataAdmin(admin.ModelAdmin):
    list_display = ['user', 'platform', 'metric_type', 'value', 'date']
    list_filter = ['platform', 'metric_type', 'date']
    search_fields = ['user__username', 'platform']

@admin.register(PerformanceReport)
class PerformanceReportAdmin(admin.ModelAdmin):
    list_display = ['user', 'report_type', 'title', 'is_generated', 'created_at']
    list_filter = ['report_type', 'is_generated', 'created_at']
    search_fields = ['user__username', 'title']

@admin.register(BestPerformingPost)
class BestPerformingPostAdmin(admin.ModelAdmin):
    list_display = ['user', 'platform', 'metric_type', 'rank', 'metric_value']
    list_filter = ['platform', 'metric_type', 'rank']
    search_fields = ['user__username']

@admin.register(CommentAnalytics)
class CommentAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['post', 'sentiment', 'sentiment_score', 'author_username']
    list_filter = ['sentiment', 'created_at']
    search_fields = ['author_username', 'comment_text']

@admin.register(PlatformAverage)
class PlatformAverageAdmin(admin.ModelAdmin):
    list_display = ['user', 'platform', 'period_type', 'avg_engagement_rate']
    list_filter = ['platform', 'period_type']
    search_fields = ['user__username']
