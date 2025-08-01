"""
URL configuration for notifications app
"""

from django.urls import path

from .views import (NotificationDetailView, NotificationListView,
                    bulk_mark_read, clear_all_notifications, mark_all_read,
                    notification_preferences, notification_stats,
                    send_test_notification)

app_name = "notifications"

urlpatterns = [
    # Notifications
    path("", NotificationListView.as_view(), name="notification-list"),
    path("<int:pk>/", NotificationDetailView.as_view(), name="notification-detail"),
    path("stats/", notification_stats, name="notification-stats"),
    # Actions
    path("mark-all-read/", mark_all_read, name="mark-all-read"),
    path("bulk-mark-read/", bulk_mark_read, name="bulk-mark-read"),
    path("clear-all/", clear_all_notifications, name="clear-all-notifications"),
    # Preferences and testing
    path("preferences/", notification_preferences, name="notification-preferences"),
    path("test/", send_test_notification, name="test-notification"),
]
