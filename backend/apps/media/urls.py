"""
Media app URL configuration
"""

from django.urls import path
from . import views

urlpatterns = [
    # Media file endpoints
    path('upload/', views.MediaUploadView.as_view(), name='media-upload'),
    path('library/', views.MediaLibraryView.as_view(), name='media-library'),
    path('<uuid:pk>/', views.MediaFileDetailView.as_view(), name='media-detail'),
    path('<uuid:file_id>/tags/', views.update_media_tags, name='media-tags'),
    path('bulk-delete/', views.bulk_delete_media, name='media-bulk-delete'),
    path('storage/', views.storage_info, name='media-storage'),
    
    # Folder endpoints
    path('folders/', views.MediaFolderListCreateView.as_view(), name='media-folders'),
    path('folders/<uuid:pk>/', views.MediaFolderDetailView.as_view(), name='media-folder-detail'),
]
