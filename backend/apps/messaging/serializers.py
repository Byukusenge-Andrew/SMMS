from rest_framework import serializers

from .models import AutomatedMessage, Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = "__all__"
        read_only_fields = ["id", "user", "created_at", "updated_at", "sent_at"]


class AutomatedMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomatedMessage
        fields = "__all__"
        read_only_fields = ["id", "user", "created_at", "updated_at"]
