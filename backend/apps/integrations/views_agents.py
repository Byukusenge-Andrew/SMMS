from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from .models import AIAgent
from .serializers import AIAgentSerializer

class AIAgentListCreateView(ListCreateAPIView):
    """List or create custom AI Agents for the authenticated user"""
    serializer_class = AIAgentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return AIAgent.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AIAgentDetailView(RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a custom AI Agent"""
    serializer_class = AIAgentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AIAgent.objects.filter(user=self.request.user)
