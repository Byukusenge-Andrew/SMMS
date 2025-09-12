"""
Media models for SMMS - handles user uploaded media files
Integrates with Supabase storage for cloud storage
"""

import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from apps.core.upload_paths import user_media_upload_path, user_thumbnail_upload_path

def get_media_storage():
    """Get the supabase storage instance for media files"""
    from apps.core.storage import get_supabase_storage
    return get_supabase_storage()


class MediaFile(models.Model):
    """Model for user uploaded media files"""
    
    MEDIA_TYPES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('audio', 'Audio'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='media_files')
    
    # File information
    name = models.CharField(max_length=255)
    original_name = models.CharField(max_length=255)
    file = models.FileField(
        upload_to=user_media_upload_path,
        storage=get_media_storage(),
        validators=[
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 
                                 'mp4', 'mov', 'avi', 'wmv', 'flv', 'webm',
                                 'mp3', 'wav', 'ogg', 'aac']
            )
        ]
    )
    
    # File metadata
    size = models.BigIntegerField()  # File size in bytes
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPES)
    mime_type = models.CharField(max_length=100)
    
    # Dimensions for images/videos
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    
    # Duration for videos/audio in seconds
    duration = models.FloatField(null=True, blank=True)
    
    # Thumbnail for videos/images
    thumbnail = models.ImageField(
        upload_to=user_thumbnail_upload_path,
        storage=get_media_storage(),
        null=True,
        blank=True
    )
    
    # Tags for organization
    tags = models.JSONField(default=list, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'media_type']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.user.username}"
    
    @property
    def file_url(self):
        """Get the file URL"""
        if self.file:
            return self.file.url
        return None
    
    @property
    def thumbnail_url(self):
        """Get thumbnail URL"""
        if self.thumbnail:
            return self.thumbnail.url
        return None
    
    @property
    def size_mb(self):
        """Get file size in MB"""
        return round(self.size / (1024 * 1024), 2)
    
    def delete(self, *args, **kwargs):
        """Delete file from storage when model is deleted"""
        if self.file:
            self.file.delete(save=False)
        if self.thumbnail:
            self.thumbnail.delete(save=False)
        super().delete(*args, **kwargs)


class MediaFolder(models.Model):
    """Model for organizing media files into folders"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='media_folders')
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        unique_together = ['user', 'name', 'parent']
    
    def __str__(self):
        return f"{self.name} - {self.user.username}"


class MediaFileFolder(models.Model):
    """Many-to-many relationship between media files and folders"""
    
    media_file = models.ForeignKey(MediaFile, on_delete=models.CASCADE)
    folder = models.ForeignKey(MediaFolder, on_delete=models.CASCADE)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['media_file', 'folder']
