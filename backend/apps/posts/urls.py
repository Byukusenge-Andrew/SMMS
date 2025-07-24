from django.urls import path
from . import views

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
    # New endpoints
    # path("calendar/share/", views.share_calendar, name="share-calendar"),
    # path("multi-platform/", views.multi_platform_post, name="multi-platform-post"),
    # path("brand-wall/", views.brand_wall, name="brand-wall"),
]
