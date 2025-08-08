from django.conf import settings

from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def slack_integration(request):
    """Handle Slack integration"""
    if request.method == "GET":
        # Return current Slack integration status
        return Response({"connected": bool(settings.SLACK_BOT_TOKEN), "webhook_configured": bool(settings.SLACK_WEBHOOK_URL)})

    elif request.method == "POST":
        # Set up Slack integration
        return Response({"message": "Slack integration setup initiated"})


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def canva_integration(request):
    """Handle Canva integration"""
    if request.method == "GET":
        return Response(
            {
                "connected": bool(settings.CANVA_API_KEY),
            }
        )

    elif request.method == "POST":
        return Response({"message": "Canva integration setup initiated"})


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def google_drive_integration(request):
    """Handle Google Drive integration"""
    if request.method == "GET":
        return Response(
            {
                "connected": bool(settings.GOOGLE_DRIVE_CREDENTIALS),
            }
        )

    elif request.method == "POST":
        return Response({"message": "Google Drive integration setup initiated"})


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def dropbox_integration(request):
    """Handle Dropbox integration"""
    if request.method == "GET":
        return Response(
            {
                "connected": bool(settings.DROPBOX_ACCESS_TOKEN),
            }
        )

    elif request.method == "POST":
        return Response({"message": "Dropbox integration setup initiated"})


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def zapier_integration(request):
    """Handle Zapier integration"""
    if request.method == "GET":
        return Response({"connected": bool(settings.ZAPIER_API_KEY)})
    elif request.method == "POST":
        return Response({"message": "Zapier integration setup initiated"})


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def oauth_callback(request):
    """Handle OAuth callbacks from social media platforms"""
    platform = request.query_params.get("platform")
    code = request.query_params.get("code")

    if not platform or not code:
        return Response({"error": "Missing platform or code"}, status=status.HTTP_400_BAD_REQUEST)

    # Handle OAuth callback logic here
    return Response({"message": f"OAuth callback handled for {platform}"})
