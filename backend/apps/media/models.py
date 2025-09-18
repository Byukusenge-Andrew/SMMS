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
    
    # Organization
    folder = models.ForeignKey(
        'MediaFolder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='files'
    )
    
    # Tags for organization (enhanced)
    tags = models.JSONField(default=list, blank=True)
    alt_text = models.CharField(max_length=500, blank=True, help_text="Alt text for accessibility")
    description = models.TextField(blank=True)
    
    # Usage tracking
    download_count = models.PositiveIntegerField(default=0)
    last_accessed = models.DateTimeField(null=True, blank=True)
    
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
    
    @property
    def file_extension(self):
        """Get file extension"""
        import os
        return os.path.splitext(self.file.name)[1].lower()
    
    @property
    def duration_formatted(self):
        """Get formatted duration"""
        if self.duration:
            minutes = int(self.duration // 60)
            seconds = int(self.duration % 60)
            return f"{minutes}:{seconds:02d}"
        return None
    
    def increment_download_count(self):
        """Increment download counter"""
        from django.utils import timezone
        self.download_count += 1
        self.last_accessed = timezone.now()
        self.save(update_fields=['download_count', 'last_accessed'])
    
    def delete(self, *args, **kwargs):
        """Delete file from storage when model is deleted"""
        if self.file:
            self.file.delete(save=False)
        if self.thumbnail:
            self.thumbnail.delete(save=False)
        super().delete(*args, **kwargs)


class MediaFolder(models.Model):
    """Enhanced model for organizing media files into folders"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='media_folders')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='subfolders'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        unique_together = ['user', 'name', 'parent']
        indexes = [
            models.Index(fields=['user', 'parent']),
            models.Index(fields=['user', 'name']),
        ]
    
    def __str__(self):
        return f"{self.user.username}/{self.get_full_path()}"
    
    def get_full_path(self):
        """Get full folder path"""
        path_parts = []
        current_folder = self
        
        while current_folder:
            path_parts.append(current_folder.name)
            current_folder = current_folder.parent
        
        path_parts.reverse()
        return "/".join(path_parts)
    
    def clean(self):
        """Validate folder data"""
        from django.core.exceptions import ValidationError
        
        # Check for circular references
        if self.parent:
            current = self.parent
            while current:
                if current == self:
                    raise ValidationError("Circular folder reference detected")
                current = current.parent
        
        # Check parent belongs to same user
        if self.parent and self.parent.user != self.user:
            raise ValidationError("Parent folder must belong to the same user")


class MediaUploadBatch(models.Model):
    """Track bulk upload batches"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='upload_batches'
    )
    name = models.CharField(max_length=255, blank=True)
    total_files = models.PositiveIntegerField()
    successful_uploads = models.PositiveIntegerField(default=0)
    failed_uploads = models.PositiveIntegerField(default=0)
    total_size = models.PositiveBigIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"Batch {self.id} - {self.user.username} ({self.status})"
    
    @property
    def completion_percentage(self):
        """Get completion percentage"""
        if self.total_files == 0:
            return 0
        processed = self.successful_uploads + self.failed_uploads
        return round((processed / self.total_files) * 100, 2)
    
    @property
    def success_rate(self):
        """Get success rate percentage"""
        processed = self.successful_uploads + self.failed_uploads
        if processed == 0:
            return 0
        return round((self.successful_uploads / processed) * 100, 2)


class MediaFileFolder(models.Model):
    """Many-to-many relationship between media files and folders"""
    
    media_file = models.ForeignKey(MediaFile, on_delete=models.CASCADE)
    folder = models.ForeignKey(MediaFolder, on_delete=models.CASCADE)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['media_file', 'folder']
