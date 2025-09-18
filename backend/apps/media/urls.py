"""
Enhanced Media app URL configuration with bulk upload and enhanced features
"""

from django.urls import path
from . import views
from .enhanced_views import (
    EnhancedMediaUploadView,
    BulkMediaUploadView,
    UserMediaStatsView
)

urlpatterns = [
    # Enhanced upload endpoints
    path('upload/', EnhancedMediaUploadView.as_view(), name='media-upload-enhanced'),
    path('upload/bulk/', BulkMediaUploadView.as_view(), name='media-bulk-upload'),
    
    # Original upload endpoint (for backward compatibility)
    path('upload/original/', views.MediaUploadView.as_view(), name='media-upload-original'),
    
    # Media management
    path('library/', views.MediaLibraryView.as_view(), name='media-library'),
    path('<uuid:pk>/', views.MediaFileDetailView.as_view(), name='media-detail'),
    path('<uuid:file_id>/tags/', views.update_media_tags, name='media-tags'),
    path('bulk-delete/', views.bulk_delete_media, name='media-bulk-delete'),
    
    # Enhanced analytics and statistics
    path('stats/', UserMediaStatsView.as_view(), name='media-stats'),
    path('storage/', views.storage_info, name='media-storage'),
    
    # Folder management
    path('folders/', views.MediaFolderListCreateView.as_view(), name='media-folders'),
    path('folders/<uuid:pk>/', views.MediaFolderDetailView.as_view(), name='media-folder-detail'),
]
