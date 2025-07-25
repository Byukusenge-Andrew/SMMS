"""
URL configuration for posts app
"""

from django.urls import path

from . import views

app_name = "posts"

urlpatterns = [
    # Posts
    path("", views.PostListCreateView.as_view(), name="post-list-create"),
    path("<uuid:pk>/", views.PostDetailView.as_view(), name="post-detail"),
    path("bulk-actions/", views.bulk_post_actions, name="bulk-actions"),
    path("calendar/", views.calendar_view, name="calendar"),
    path("dashboard/", views.dashboard_stats, name="dashboard-stats"),
    # Templates
    path("templates/", views.PostTemplateListCreateView.as_view(), name="template-list-create"),
    path("templates/<uuid:pk>/", views.PostTemplateDetailView.as_view(), name="template-detail"),
    # Social Sets
    path("social-sets/", views.SocialSetListCreateView.as_view(), name="socialset-list-create"),
    path("social-sets/<uuid:pk>/", views.SocialSetDetailView.as_view(), name="socialset-detail"),
    # Holidays
    path("holidays/", views.HolidayListView.as_view(), name="holiday-list"),
    # Suggestions
    path("suggestions/", views.PostSuggestionListView.as_view(), name="suggestion-list"),
    path("suggestions/generate/", views.generate_suggestions, name="generate-suggestions"),
    # Advanced Features
    path("calendar/share/", views.share_calendar, name="share-calendar"),
    path("multi-platform/", views.multi_platform_post, name="multi-platform-post"),
    path("brand-wall/", views.brand_wall, name="brand-wall"),
    # AI-Powered Features
    path("ai/content-suggestions/", views.ai_content_suggestions, name="ai-content-suggestions"),
    path("ai/analyze-content/", views.analyze_content_performance, name="analyze-content"),
    path("ai/optimal-times/", views.get_optimal_posting_times, name="optimal-posting-times"),
    path("ai/trigger-insights/", views.trigger_ai_insights, name="trigger-ai-insights"),
    # AI Sentiment Analysis
    path("ai/sentiment/comment/", views.analyze_single_comment_sentiment, name="analyze-single-comment-sentiment"),
    path("ai/sentiment/post/<uuid:post_id>/", views.analyze_comment_sentiment, name="analyze-post-comments-sentiment"),
    path("ai/sentiment/batch/", views.batch_analyze_post_comments, name="batch-analyze-comments-sentiment"),
]
