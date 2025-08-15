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
    
    # Payment and CRM functionality
    path("", include("apps.core.urls_payment")),
]
