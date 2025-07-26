from django.utils import timezone

from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import AutomatedMessage, Message
from .serializers import AutomatedMessageSerializer, MessageSerializer
from .tasks import send_message


class MessageListCreateView(generics.ListCreateAPIView):
    """List and create messages"""

    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Message.objects.filter(user=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        message = serializer.save(user=self.request.user)
        # Queue message for sending
        send_message.delay(str(message.id))


class MessageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a message"""

    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Message.objects.filter(user=self.request.user)


class AutomatedMessageListCreateView(generics.ListCreateAPIView):
    """List and create automated messages"""

    serializer_class = AutomatedMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return AutomatedMessage.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AutomatedMessageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete an automated message"""

    serializer_class = AutomatedMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return AutomatedMessage.objects.filter(user=self.request.user)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def send_message_now(request):
    """Send a message immediately"""
    try:
        content = request.data.get("content")
        platform = request.data.get("platform")
        recipient = request.data.get("recipient")
        priority = request.data.get("priority", "normal")

        if not all([content, platform, recipient]):
            return Response({"error": "Content, platform, and recipient are required"}, status=status.HTTP_400_BAD_REQUEST)

        message = Message.objects.create(
            user=request.user,
            platform=platform,
            recipient=recipient,
            content=content,
            priority=priority,
            message_type="direct",
        )

        # Send immediately
        send_message.delay(str(message.id))

        return Response({"message_id": str(message.id), "status": "queued", "platform": platform, "recipient": recipient})

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def toggle_automated_message(request, message_id):
    """Toggle automated message active status"""
    try:
        automated_msg = AutomatedMessage.objects.get(id=message_id, user=request.user)

        automated_msg.is_active = not automated_msg.is_active
        automated_msg.save()

        return Response(
            {
                "id": str(automated_msg.id),
                "name": automated_msg.name,
                "is_active": automated_msg.is_active,
                "status": "active" if automated_msg.is_active else "inactive",
            }
        )

    except AutomatedMessage.DoesNotExist:
        return Response({"error": "Automated message not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def message_stats(request):
    """Get messaging statistics for user"""
    try:
        user_messages = Message.objects.filter(user=request.user)

        stats = {
            "total_messages": user_messages.count(),
            "sent_messages": user_messages.filter(status="sent").count(),
            "pending_messages": user_messages.filter(status="pending").count(),
            "failed_messages": user_messages.filter(status="failed").count(),
            "platform_breakdown": {},
            "recent_activity": [],
        }

        # Platform breakdown
        platforms = user_messages.values_list("platform", flat=True).distinct()
        for platform in platforms:
            platform_count = user_messages.filter(platform=platform).count()
            stats["platform_breakdown"][platform] = platform_count

        # Recent activity (last 5 messages)
        recent_messages = user_messages.order_by("-created_at")[:5]
        for msg in recent_messages:
            stats["recent_activity"].append(
                {
                    "id": str(msg.id),
                    "platform": msg.platform,
                    "recipient": msg.recipient,
                    "status": msg.status,
                    "created_at": msg.created_at.isoformat(),
                    "content_preview": msg.content[:50] + "..." if len(msg.content) > 50 else msg.content,
                }
            )

        return Response(stats)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def test_automated_message(request, message_id):
    """Test an automated message by sending it once"""
    try:
        automated_msg = AutomatedMessage.objects.get(id=message_id, user=request.user)

        test_recipient = request.data.get("test_recipient")
        if not test_recipient:
            return Response({"error": "Test recipient is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Create a test message
        test_message = Message.objects.create(
            user=request.user,
            platform=automated_msg.platform,
            recipient=test_recipient,
            content=f"[TEST] {automated_msg.template_content}",
            message_type="test",
            priority="normal",
        )

        # Send the test message
        send_message.delay(str(test_message.id))

        return Response(
            {
                "message": "Test message sent successfully",
                "test_message_id": str(test_message.id),
                "automated_message_id": str(automated_msg.id),
            }
        )

    except AutomatedMessage.DoesNotExist:
        return Response({"error": "Automated message not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
