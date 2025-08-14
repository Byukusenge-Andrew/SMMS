"""
Utility functions for media processing
"""

import os
import time
import logging
from PIL import Image, ImageOps
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import io

logger = logging.getLogger(__name__)


def extract_media_metadata(file):
    """Extract metadata from media files"""
    try:
        # For images, extract dimensions using PIL
        if hasattr(file, 'content_type') and file.content_type.startswith('image/'):
            try:
                image = Image.open(file)
                return {
                    'width': image.width,
                    'height': image.height
                }
            except Exception as e:
                logger.warning(f"Failed to extract image dimensions: {str(e)}")
                return {}
        
        # For videos, you could use ffmpeg-python or similar
        # For now, return empty dict
        return {}
        
    except Exception as e:
        logger.error(f"Error extracting metadata: {str(e)}")
        return {}


def generate_thumbnail(media_file, size=(300, 300)):
    """Generate thumbnail for media files"""
    try:
        if media_file.media_type != 'image':
            # For now, only handle image thumbnails
            return
        
        # Open the original image
        image = Image.open(media_file.file)
        
        # Convert to RGB if necessary (for PNG with transparency, etc.)
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')
        
        # Create thumbnail while maintaining aspect ratio
        image.thumbnail(size, Image.Resampling.LANCZOS)
        
        # Save thumbnail to BytesIO
        thumbnail_io = io.BytesIO()
        image.save(thumbnail_io, format='JPEG', quality=85, optimize=True)
        thumbnail_io.seek(0)
        
        # Create ContentFile and save
        thumbnail_name = f"thumb_{media_file.id}.jpg"
        thumbnail_content = ContentFile(thumbnail_io.getvalue(), name=thumbnail_name)
        
        # Save thumbnail to media file
        media_file.thumbnail.save(thumbnail_name, thumbnail_content, save=True)
        
        logger.info(f"Generated thumbnail for {media_file.name}")
        
    except Exception as e:
        logger.error(f"Error generating thumbnail for {media_file.name}: {str(e)}")


def validate_file_type(file):
    """Validate uploaded file type"""
    allowed_types = {
        'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp',
        'video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/webm',
        'audio/mpeg', 'audio/wav', 'audio/ogg'
    }
    
    return hasattr(file, 'content_type') and file.content_type in allowed_types


def get_file_extension(filename):
    """Get file extension from filename"""
    return os.path.splitext(filename)[1].lower()


def generate_unique_filename(original_filename, user_id):
    """Generate unique filename to prevent conflicts"""
    name, ext = os.path.splitext(original_filename)
    timestamp = str(int(time.time()))
    return f"{name}_{user_id}_{timestamp}{ext}"
