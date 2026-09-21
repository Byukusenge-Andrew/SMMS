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
    path("<uuid:post_id>/submit-approval/", views.submit_post_for_approval, name="post-submit-approval"),
    path("<uuid:post_id>/approve/", views.approve_post, name="post-approve"),
    path("<uuid:post_id>/reject/", views.reject_post, name="post-reject"),
    path("<uuid:post_id>/add-to-queue/", views.add_post_to_queue, name="post-add-to-queue"),
    path("bulk-actions/", views.bulk_post_actions, name="bulk-actions"),
    path("calendar/", views.calendar_view, name="calendar"),
    path("dashboard/", views.dashboard_stats, name="dashboard-stats"),
    # Queue & Dynamic Scheduling
    path("queue/", views.queue_posts_list, name="queue-posts-list"),
    path("queue/next-slot/", views.get_next_queue_slot, name="queue-next-slot"),
    path("schedule-slots/", views.PostingScheduleSlotListCreateView.as_view(), name="schedule-slots-list-create"),
    path("schedule-slots/<uuid:pk>/", views.PostingScheduleSlotDetailView.as_view(), name="schedule-slots-detail"),
    path("schedule-slots/bulk/", views.bulk_create_schedule_slots, name="schedule-slots-bulk"),
    # Scheduled Posts
    path("scheduled/", views.ScheduledPostListCreateView.as_view(), name="scheduled-list-create"),
    path("scheduled/<uuid:pk>/", views.ScheduledPostDetailView.as_view(), name="scheduled-detail"),
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
    path("ai/content-suggestions/stream/", views.ai_content_suggestions_stream, name="ai-content-suggestions-stream"),
    path("ai/feedback/", views.ai_suggestion_feedback, name="ai-suggestion-feedback"),
    path("ai/analyze-content/", views.analyze_content_performance, name="analyze-content"),

    path("ai/optimal-times/", views.get_optimal_posting_times, name="optimal-posting-times"),
    path("ai/trigger-insights/", views.trigger_ai_insights, name="trigger-ai-insights"),
    # AI Sentiment Analysis
    path("ai/sentiment/comment/", views.analyze_single_comment_sentiment, name="analyze-single-comment-sentiment"),
    path("ai/sentiment/post/<uuid:post_id>/", views.analyze_comment_sentiment, name="analyze-post-comments-sentiment"),
    path("ai/sentiment/batch/", views.batch_analyze_post_comments, name="batch-analyze-comments-sentiment"),
]
