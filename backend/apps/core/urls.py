"""
URL routing for core functionality including rate limiting, payments, and CRM
"""

from django.urls import include, path

# Import rate limiting views from the dedicated rate limiting views file
from .rate_limit_views import (
    IPBlacklistView,
    IPWhitelistView,
    RateLimitDashboardView,
    RateLimitLogsView,
    RateLimitStatsView,
    RateLimitTestView,
)

# Import log visualizer views
from .views import (
    log_viewer_html,
    log_list_api,
    log_content_api,
    log_clear_api,
    log_download_api,
)

app_name = "core"

urlpatterns = [
    # Rate limiting management
    path("rate-limit/dashboard/", RateLimitDashboardView.as_view(), name="rate-limit-dashboard"),
    path("rate-limit/logs/", RateLimitLogsView.as_view(), name="rate-limit-logs"),
    path("rate-limit/stats/", RateLimitStatsView.as_view(), name="rate-limit-stats"),
    path("rate-limit/test/", RateLimitTestView.as_view(), name="rate-limit-test"),
    # IP management
    path("ip/whitelist/", IPWhitelistView.as_view(), name="ip-whitelist"),
    path("ip/blacklist/", IPBlacklistView.as_view(), name="ip-blacklist"),
    
    # Log visualizer management
    path("logs/", log_viewer_html, name="log-viewer-html"),
    path("logs/api/list/", log_list_api, name="log-list-api"),
    path("logs/api/content/<str:filename>/", log_content_api, name="log-content-api"),
    path("logs/api/clear/<str:filename>/", log_clear_api, name="log-clear-api"),
    path("logs/api/download/<str:filename>/", log_download_api, name="log-download-api"),
    
    # Payment and CRM functionality
    path("", include("apps.core.urls_payment")),
]
