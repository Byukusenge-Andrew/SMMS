from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from .models import Message, AutomatedMessage
from .serializers import MessageSerializer, AutomatedMessageSerializer
from .tasks import send_message, send_automated_message

class MessageListCreateView(generics.ListCreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Message.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def send_message_now(request):
    """Send a message immediately"""
    try:
        content = request.data.get('content')
        platform = request.data.get('platform')
        recipient = request.data.get('recipient')
        priority = request.data.get('priority', 'normal')
        
        message = Message.objects.create(
            user=request.user,
            platform=platform,
            recipient=recipient,
            content=content,
            priority=priority,
            message_type='direct'
        )
        
        # Send immediately
        send_message.delay(message.id)
        
        return Response({
            "message_id": str(message.id),
            "status": "queued",
            "platform": platform
        })
        
    except Exception as e:
        return Response(
            {"error": str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def send_automated_message(request):
    """Set up automated messaging"""
    try:
        serializer = AutomatedMessageSerializer(data=request.data)
        if serializer.is_valid():
            automated_msg = serializer.save(user=request.user)
            
            return Response({
                "id": str(automated_msg.id),
                "name": automated_msg.name,
                "status": "active" if automated_msg.active else "inactive"
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        return Response(
            {"error": str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )