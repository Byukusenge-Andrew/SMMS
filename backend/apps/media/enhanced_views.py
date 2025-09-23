"""
Enhanced media upload views with bulk upload and user-specific organization
"""

import logging
import mimetypes
from typing import List, Dict, Any
from django.db import transaction
from django.db.models import Sum, Count, Q
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.views import APIView

from .models import MediaFile, MediaFolder, MediaUploadBatch
from .serializers import (
    MediaFileSerializer, 
    MediaFileUploadSerializer, 
    MediaFolderSerializer
)
from .enhanced_serializers import (
    BulkMediaUploadSerializer,
    MediaFileUpdateSerializer
)
from .utils import generate_thumbnail, extract_media_metadata
from .enhanced_utils import validate_file_type
from apps.core.permissions import IsOwnerOnly, DataIsolationMixin, ClientDataValidator, ensure_data_isolation
from apps.core.uuid_transition_helpers import get_user_storage_path

logger = logging.getLogger(__name__)


class EnhancedMediaUploadView(DataIsolationMixin, APIView):
    """Enhanced media file upload with metadata extraction and validation"""
    
    permission_classes = [permissions.IsAuthenticated, IsOwnerOnly]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request, *args, **kwargs):
        """Upload single media file with enhanced validation"""
        try:
            # Validate file presence
            if 'file' not in request.FILES:
                return Response({
                    'error': 'No file provided',
                    'code': 'FILE_REQUIRED'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            file = request.FILES['file']
            
            # Validate file type and size
            validation_result = self._validate_upload(file, request.user)
            if not validation_result['valid']:
                return Response({
                    'error': validation_result['error'],
                    'code': validation_result.get('code', 'VALIDATION_ERROR')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Prepare data for serializer
            upload_data = {
                'file': file,
                'name': request.data.get('name', file.name),
                'tags': request.data.get('tags', []),
                'folder': request.data.get('folder'),
                'description': request.data.get('description', ''),
                'alt_text': request.data.get('alt_text', ''),
            }
            
            # Process upload
            result = self._process_single_upload(upload_data, request.user)
            
            if result['success']:
                return Response({
                    'file': result['data'],
                    'message': 'File uploaded successfully',
                    'storage_info': self._get_user_storage_info(request.user)
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'error': result['error'],
                    'code': result.get('code', 'UPLOAD_ERROR')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"Error in enhanced upload: {str(e)}")
            return Response({
                'error': 'Upload failed',
                'message': str(e),
                'code': 'INTERNAL_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _validate_upload(self, file, user) -> Dict[str, Any]:
        """Validate file upload"""
        # Check file size (50MB limit)
        max_size = 50 * 1024 * 1024  # 50MB
        if file.size > max_size:
            return {
                'valid': False,
                'error': f'File too large. Maximum size is {max_size // (1024*1024)}MB',
                'code': 'FILE_TOO_LARGE'
            }
        
        # Check file type
        allowed_types = [
            'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp',
            'video/mp4', 'video/mov', 'video/webm', 'video/mkv', 'video/3gpp',
            'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/aac', 'audio/ogg', 'audio/m4a', 'audio/opus'
        ]
        
        if file.content_type not in allowed_types:
            return {
                'valid': False,
                'error': f'File type {file.content_type} not allowed',
                'code': 'INVALID_FILE_TYPE'
            }
        
        # Check user storage quota
        storage_info = self._get_user_storage_info(user)
        if storage_info['used_storage'] + file.size > storage_info['total_storage']:
            return {
                'valid': False,
                'error': 'Storage quota exceeded',
                'code': 'QUOTA_EXCEEDED'
            }
        
        return {'valid': True}
    
    def _process_single_upload(self, upload_data, user) -> Dict[str, Any]:
        """Process single file upload"""
        try:
            with transaction.atomic():
                # Create serializer
                serializer = MediaFileUploadSerializer(
                    data=upload_data,
                    context={'request': type('obj', (object,), {'user': user})()}
                )
                
                if not serializer.is_valid():
                    return {
                        'success': False,
                        'error': 'Invalid upload data',
                        'details': serializer.errors,
                        'code': 'VALIDATION_ERROR'
                    }
                
                # Save media file
                media_file = serializer.save(user=user)
                
                # Validate user access
                ClientDataValidator.validate_user_access(user, media_file)
                
                # Extract metadata asynchronously
                try:
                    metadata = extract_media_metadata(media_file.file)
                    if metadata:
                        media_file.width = metadata.get('width')
                        media_file.height = metadata.get('height')
                        media_file.duration = metadata.get('duration')
                        media_file.save()
                except Exception as e:
                    logger.warning(f"Failed to extract metadata for {media_file.name}: {str(e)}")
                
                # Generate thumbnail
                try:
                    generate_thumbnail(media_file)
                except Exception as e:
                    logger.warning(f"Failed to generate thumbnail for {media_file.name}: {str(e)}")
                
                # Return serialized data
                response_serializer = MediaFileSerializer(media_file)
                return {
                    'success': True,
                    'data': response_serializer.data
                }
                
        except Exception as e:
            logger.error(f"Error processing upload: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'code': 'PROCESSING_ERROR'
            }
    
    def _get_user_storage_info(self, user) -> Dict[str, Any]:
        """Get user storage information"""
        user_files = MediaFile.objects.filter(user=user)
        total_size = user_files.aggregate(total=Sum('size'))['total'] or 0
        file_count = user_files.count()
        
        # Storage limits based on subscription
        storage_limit = 5 * 1024 * 1024 * 1024  # 5GB default
        if hasattr(user, 'profile') and user.profile and user.profile.subscription_tier:
            # Get storage limit from subscription tier
            tier = user.profile.subscription_tier
            if hasattr(tier, 'storage_limit_gb'):
                storage_limit = tier.storage_limit_gb * 1024 * 1024 * 1024
        
        return {
            'used_storage': total_size,
            'total_storage': storage_limit,
            'file_count': file_count,
            'storage_percentage': round((total_size / storage_limit) * 100, 2) if storage_limit > 0 else 0
        }


class BulkMediaUploadView(DataIsolationMixin, APIView):
    """Bulk media file upload with progress tracking"""
    
    permission_classes = [permissions.IsAuthenticated, IsOwnerOnly]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request, *args, **kwargs):
        """Upload multiple files with batch processing"""
        try:
            # Get all uploaded files
            files = request.FILES.getlist('files')
            if not files:
                return Response({
                    'error': 'No files provided',
                    'code': 'FILES_REQUIRED'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate file count (max 20 files per bulk upload)
            if len(files) > 20:
                return Response({
                    'error': 'Too many files. Maximum 20 files per bulk upload',
                    'code': 'TOO_MANY_FILES'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get common metadata
            folder_id = request.data.get('folder')
            tags = request.data.getlist('tags') or []
            
            # Process bulk upload
            results = self._process_bulk_upload(files, request.user, folder_id, tags)
            
            return Response({
                'results': results,
                'summary': {
                    'total_files': len(files),
                    'successful_uploads': len([r for r in results if r['success']]),
                    'failed_uploads': len([r for r in results if not r['success']]),
                },
                'storage_info': self._get_user_storage_info(request.user)
            }, status=status.HTTP_207_MULTI_STATUS)
            
        except Exception as e:
            logger.error(f"Error in bulk upload: {str(e)}")
            return Response({
                'error': 'Bulk upload failed',
                'message': str(e),
                'code': 'BULK_UPLOAD_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _process_bulk_upload(self, files, user, folder_id=None, tags=None) -> List[Dict[str, Any]]:
        """Process multiple file uploads"""
        results = []
        
        for i, file in enumerate(files):
            try:
                print(file)
                # Validate individual file
                upload_view = EnhancedMediaUploadView()
                validation_result = upload_view._validate_upload(file, user)
                
                if not validation_result['valid']:
                    results.append({
                        'index': i,
                        'filename': file.name,
                        'success': False,
                        'error': validation_result['error'],
                        'code': validation_result.get('code')
                    })
                    continue
                
                # Prepare upload data
                upload_data = {
                    'file': file,
                    'name': file.name,
                    'tags': tags or [],
                    'folder': folder_id,
                }
                
                # Process upload
                result = upload_view._process_single_upload(upload_data, user)
                
                if result['success']:
                    results.append({
                        'index': i,
                        'filename': file.name,
                        'success': True,
                        'file': result['data']
                    })
                else:
                    results.append({
                        'index': i,
                        'filename': file.name,
                        'success': False,
                        'error': result['error'],
                        'code': result.get('code')
                    })
                    
            except Exception as e:
                logger.error(f"Error processing file {file.name}: {str(e)}")
                results.append({
                    'index': i,
                    'filename': file.name,
                    'success': False,
                    'error': str(e),
                    'code': 'PROCESSING_ERROR'
                })
        
        return results
    
    def _get_user_storage_info(self, user) -> Dict[str, Any]:
        """Get user storage information"""
        return EnhancedMediaUploadView()._get_user_storage_info(user)


class UserMediaStatsView(DataIsolationMixin, APIView):
    """Get detailed media statistics for the user"""
    
    permission_classes = [permissions.IsAuthenticated, IsOwnerOnly]
    
    def get(self, request, *args, **kwargs):
        """Get comprehensive media statistics"""
        try:
            user_files = MediaFile.objects.filter(user=request.user)
            
            # Basic stats
            total_files = user_files.count()
            total_size = user_files.aggregate(total=Sum('size'))['total'] or 0
            
            # Media type breakdown
            media_types = user_files.values('media_type').annotate(
                count=Count('id'),
                size=Sum('size')
            )
            
            # Monthly upload stats (last 12 months)
            from django.utils import timezone
            from datetime import timedelta
            import calendar
            
            twelve_months_ago = timezone.now() - timedelta(days=365)
            monthly_stats = []
            
            for i in range(12):
                month_start = twelve_months_ago + timedelta(days=30*i)
                month_end = month_start + timedelta(days=30)
                
                month_files = user_files.filter(
                    created_at__gte=month_start,
                    created_at__lt=month_end
                )
                
                monthly_stats.append({
                    'month': month_start.strftime('%Y-%m'),
                    'month_name': calendar.month_name[month_start.month],
                    'files_count': month_files.count(),
                    'total_size': month_files.aggregate(total=Sum('size'))['total'] or 0
                })
            
            # Storage info
            storage_info = EnhancedMediaUploadView()._get_user_storage_info(request.user)
            
            # Recent uploads (last 10)
            recent_files = user_files.order_by('-created_at')[:10]
            recent_serializer = MediaFileSerializer(recent_files, many=True)
            
            return Response({
                'total_files': total_files,
                'total_size': total_size,
                'storage_info': storage_info,
                'media_types': list(media_types),
                'monthly_stats': monthly_stats,
                'recent_uploads': recent_serializer.data,
                'upload_limits': {
                    'max_file_size': 50 * 1024 * 1024,  # 50MB
                    'max_bulk_files': 20,
                    'allowed_types': [
                        'image/jpeg', 'image/png', 'image/gif', 'image/webp',
                        'video/mp4', 'video/quicktime', 'video/webm',
                        'audio/mp3', 'audio/wav', 'audio/ogg'
                    ]
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting media stats: {str(e)}")
            return Response({
                'error': 'Failed to get media statistics',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)