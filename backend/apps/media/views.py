"""
Media API views for handling file uploads and management
"""

import logging
from django.db.models import Sum, Count, Q
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import MediaFile, MediaFolder, MediaUploadBatch
from .serializers import MediaFileSerializer, MediaFileUploadSerializer, MediaFolderSerializer
from .utils import generate_thumbnail, extract_media_metadata
from apps.core.permissions import IsOwnerOnly, DataIsolationMixin, ClientDataValidator, ensure_data_isolation

logger = logging.getLogger(__name__)


class MediaUploadView(DataIsolationMixin, generics.CreateAPIView):
    """Handle media file uploads"""
    
    serializer_class = MediaFileUploadSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOnly]
    parser_classes = [MultiPartParser, FormParser]
    
    def create(self, request, *args, **kwargs):
        """Upload media file with metadata extraction"""
        try:
            serializer = self.get_serializer(data=request.data)
            
            if serializer.is_valid():
                # Ensure user is set correctly (DataIsolationMixin handles this)
                media_file = serializer.save(user=request.user)
                
                # Validate user access
                ClientDataValidator.validate_user_access(request.user, media_file)
                
                # Extract additional metadata (dimensions, duration, etc.)
                try:
                    metadata = extract_media_metadata(media_file.file)
                    if metadata:
                        media_file.width = metadata.get('width')
                        media_file.height = metadata.get('height')
                        media_file.duration = metadata.get('duration')
                        media_file.save()
                except Exception as e:
                    logger.warning(f"Failed to extract metadata for {media_file.name}: {str(e)}")
                
                # Generate thumbnail for images and videos
                try:
                    generate_thumbnail(media_file)
                except Exception as e:
                    logger.warning(f"Failed to generate thumbnail for {media_file.name}: {str(e)}")
                
                # Return response
                response_serializer = MediaFileSerializer(media_file)
                return Response({
                    'file': response_serializer.data,
                    'message': 'File uploaded successfully'
                }, status=status.HTTP_201_CREATED)
            
            return Response({
                'error': 'Invalid file data',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            return Response({
                'error': 'Failed to upload file',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MediaLibraryView(DataIsolationMixin, generics.ListAPIView):
    """List media files with filtering and pagination"""
    
    serializer_class = MediaFileSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOnly]
    queryset = MediaFile.objects.all()  # This will be filtered by DataIsolationMixin
    
    def get_queryset(self):
        """Filter media files by user and optional filters"""
        # DataIsolationMixin ensures base filtering by user
        queryset = super().get_queryset()
        
        # Apply additional filters from query parameters
        media_type = self.request.query_params.get('type')
        if media_type and media_type in ['image', 'video', 'audio']:
            queryset = queryset.filter(media_type=media_type)
        
        tag = self.request.query_params.get('tag')
        if tag:
            queryset = queryset.filter(tags__icontains=tag)
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(original_name__icontains=search) |
                Q(tags__icontains=search)
            )
        
        date_from = self.request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        
        date_to = self.request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)
        
        return queryset.order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        """Return paginated list of media files"""
        queryset = self.get_queryset()
        
        # Pagination
        page_size = int(request.query_params.get('page_size', 20))
        page = int(request.query_params.get('page', 1))
        
        total_count = queryset.count()
        total_pages = (total_count + page_size - 1) // page_size
        
        start = (page - 1) * page_size
        end = start + page_size
        
        paginated_queryset = queryset[start:end]
        serializer = self.get_serializer(paginated_queryset, many=True)
        
        return Response({
            'files': serializer.data,
            'total_count': total_count,
            'page': page,
            'total_pages': total_pages
        })


class MediaFileDetailView(DataIsolationMixin, generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a specific media file"""
    
    serializer_class = MediaFileSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOnly]
    queryset = MediaFile.objects.all()  # This will be filtered by DataIsolationMixin
    
    def get_queryset(self):
        # DataIsolationMixin will automatically filter by user
        return super().get_queryset()
    
    def perform_update(self, serializer):
        """Ensure user ownership is maintained on update"""
        instance = serializer.save()
        ClientDataValidator.validate_user_access(self.request.user, instance)
    
    def perform_destroy(self, instance):
        """Validate access before deletion"""
        ClientDataValidator.validate_user_access(self.request.user, instance)
        super().perform_destroy(instance)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
@ensure_data_isolation
def bulk_delete_media(request):
    """Bulk delete media files"""
    try:
        ids = request.data.get('ids', [])
        if not ids:
            return Response({
                'error': 'No file IDs provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user files and validate access
        user_files = MediaFile.objects.filter(user=request.user, id__in=ids)
        
        # Additional security check - ensure all files belong to user
        found_ids = set(str(f.id) for f in user_files)
        requested_ids = set(str(id) for id in ids)
        
        if found_ids != requested_ids:
            missing_ids = requested_ids - found_ids
            logger.warning(
                f"User {request.user.id} attempted to delete files they don't own: {missing_ids}"
            )
            return Response({
                'error': 'Access denied - some files do not belong to you'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Validate access to all files
        ClientDataValidator.bulk_validate_access(request.user, user_files)
        
        # Delete the files
        deleted_count = user_files.count()
        user_files.delete()
        
        return Response({
            'deleted_count': deleted_count,
            'message': f'Successfully deleted {deleted_count} files'
        })
        
    except Exception as e:
        logger.error(f"Error bulk deleting files: {str(e)}")
        return Response({
            'error': 'Failed to delete files',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def update_media_tags(request, file_id):
    """Update tags for a media file"""
    try:
        media_file = MediaFile.objects.get(
            user=request.user,
            id=file_id
        )
        
        tags = request.data.get('tags', [])
        media_file.tags = tags
        media_file.save()
        
        serializer = MediaFileSerializer(media_file)
        return Response(serializer.data)
        
    except MediaFile.DoesNotExist:
        return Response({
            'error': 'Media file not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        logger.error(f"Error updating tags: {str(e)}")
        return Response({
            'error': 'Failed to update tags',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def storage_info(request):
    """Get storage usage information for the user"""
    try:
        user_files = MediaFile.objects.filter(user=request.user)
        
        # Calculate storage usage
        total_size = user_files.aggregate(
            total=Sum('size')
        )['total'] or 0
        
        file_count = user_files.count()
        
        # Storage limits (can be configured per user/plan)
        storage_limit = 5 * 1024 * 1024 * 1024  # 5GB default limit
        storage_percentage = (total_size / storage_limit) * 100 if storage_limit > 0 else 0
        
        return Response({
            'used_storage': total_size,
            'total_storage': storage_limit,
            'file_count': file_count,
            'storage_percentage': round(storage_percentage, 2)
        })
        
    except Exception as e:
        logger.error(f"Error getting storage info: {str(e)}")
        return Response({
            'error': 'Failed to get storage information',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Media Folder Views
class MediaFolderListCreateView(DataIsolationMixin, generics.ListCreateAPIView):
    """List and create media folders"""
    
    serializer_class = MediaFolderSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOnly]
    queryset = MediaFolder.objects.all()  # This will be filtered by DataIsolationMixin


class MediaFolderDetailView(DataIsolationMixin, generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a media folder"""
    
    serializer_class = MediaFolderSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOnly]
    queryset = MediaFolder.objects.all()  # This will be filtered by DataIsolationMixin
