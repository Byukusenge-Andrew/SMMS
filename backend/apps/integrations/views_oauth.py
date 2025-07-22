from django.conf import settings
from django.contrib.auth import login
from django.shortcuts import redirect

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from social_django.utils import psa


class OAuthLoginView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, provider):
        """
        Redirect user to the OAuth provider's login page.
        """
        if provider == "google":
            redirect_uri = request.build_absolute_uri("/oauth/complete/google-oauth2/")
            url = f"https://accounts.google.com/o/oauth2/auth?client_id={settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY}&redirect_uri={redirect_uri}&response_type=code&scope=openid email profile"
            return redirect(url)
        elif provider == "github":
            redirect_uri = request.build_absolute_uri("/oauth/complete/github/")
            url = f"https://github.com/login/oauth/authorize?client_id={settings.SOCIAL_AUTH_GITHUB_KEY}&redirect_uri={redirect_uri}&scope=user:email"
            return redirect(url)
        return Response({"error": "Unsupported provider"}, status=status.HTTP_400_BAD_REQUEST)


class OAuthCallbackView(APIView):
    permission_classes = [AllowAny]

    @psa("social:complete")
    def get(self, request, backend):
        """
        Handle OAuth callback and authenticate user.
        """
        # The actual authentication is handled by social-auth-app-django
        # This view can be used for custom post-auth logic if needed
        return Response({"detail": "OAuth callback handled."})
