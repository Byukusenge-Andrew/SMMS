from django.urls import path
from .views import slack_integration, canva_integration, google_drive_integration, dropbox_integration, oauth_callback

urlpatterns = [
    path("slack/", slack_integration, name="slack-integration"),
    path("canva/", canva_integration, name="canva-integration"),
    path("google-drive/", google_drive_integration, name="google-drive"),
    path("dropbox/", dropbox_integration, name="dropbox"),
    path("oauth/callback/", oauth_callback, name="oauth-callback"),
]
