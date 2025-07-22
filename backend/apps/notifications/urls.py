from django.urls import path
from .views import (
    NotificationListView, NotificationDetailView, mark_all_read,
    notification_preferences, send_test_notification
)

urlpatterns = [
    path('', NotificationListView.as_view(), name='notification-list'),
    path('<int:pk>/', NotificationDetailView.as_view(), name='notification-detail'),
    path('mark-all-read/', mark_all_read, name='mark-all-read'),
    path('preferences/', notification_preferences, name='notification-preferences'),
    path('test/', send_test_notification, name='test-notification'),
]