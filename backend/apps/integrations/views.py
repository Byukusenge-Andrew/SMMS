from django.conf import settings

from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes, parser_classes, throttle_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.request import Request
from apps.core.throttles import AIEndpointThrottle
from apps.integrations.ai_service import get_ai_service

from .slack_service import SlackService
from .models import IntegrationConnection, IntegrationProvider


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def slack_integration(request):
    """Handle Slack integration"""
    if request.method == "GET":
        # Per-user connection if exists, else fallback to global token env
        conn = IntegrationConnection.objects.filter(user=request.user, provider=IntegrationProvider.SLACK).first()
        return Response({
            "connected": bool(conn) or bool(settings.SLACK_BOT_TOKEN),
            "webhook_configured": bool(settings.SLACK_WEBHOOK_URL),
            "scopes": (conn.scopes if conn else []),
            "per_user": bool(conn)})

    elif request.method == "POST":
        action = request.data.get("action", "connect")
        if action == "disconnect":
            IntegrationConnection.objects.filter(user=request.user, provider=IntegrationProvider.SLACK).delete()
            return Response({"message": "Slack disconnected"})
        # For now just create a placeholder per-user record (no OAuth yet)
        conn, _ = IntegrationConnection.objects.get_or_create(user=request.user, provider=IntegrationProvider.SLACK)
        return Response({"message": "Slack connected", "connection_id": str(conn.id)})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def slack_conversations(request: Request):
    """List Slack conversations (channels and DMs) for the connected bot token."""
    types = request.query_params.get("types", "public_channel,private_channel,im")
    svc = SlackService()
    data = svc.list_conversations(types=types)
    status_code = status.HTTP_200_OK if data.get("ok", True) else status.HTTP_400_BAD_REQUEST
    return Response(data, status=status_code)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def slack_history(request: Request):
    """Retrieve message history for a Slack channel or DM (channel param)."""
    channel = request.query_params.get("channel")
    if not channel:
        return Response({"ok": False, "error": "missing_channel"}, status=400)
    limit = int(request.query_params.get("limit", 100))
    cursor = request.query_params.get("cursor")
    svc = SlackService()
    data = svc.conversation_history(channel, limit=limit, cursor=cursor)
    return Response(data, status=200 if data.get("ok", True) else 400)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def slack_auth_status(request: Request):
    svc = SlackService()
    data = svc.auth_status()
    return Response(data, status=200 if data.get("ok", True) else 400)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def slack_send_message(request: Request):
    """Send a Slack message to a channel or DM. Body: { recipient: string, text: string }"""
    payload = request.data or {}
    recipient = payload.get("recipient")
    text = payload.get("text")
    if not recipient or not text:
        return Response({"ok": False, "error": "missing_fields"}, status=status.HTTP_400_BAD_REQUEST)

    svc = SlackService()
    # Resolve recipient
    if recipient.startswith("@"):
        user_id = svc.find_user_id_by_username(recipient)
        if not user_id:
            return Response({"ok": False, "error": "user_not_found"}, status=status.HTTP_404_NOT_FOUND)
        resp = svc.send_dm(user_id, text)
        code = status.HTTP_200_OK if resp.get("ok", True) else status.HTTP_400_BAD_REQUEST
        return Response(resp, status=code)

    channel_id = None
    if recipient.startswith("#"):
        name = recipient.lstrip("#")
        channel_id = svc.find_channel_id_by_name(name) or recipient
    else:
        channel_id = recipient

    resp = svc.post_message(channel_id, text)
    code = status.HTTP_200_OK if resp.get("ok", True) else status.HTTP_400_BAD_REQUEST
    return Response(resp, status=code)


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def canva_integration(request):
    """Handle Canva integration"""
    if request.method == "GET":
        conn = IntegrationConnection.objects.filter(user=request.user, provider=IntegrationProvider.CANVA).first()
        return Response({"connected": bool(conn), "per_user": bool(conn)})

    elif request.method == "POST":
        action = request.data.get("action", "connect")
        if action == "disconnect":
            IntegrationConnection.objects.filter(user=request.user, provider=IntegrationProvider.CANVA).delete()
            return Response({"message": "Canva disconnected"})
        conn, _ = IntegrationConnection.objects.get_or_create(user=request.user, provider=IntegrationProvider.CANVA)
        return Response({"message": "Canva connected", "connection_id": str(conn.id)})


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def google_drive_integration(request):
    """Handle Google Drive integration"""
    if request.method == "GET":
        conn = IntegrationConnection.objects.filter(user=request.user, provider=IntegrationProvider.GOOGLE_DRIVE).first()
        return Response({"connected": bool(conn), "per_user": bool(conn)})

    elif request.method == "POST":
        action = request.data.get("action", "connect")
        if action == "disconnect":
            IntegrationConnection.objects.filter(user=request.user, provider=IntegrationProvider.GOOGLE_DRIVE).delete()
            return Response({"message": "Google Drive disconnected"})
        conn, _ = IntegrationConnection.objects.get_or_create(user=request.user, provider=IntegrationProvider.GOOGLE_DRIVE)
        return Response({"message": "Google Drive connected", "connection_id": str(conn.id)})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def google_drive_files(request: Request):
    """List files from Google Drive (placeholder mock until real OAuth implemented)."""
    # In production, use Google Drive API with stored credentials in IntegrationConnection.metadata
    mock_files = [
        {"id": "file_1", "name": "Marketing Plan.docx", "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
        {"id": "file_2", "name": "Q3 Campaign Assets", "mime_type": "application/vnd.google-apps.folder"},
    ]
    return Response({"files": mock_files})


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def google_drive_import(request: Request):
    """Import (attach) a file by id from Google Drive (placeholder)."""
    file_id = request.data.get("file_id")
    if not file_id:
        return Response({"error": "file_id required"}, status=400)
    # Simulate storing a media reference
    return Response({"imported": True, "file_id": file_id})


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def dropbox_integration(request):
    """Handle Dropbox integration"""
    if request.method == "GET":
        conn = IntegrationConnection.objects.filter(user=request.user, provider=IntegrationProvider.DROPBOX).first()
        return Response({"connected": bool(conn), "per_user": bool(conn)})

    elif request.method == "POST":
        action = request.data.get("action", "connect")
        if action == "disconnect":
            IntegrationConnection.objects.filter(user=request.user, provider=IntegrationProvider.DROPBOX).delete()
            return Response({"message": "Dropbox disconnected"})
        conn, _ = IntegrationConnection.objects.get_or_create(user=request.user, provider=IntegrationProvider.DROPBOX)
        return Response({"message": "Dropbox connected", "connection_id": str(conn.id)})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def dropbox_files(request: Request):
    """List Dropbox files (placeholder)."""
    mock_files = [
        {"id": "dbx_1", "name": "AdCreative.png", "path": "/Campaign/AdCreative.png"},
        {"id": "dbx_2", "name": "VideoDraft.mp4", "path": "/Campaign/VideoDraft.mp4"},
    ]
    return Response({"files": mock_files})


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def dropbox_import(request: Request):
    path = request.data.get("path")
    if not path:
        return Response({"error": "path required"}, status=400)
    return Response({"imported": True, "path": path})


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def zapier_integration(request):
    """Handle Zapier integration"""
    if request.method == "GET":
        conn = IntegrationConnection.objects.filter(user=request.user, provider=IntegrationProvider.ZAPIER).first()
        return Response({"connected": bool(conn), "per_user": bool(conn)})
    elif request.method == "POST":
        action = request.data.get("action", "connect")
        if action == "disconnect":
            IntegrationConnection.objects.filter(user=request.user, provider=IntegrationProvider.ZAPIER).delete()
            return Response({"message": "Zapier disconnected"})
        conn, _ = IntegrationConnection.objects.get_or_create(user=request.user, provider=IntegrationProvider.ZAPIER)
        return Response({"message": "Zapier connected", "connection_id": str(conn.id)})


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
@throttle_classes([AIEndpointThrottle])
def hashtag_suggestions(request: Request):
    """Return AI-generated hashtag suggestions for given content/platform."""
    content = request.data.get("content", "")
    platform = request.data.get("platform", "instagram")
    if not content:
        return Response({"error": "content required"}, status=400)
    ai = get_ai_service()
    hashtags = ai.generate_hashtags(content, platform, user_id=request.user.id)
    return Response({"hashtags": hashtags})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def optimal_posting_times(request: Request):
    """Return cached / generated optimal posting times (reuse prediction task)."""
    import logging
    logger = logging.getLogger(__name__)
    from apps.analytics.tasks import predict_optimal_posting_times
    try:
        data = predict_optimal_posting_times.apply(args=[request.user.id]).get()  # type: ignore
        if data:
            return Response(data)
    except Exception as e:
        logger.error(f"Error in optimal_posting_times view: {str(e)}")
    
    # Fallback default times
    default_times = [
        {"hour": 9, "minute": 0, "day_of_week": 0, "engagement_score": 85.0},
        {"hour": 12, "minute": 0, "day_of_week": 2, "engagement_score": 75.0},
        {"hour": 15, "minute": 0, "day_of_week": 4, "engagement_score": 90.0},
        {"hour": 18, "minute": 0, "day_of_week": 1, "engagement_score": 65.0},
        {"hour": 11, "minute": 0, "day_of_week": 3, "engagement_score": 70.0},
        {"hour": 13, "minute": 0, "day_of_week": 5, "engagement_score": 55.0},
    ]
    return Response({"optimal_times": default_times, "confidence": 0.6})


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
