"""
Media serializers for API responses
"""

import os
import uuid
from django.utils import timezone
from rest_framework import serializers
from .models import MediaFile, MediaFolder


class MediaFileSerializer(serializers.ModelSerializer):
    """Serializer for MediaFile model"""
    
    url = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()
    dimensions = serializers.SerializerMethodField()
    
    class Meta:
        model = MediaFile
        fields = [
            'id', 'name', 'original_name', 'size', 'media_type', 'mime_type',
            'width', 'height', 'duration', 'tags', 'url', 'thumbnail',
            'dimensions', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'size', 'mime_type']
    
    def get_url(self, obj):
        """Get file URL"""
        return obj.file_url
    
    def get_thumbnail(self, obj):
        """Get thumbnail URL"""
        return obj.thumbnail_url
    
    def get_dimensions(self, obj):
        """Get dimensions as dict"""
        if obj.width and obj.height:
            return {
                'width': obj.width,
                'height': obj.height
            }
        return None


class MediaFileUploadSerializer(serializers.ModelSerializer):
    """Serializer for uploading media files"""
    
    file = serializers.FileField()
    tags = serializers.JSONField(required=False, default=list)
    
    class Meta:
        model = MediaFile
        fields = ['file', 'name', 'tags']
    
    def create(self, validated_data):
        """Create media file with metadata extraction"""
        file = validated_data['file']
        
        # Extract metadata
        validated_data['original_name'] = file.name
        validated_data['size'] = file.size
        validated_data['mime_type'] = file.content_type
        
        # Determine media type
        if file.content_type.startswith('image/'):
            validated_data['media_type'] = 'image'
        elif file.content_type.startswith('video/'):
            validated_data['media_type'] = 'video'
        elif file.content_type.startswith('audio/'):
            validated_data['media_type'] = 'audio'
        else:
            validated_data['media_type'] = 'image'  # Default fallback
            
        # Generate timestamped filename
        name, ext = os.path.splitext(file.name)
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        unique_id = uuid.uuid4().hex[:8]
        validated_data['name'] = f"{name}_{timestamp}_{unique_id}{ext}"
        
        # Set default name if not provided
        if not validated_data.get('name'):
            validated_data['name'] = file.name
        
        # Set user from request
        validated_data['user'] = self.context['request'].user
        
        return super().create(validated_data)


class MediaFolderSerializer(serializers.ModelSerializer):
    """Serializer for MediaFolder model"""
    
    class Meta:
        model = MediaFolder
        fields = ['id', 'name', 'parent', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        """Create folder for current user"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
