"""
Enhanced media serializers for bulk upload and user-specific organization
"""

import os
import mimetypes
from typing import List, Dict, Any
from django.core.files.storage import default_storage
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import MediaFile, MediaFolder, MediaUploadBatch
from apps.core.upload_paths import user_media_upload_path, user_thumbnail_upload_path
from apps.core.permissions import ClientDataValidator


class MediaFolderSerializer(serializers.ModelSerializer):
    """Serializer for media folders"""
    
    file_count = serializers.SerializerMethodField()
    total_size = serializers.SerializerMethodField()
    
    class Meta:
        model = MediaFolder
        fields = [
            'id', 'name', 'description', 'parent', 'created_at', 
            'updated_at', 'file_count', 'total_size'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_file_count(self, obj):
        """Get number of files in folder"""
        return obj.files.count()
    
    def get_total_size(self, obj):
        """Get total size of files in folder"""
        from django.db.models import Sum
        return obj.files.aggregate(total=Sum('size'))['total'] or 0
    
    def validate(self, attrs):
        """Validate folder data"""
        user = self.context.get('request').user
        
        # Check parent folder belongs to user
        if attrs.get('parent'):
            parent = attrs['parent']
            if parent.user != user:
                raise ValidationError("Invalid parent folder")
        
        return attrs
    
    def create(self, validated_data):
        """Create folder with user assignment"""
        user = self.context.get('request').user
        validated_data['user'] = user
        return super().create(validated_data)


class MediaFileUploadSerializer(serializers.ModelSerializer):
    """Enhanced serializer for individual file uploads"""
    
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        allow_empty=True
    )
    folder = serializers.PrimaryKeyRelatedField(
        queryset=MediaFolder.objects.none(),
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = MediaFile
        fields = [
            'file', 'name', 'description', 'alt_text', 'tags', 
            'folder', 'media_type', 'size'
        ]
        read_only_fields = ['media_type', 'size']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set folder queryset based on user
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            self.fields['folder'].queryset = MediaFolder.objects.filter(user=request.user)
    
    def validate_file(self, value):
        """Validate uploaded file"""
        if not value:
            raise ValidationError("File is required")
        
        # Check file size (50MB limit)
        max_size = 50 * 1024 * 1024  # 50MB
        if value.size > max_size:
            raise ValidationError(f"File too large. Maximum size is {max_size // (1024*1024)}MB")
        
        # Check file type
        allowed_types = [
            'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml',
            'video/mp4', 'video/quicktime', 'video/webm', 'video/avi',
            'audio/mp3', 'audio/wav', 'audio/ogg', 'audio/mpeg'
        ]
        
        content_type = getattr(value, 'content_type', None)
        if content_type not in allowed_types:
            raise ValidationError(f"File type {content_type} not allowed")
        
        return value
    
    def validate_tags(self, value):
        """Validate tags list"""
        if value and len(value) > 10:
            raise ValidationError("Maximum 10 tags allowed")
        
        # Clean and validate individual tags
        cleaned_tags = []
        for tag in value or []:
            tag = tag.strip().lower()
            if tag and len(tag) <= 50:
                cleaned_tags.append(tag)
        
        return cleaned_tags
    
    def validate_folder(self, value):
        """Validate folder belongs to user"""
        if value:
            request = self.context.get('request')
            if not request or value.user != request.user:
                raise ValidationError("Invalid folder")
        return value
    
    def create(self, validated_data):
        """Create media file with metadata extraction"""
        user = validated_data.pop('user', None)
        if not user:
            user = self.context.get('request').user
        
        file = validated_data['file']
        
        # Auto-detect media type
        content_type = file.content_type
        if content_type.startswith('image/'):
            media_type = 'image'
        elif content_type.startswith('video/'):
            media_type = 'video'
        elif content_type.startswith('audio/'):
            media_type = 'audio'
        else:
            media_type = 'document'
        
        validated_data['media_type'] = media_type
        validated_data['size'] = file.size
        validated_data['user'] = user
        
        # Set upload path
        file.name = user_media_upload_path(
            instance=type('obj', (), {'user': user, 'file': file})(),
            filename=file.name
        )
        
        return super().create(validated_data)


class BulkMediaUploadSerializer(serializers.Serializer):
    """Serializer for bulk file uploads"""
    
    files = serializers.ListField(
        child=serializers.FileField(),
        min_length=1,
        max_length=20,
        help_text="List of files to upload (max 20)"
    )
    folder = serializers.PrimaryKeyRelatedField(
        queryset=MediaFolder.objects.none(),
        required=False,
        allow_null=True,
        help_text="Optional folder to organize files"
    )
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        allow_empty=True,
        help_text="Tags to apply to all uploaded files"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set folder queryset based on user
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            self.fields['folder'].queryset = MediaFolder.objects.filter(user=request.user)
    
    def validate_files(self, value):
        """Validate all uploaded files"""
        if len(value) > 20:
            raise ValidationError("Maximum 20 files allowed per bulk upload")
        
        total_size = sum(file.size for file in value)
        max_total_size = 500 * 1024 * 1024  # 500MB total
        
        if total_size > max_total_size:
            raise ValidationError(f"Total file size too large. Maximum {max_total_size // (1024*1024)}MB")
        
        # Validate each file individually
        for file in value:
            # Use the individual file validator
            upload_serializer = MediaFileUploadSerializer()
            upload_serializer.validate_file(file)
        
        return value
    
    def validate_tags(self, value):
        """Validate tags for bulk upload"""
        upload_serializer = MediaFileUploadSerializer()
        return upload_serializer.validate_tags(value)
    
    def validate_folder(self, value):
        """Validate folder for bulk upload"""
        if value:
            request = self.context.get('request')
            if not request or value.user != request.user:
                raise ValidationError("Invalid folder")
        return value


class MediaFileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating media file metadata"""
    
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        allow_empty=True
    )
    folder = serializers.PrimaryKeyRelatedField(
        queryset=MediaFolder.objects.none(),
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = MediaFile
        fields = [
            'name', 'description', 'alt_text', 'tags', 'folder'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set folder queryset based on user
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            self.fields['folder'].queryset = MediaFolder.objects.filter(user=request.user)
    
    def validate_tags(self, value):
        """Validate tags update"""
        upload_serializer = MediaFileUploadSerializer()
        return upload_serializer.validate_tags(value)
    
    def validate_folder(self, value):
        """Validate folder move"""
        if value:
            request = self.context.get('request')
            if not request or value.user != request.user:
                raise ValidationError("Invalid folder")
        return value


class MediaFileSerializer(serializers.ModelSerializer):
    """Enhanced serializer for media file responses"""
    
    folder_name = serializers.CharField(source='folder.name', read_only=True)
    folder_path = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    metadata = serializers.SerializerMethodField()
    
    class Meta:
        model = MediaFile
        fields = [
            'id', 'name', 'description', 'alt_text', 'file', 'file_url',
            'thumbnail', 'thumbnail_url', 'download_url', 'media_type',
            'size', 'width', 'height', 'duration', 'tags', 'folder',
            'folder_name', 'folder_path', 'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'file', 'size', 'width', 'height', 'duration',
            'created_at', 'updated_at'
        ]
    
    def get_folder_path(self, obj):
        """Get full folder path"""
        if not obj.folder:
            return "/"
        
        path_parts = []
        current_folder = obj.folder
        
        while current_folder:
            path_parts.append(current_folder.name)
            current_folder = current_folder.parent
        
        path_parts.reverse()
        return "/" + "/".join(path_parts)
    
    def get_file_url(self, obj):
        """Get file URL with proper access control"""
        if obj.file:
            try:
                # For Supabase storage, generate signed URL
                if hasattr(default_storage, 'generate_signed_url'):
                    return default_storage.generate_signed_url(obj.file.name, expires_in=3600)
                else:
                    return obj.file.url
            except Exception:
                return None
        return None
    
    def get_thumbnail_url(self, obj):
        """Get thumbnail URL"""
        if obj.thumbnail:
            try:
                if hasattr(default_storage, 'generate_signed_url'):
                    return default_storage.generate_signed_url(obj.thumbnail.name, expires_in=3600)
                else:
                    return obj.thumbnail.url
            except Exception:
                return None
        return None
    
    def get_download_url(self, obj):
        """Get download URL with proper headers"""
        if obj.file:
            try:
                # Generate signed URL for download
                if hasattr(default_storage, 'generate_signed_url'):
                    return default_storage.generate_signed_url(
                        obj.file.name, 
                        expires_in=3600,
                        download=True
                    )
                else:
                    return obj.file.url
            except Exception:
                return None
        return None
    
    def get_metadata(self, obj):
        """Get additional metadata"""
        metadata = {}
        
        # Basic file info
        if obj.file:
            metadata['original_name'] = os.path.basename(obj.file.name)
            metadata['extension'] = os.path.splitext(obj.file.name)[1].lower()
            metadata['mime_type'] = mimetypes.guess_type(obj.file.name)[0]
        
        # Media-specific metadata
        if obj.media_type == 'image' and obj.width and obj.height:
            metadata['dimensions'] = f"{obj.width}x{obj.height}"
            metadata['aspect_ratio'] = round(obj.width / obj.height, 2) if obj.height > 0 else None
        
        if obj.media_type in ['video', 'audio'] and obj.duration:
            metadata['duration_formatted'] = f"{obj.duration // 60}:{obj.duration % 60:02d}"
        
        # Size formatting
        if obj.size:
            if obj.size < 1024:
                metadata['size_formatted'] = f"{obj.size} B"
            elif obj.size < 1024 * 1024:
                metadata['size_formatted'] = f"{obj.size / 1024:.1f} KB"
            else:
                metadata['size_formatted'] = f"{obj.size / (1024 * 1024):.1f} MB"
        
        return metadata