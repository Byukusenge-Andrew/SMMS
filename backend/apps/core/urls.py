"""
URL routing for rate limiting API
"""

from django.urls import include, path

from .views import (
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
]
