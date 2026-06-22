"""
URL configuration for messaging app
"""

from django.urls import path

from . import views

app_name = "messaging"

urlpatterns = [
    # Messages
    path("messages/", views.MessageListCreateView.as_view(), name="message-list"),
    path("messages/<uuid:pk>/", views.MessageDetailView.as_view(), name="message-detail"),
    path("messages/send/", views.send_message_now, name="send-message-now"),
    path("messages/stats/", views.message_stats, name="message-stats"),
    # Automated Messages
    path("automated/", views.AutomatedMessageListCreateView.as_view(), name="automated-message-list"),
    path("automated/<uuid:pk>/", views.AutomatedMessageDetailView.as_view(), name="automated-message-detail"),
    path("automated/<uuid:message_id>/toggle/", views.toggle_automated_message, name="toggle-automated-message"),
    path("automated/<uuid:message_id>/test/", views.test_automated_message, name="test-automated-message"),
    # LinkedIn real-time automation
    path("automated/linkedin/sync/", views.sync_linkedin_automation, name="sync-linkedin-automation"),
]
