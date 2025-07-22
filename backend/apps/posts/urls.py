from django.urls import path
from .views import (
    PostListCreateView,
    PostDetailView,
    PostTemplateListCreateView,
    PostTemplateDetailView,
    SocialSetListCreateView,
    SocialSetDetailView,
    HolidayListView,
    PostSuggestionListView,
    generate_suggestions,
    bulk_post_actions,
    calendar_view,
    dashboard_stats,
)

urlpatterns = [
    # Posts
    path("", PostListCreateView.as_view(), name="post-list-create"),
    path("<int:pk>/", PostDetailView.as_view(), name="post-detail"),
    path("bulk-actions/", bulk_post_actions, name="bulk-post-actions"),
    path("calendar/", calendar_view, name="calendar-view"),
    path("dashboard/", dashboard_stats, name="dashboard-stats"),
    # Templates
    path("templates/", PostTemplateListCreateView.as_view(), name="template-list-create"),
    path("templates/<int:pk>/", PostTemplateDetailView.as_view(), name="template-detail"),
    # Social Sets
    path("social-sets/", SocialSetListCreateView.as_view(), name="social-set-list-create"),
    path("social-sets/<int:pk>/", SocialSetDetailView.as_view(), name="social-set-detail"),
    # Holidays
    path("holidays/", HolidayListView.as_view(), name="holiday-list"),
    # Suggestions
    path("suggestions/", PostSuggestionListView.as_view(), name="suggestion-list"),
    path("suggestions/generate/", generate_suggestions, name="generate-suggestions"),
]
