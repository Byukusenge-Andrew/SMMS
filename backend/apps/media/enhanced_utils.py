"""
Enhanced media utility functions for processing and validation
"""

import os
import logging
import mimetypes
from typing import Dict, Any, Optional, Tuple
from PIL import Image, ImageOps
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings

logger = logging.getLogger(__name__)


def extract_media_metadata(file) -> Dict[str, Any]:
    """Extract metadata from media files"""
    metadata = {}
    
    try:
        # Get basic file info
        metadata['size'] = file.size
        metadata['name'] = file.name
        metadata['content_type'] = getattr(file, 'content_type', mimetypes.guess_type(file.name)[0])
        
        # Process based on content type
        content_type = metadata['content_type'] or ''
        
        if content_type.startswith('image/'):
            metadata.update(_extract_image_metadata(file))
        elif content_type.startswith('video/'):
            metadata.update(_extract_video_metadata(file))
        elif content_type.startswith('audio/'):
            metadata.update(_extract_audio_metadata(file))
        
    except Exception as e:
        logger.error(f"Error extracting metadata from {file.name}: {str(e)}")
    
    return metadata


def _extract_image_metadata(file) -> Dict[str, Any]:
    """Extract metadata from image files"""
    metadata = {}
    
    try:
        # Open image with PIL
        with Image.open(file) as img:
            metadata['width'] = img.width
            metadata['height'] = img.height
            metadata['format'] = img.format
            metadata['mode'] = img.mode
            
            # Get EXIF data if available
            if hasattr(img, '_getexif') and img._getexif():
                exif = img._getexif()
                if exif:
                    # Extract common EXIF tags
                    metadata['exif'] = {
                        'camera_make': exif.get(271),  # Make
                        'camera_model': exif.get(272),  # Model
                        'datetime': exif.get(306),  # DateTime
                        'orientation': exif.get(274),  # Orientation
                    }
            
            # Calculate aspect ratio
            if metadata['width'] and metadata['height']:
                metadata['aspect_ratio'] = round(metadata['width'] / metadata['height'], 2)
    
    except Exception as e:
        logger.warning(f"Error extracting image metadata: {str(e)}")
    
    return metadata


def _extract_video_metadata(file) -> Dict[str, Any]:
    """Extract metadata from video files"""
    metadata = {}
    
    try:
        # Try to use moviepy if available
        try:
            from moviepy.editor import VideoFileClip # type: ignore
            
            # Create temporary file
            temp_path = f"/tmp/{file.name}"
            with open(temp_path, 'wb') as temp_file:
                for chunk in file.chunks():
                    temp_file.write(chunk)
            
            # Extract metadata
            with VideoFileClip(temp_path) as clip:
                metadata['duration'] = int(clip.duration) if clip.duration else 0
                metadata['width'] = clip.w
                metadata['height'] = clip.h
                metadata['fps'] = clip.fps
            
            # Clean up
            os.remove(temp_path)
            
        except ImportError:
            logger.warning("moviepy not available for video metadata extraction")
    
    except Exception as e:
        logger.warning(f"Error extracting video metadata: {str(e)}")
    
    return metadata


def _extract_audio_metadata(file) -> Dict[str, Any]:
    """Extract metadata from audio files"""
    metadata = {}
    
    try:
        # Try to use mutagen if available
        try:
            from mutagen import File as MutagenFile # type: ignore
            
            # Create temporary file
            temp_path = f"/tmp/{file.name}"
            with open(temp_path, 'wb') as temp_file:
                for chunk in file.chunks():
                    temp_file.write(chunk)
            
            # Extract metadata
            audio_file = MutagenFile(temp_path)
            if audio_file:
                metadata['duration'] = int(audio_file.info.length) if hasattr(audio_file.info, 'length') else 0
                metadata['bitrate'] = getattr(audio_file.info, 'bitrate', None)
                metadata['sample_rate'] = getattr(audio_file.info, 'sample_rate', None)
                
                # Extract tags
                if audio_file.tags:
                    metadata['tags'] = {
                        'title': audio_file.tags.get('TIT2', [None])[0] if 'TIT2' in audio_file.tags else None,
                        'artist': audio_file.tags.get('TPE1', [None])[0] if 'TPE1' in audio_file.tags else None,
                        'album': audio_file.tags.get('TALB', [None])[0] if 'TALB' in audio_file.tags else None,
                    }
            
            # Clean up
            os.remove(temp_path)
            
        except ImportError:
            logger.warning("mutagen not available for audio metadata extraction")
    
    except Exception as e:
        logger.warning(f"Error extracting audio metadata: {str(e)}")
    
    return metadata


def generate_thumbnail(media_file, size: Tuple[int, int] = (300, 300)) -> bool:
    """Generate thumbnail for media file"""
    
    try:
        if media_file.media_type == 'image':
            return _generate_image_thumbnail(media_file, size)
        elif media_file.media_type == 'video':
            return _generate_video_thumbnail(media_file, size)
        else:
            return False
    
    except Exception as e:
        logger.error(f"Error generating thumbnail for {media_file.name}: {str(e)}")
        return False


def _generate_image_thumbnail(media_file, size: Tuple[int, int]) -> bool:
    """Generate thumbnail for image file"""
    
    try:
        # Open the image
        with Image.open(media_file.file) as img:
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # Create thumbnail
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Save thumbnail
            from io import BytesIO
            thumb_io = BytesIO()
            img.save(thumb_io, format='JPEG', quality=85, optimize=True)
            thumb_io.seek(0)
            
            # Generate thumbnail filename
            base_name = os.path.splitext(media_file.file.name)[0]
            thumb_name = f"{base_name}_thumb.jpg"
            
            # Save thumbnail file
            media_file.thumbnail.save(
                thumb_name,
                ContentFile(thumb_io.read()),
                save=False
            )
            
            return True
    
    except Exception as e:
        logger.warning(f"Error generating image thumbnail: {str(e)}")
        return False


def _generate_video_thumbnail(media_file, size: Tuple[int, int]) -> bool:
    """Generate thumbnail for video file"""
    
    try:
        # Try to use moviepy if available
        try:
            from moviepy.editor import VideoFileClip # type: ignore
            
            # Create temporary file
            temp_path = f"/tmp/{media_file.file.name}"
            with open(temp_path, 'wb') as temp_file:
                for chunk in media_file.file.chunks():
                    temp_file.write(chunk)
            
            # Extract frame at 1 second (or 10% of duration)
            with VideoFileClip(temp_path) as clip:
                frame_time = min(1.0, clip.duration * 0.1) if clip.duration else 1.0
                frame = clip.get_frame(frame_time)
                
                # Convert to PIL Image
                img = Image.fromarray(frame)
                
                # Create thumbnail
                img.thumbnail(size, Image.Resampling.LANCZOS)
                
                # Save thumbnail
                from io import BytesIO
                thumb_io = BytesIO()
                img.save(thumb_io, format='JPEG', quality=85, optimize=True)
                thumb_io.seek(0)
                
                # Generate thumbnail filename
                base_name = os.path.splitext(media_file.file.name)[0]
                thumb_name = f"{base_name}_thumb.jpg"
                
                # Save thumbnail file
                media_file.thumbnail.save(
                    thumb_name,
                    ContentFile(thumb_io.read()),
                    save=False
                )
            
            # Clean up
            os.remove(temp_path)
            return True
            
        except ImportError:
            logger.warning("moviepy not available for video thumbnail generation")
            return False
    
    except Exception as e:
        logger.warning(f"Error generating video thumbnail: {str(e)}")
        return False


def validate_file_type(file) -> Dict[str, Any]:
    """Validate file type and return detailed information"""
    
    result = {
        'valid': False,
        'media_type': None,
        'content_type': None,
        'extension': None,
        'errors': []
    }
    
    try:
        # Get file info
        content_type = getattr(file, 'content_type', None)
        if not content_type:
            content_type = mimetypes.guess_type(file.name)[0]
        
        extension = os.path.splitext(file.name)[1].lower()
        
        result['content_type'] = content_type
        result['extension'] = extension
        
        # Define allowed types
        allowed_types = {
            'image': [
                'image/jpeg', 'image/png', 'image/gif', 
                'image/webp', 'image/svg+xml'
            ],
            'video': [
                'video/mp4', 'video/quicktime', 'video/webm', 
                'video/avi', 'video/x-msvideo'
            ],
            'audio': [
                'audio/mp3', 'audio/mpeg', 'audio/wav', 
                'audio/ogg', 'audio/flac'
            ],
            'document': [
                'application/pdf', 'text/plain',
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            ]
        }
        
        # Check if content type is allowed
        media_type = None
        for mtype, types in allowed_types.items():
            if content_type in types:
                media_type = mtype
                break
        
        if not media_type:
            result['errors'].append(f"File type {content_type} not allowed")
            return result
        
        result['media_type'] = media_type
        result['valid'] = True
        
    except Exception as e:
        result['errors'].append(f"Error validating file: {str(e)}")
    
    return result


def optimize_image(image_file, max_size: Tuple[int, int] = (2048, 2048), quality: int = 85) -> Optional[ContentFile]:
    """Optimize image file for storage"""
    
    try:
        with Image.open(image_file) as img:
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                # For images with transparency, preserve it
                if img.mode == 'RGBA':
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background
                else:
                    img = img.convert('RGB')
            
            # Resize if too large
            if img.width > max_size[0] or img.height > max_size[1]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save optimized image
            from io import BytesIO
            output = BytesIO()
            img.save(output, format='JPEG', quality=quality, optimize=True)
            output.seek(0)
            
            return ContentFile(output.read())
    
    except Exception as e:
        logger.warning(f"Error optimizing image: {str(e)}")
        return None


def get_file_hash(file) -> str:
    """Generate SHA-256 hash of file content"""
    import hashlib
    
    hasher = hashlib.sha256()
    
    try:
        for chunk in file.chunks():
            hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        logger.error(f"Error generating file hash: {str(e)}")
        return ""


def clean_filename(filename: str) -> str:
    """Clean filename for safe storage"""
    import re
    
    # Remove or replace unsafe characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove multiple consecutive spaces/underscores
    filename = re.sub(r'[_\s]+', '_', filename)
    
    # Limit length
    name, ext = os.path.splitext(filename)
    if len(name) > 100:
        name = name[:100]
    
    return f"{name}{ext}".strip('_')


def get_storage_stats(user) -> Dict[str, Any]:
    """Get detailed storage statistics for user"""
    from .models import MediaFile
    from django.db.models import Sum, Count, Avg
    
    try:
        user_files = MediaFile.objects.filter(user=user)
        
        # Basic stats
        stats = {
            'total_files': user_files.count(),
            'total_size': user_files.aggregate(total=Sum('size'))['total'] or 0,
            'average_size': user_files.aggregate(avg=Avg('size'))['avg'] or 0,
        }
        
        # By media type
        type_stats = user_files.values('media_type').annotate(
            count=Count('id'),
            total_size=Sum('size')
        )
        stats['by_type'] = {item['media_type']: item for item in type_stats}
        
        # By month (last 12 months)
        from django.utils import timezone
        from datetime import timedelta
        
        twelve_months_ago = timezone.now() - timedelta(days=365)
        monthly_files = user_files.filter(created_at__gte=twelve_months_ago)
        
        # Group by month
        monthly_stats = []
        for i in range(12):
            month_start = twelve_months_ago + timedelta(days=30*i)
            month_end = month_start + timedelta(days=30)
            
            month_files = monthly_files.filter(
                created_at__gte=month_start,
                created_at__lt=month_end
            )
            
            monthly_stats.append({
                'month': month_start.strftime('%Y-%m'),
                'files': month_files.count(),
                'size': month_files.aggregate(total=Sum('size'))['total'] or 0
            })
        
        stats['monthly'] = monthly_stats
        
        return stats
    
    except Exception as e:
        logger.error(f"Error getting storage stats: {str(e)}")
        return {}