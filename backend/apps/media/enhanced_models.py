"""
Enhanced media models with user-specific organization and folders
"""

import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.contrib.postgres.fields import ArrayField

from apps.core.upload_paths import user_media_upload_path, user_thumbnail_upload_path


class MediaFolder(models.Model):
    """Folder for organizing user media files"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='media_folders'
    )
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
        db_table = 'media_folders'
        unique_together = ['user', 'parent', 'name']
        ordering = ['name']
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
    
    def get_all_files(self):
        """Get all files in this folder and subfolders"""
        from .models import MediaFile
        
        files = MediaFile.objects.filter(folder=self)
        
        # Add files from subfolders
        for subfolder in self.subfolders.all():
            files = files.union(subfolder.get_all_files())
        
        return files
    
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


class MediaFile(models.Model):
    """Enhanced media file model with user organization"""
    
    MEDIA_TYPES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('document', 'Document'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='media_files'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    alt_text = models.CharField(max_length=500, blank=True, help_text="Alt text for accessibility")
    
    # File fields
    file = models.FileField(
        upload_to=user_media_upload_path,
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg',
                    'mp4', 'mov', 'webm', 'avi',
                    'mp3', 'wav', 'ogg', 'flac',
                    'pdf', 'doc', 'docx', 'txt'
                ]
            )
        ]
    )
    thumbnail = models.ImageField(
        upload_to=user_thumbnail_upload_path,
        blank=True,
        null=True
    )
    
    # Metadata fields
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPES)
    size = models.PositiveIntegerField(help_text="File size in bytes")
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    duration = models.PositiveIntegerField(null=True, blank=True, help_text="Duration in seconds")
    
    # Organization fields
    folder = models.ForeignKey(
        MediaFolder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='files'
    )
    tags = ArrayField(
        models.CharField(max_length=50),
        size=10,
        default=list,
        blank=True,
        help_text="Tags for organizing and searching files"
    )
    
    # Usage tracking
    download_count = models.PositiveIntegerField(default=0)
    last_accessed = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'media_files'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'media_type']),
            models.Index(fields=['user', 'folder']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['media_type', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username}/{self.name}"
    
    @property
    def file_extension(self):
        """Get file extension"""
        import os
        return os.path.splitext(self.file.name)[1].lower()
    
    @property
    def file_size_formatted(self):
        """Get formatted file size"""
        if self.size < 1024:
            return f"{self.size} B"
        elif self.size < 1024 * 1024:
            return f"{self.size / 1024:.1f} KB"
        else:
            return f"{self.size / (1024 * 1024):.1f} MB"
    
    @property
    def duration_formatted(self):
        """Get formatted duration"""
        if self.duration:
            minutes = self.duration // 60
            seconds = self.duration % 60
            return f"{minutes}:{seconds:02d}"
        return None
    
    def get_folder_path(self):
        """Get full folder path"""
        if self.folder:
            return self.folder.get_full_path()
        return ""
    
    def increment_download_count(self):
        """Increment download counter"""
        from django.utils import timezone
        self.download_count += 1
        self.last_accessed = timezone.now()
        self.save(update_fields=['download_count', 'last_accessed'])
    
    def clean(self):
        """Validate media file data"""
        from django.core.exceptions import ValidationError
        
        # Check folder belongs to same user
        if self.folder and self.folder.user != self.user:
            raise ValidationError("Folder must belong to the same user")
        
        # Validate tags
        if self.tags:
            if len(self.tags) > 10:
                raise ValidationError("Maximum 10 tags allowed")
            
            for tag in self.tags:
                if len(tag) > 50:
                    raise ValidationError("Tag length cannot exceed 50 characters")


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
        db_table = 'media_upload_batches'
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


class MediaFileVersion(models.Model):
    """Track media file versions for updates"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    media_file = models.ForeignKey(
        MediaFile,
        on_delete=models.CASCADE,
        related_name='versions'
    )
    version_number = models.PositiveIntegerField()
    file = models.FileField(upload_to=user_media_upload_path)
    size = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_file_versions'
    )
    
    class Meta:
        db_table = 'media_file_versions'
        unique_together = ['media_file', 'version_number']
        ordering = ['-version_number']
        indexes = [
            models.Index(fields=['media_file', '-version_number']),
        ]
    
    def __str__(self):
        return f"{self.media_file.name} v{self.version_number}"