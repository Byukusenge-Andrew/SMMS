"""
Enhanced URL patterns for media upload functionality
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .enhanced_views import (
    EnhancedMediaUploadView,
    BulkMediaUploadView,
    UserMediaStatsView
)
from .views import (
    MediaLibraryView,
    MediaDetailView,
    MediaDeleteView,
    MediaFolderListCreateView,
    MediaFolderDetailView
)

# Create router for viewsets
router = DefaultRouter()

# URL patterns
urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
    
    # Enhanced upload endpoints
    path('upload/', EnhancedMediaUploadView.as_view(), name='media-upload'),
    path('upload/bulk/', BulkMediaUploadView.as_view(), name='media-bulk-upload'),
    
    # Media management
    path('library/', MediaLibraryView.as_view(), name='media-library'),
    path('<uuid:pk>/', MediaDetailView.as_view(), name='media-detail'),
    path('<uuid:pk>/delete/', MediaDeleteView.as_view(), name='media-delete'),
    
    # Folder management
    path('folders/', MediaFolderListCreateView.as_view(), name='media-folders'),
    path('folders/<uuid:pk>/', MediaFolderDetailView.as_view(), name='media-folder-detail'),
    
    # Statistics and analytics
    path('stats/', UserMediaStatsView.as_view(), name='media-stats'),
]

app_name = 'media'