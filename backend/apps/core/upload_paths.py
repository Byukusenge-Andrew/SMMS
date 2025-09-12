"""
Custom upload path functions for proper user-scoped file organization
that aligns with Supabase RLS policies
"""

import os
import uuid
from django.utils import timezone


def user_media_upload_path(instance, filename):
    """
    Generate upload path for user media files that aligns with RLS policies.
    Format: {user_id}/media/{filename}
    
    This ensures the first folder is the user ID, which matches the RLS policy:
    ((storage.foldername(name))[1] = auth.uid()::text)
    """
    # Get file extension
    name, ext = os.path.splitext(filename)
    
    # Generate unique filename to prevent conflicts
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    unique_filename = f"{name}_{timestamp}_{uuid.uuid4().hex[:8]}{ext}"
    
    # Return path: user_id/media/filename
    return f"{instance.user.id}/media/{unique_filename}"


def user_thumbnail_upload_path(instance, filename):
    """
    Generate upload path for user thumbnail files.
    Format: {user_id}/thumbnails/{filename}
    """
    # Get file extension
    name, ext = os.path.splitext(filename)
    
    # Generate unique filename
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    unique_filename = f"thumb_{name}_{timestamp}_{uuid.uuid4().hex[:8]}{ext}"
    
    # Return path: user_id/thumbnails/filename
    return f"{instance.user.id}/thumbnails/{unique_filename}"


def user_avatar_upload_path(instance, filename):
    """
    Generate upload path for user avatar files.
    Format: {user_id}/avatars/{filename}
    """
    # Get file extension
    _, ext = os.path.splitext(filename)
    
    # Use a consistent filename for avatars (one per user)
    avatar_filename = f"avatar{ext}"
    
    # Return path: user_id/avatars/avatar.ext
    return f"{instance.user.id}/avatars/{avatar_filename}"


def user_post_media_upload_path(instance, filename):
    """
    Generate upload path for post media files.
    Format: {user_id}/posts/{post_id}/{filename}
    """
    # Get file extension
    name, ext = os.path.splitext(filename)
    
    # Generate unique filename
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    unique_filename = f"{name}_{timestamp}_{uuid.uuid4().hex[:8]}{ext}"
    
    # Get post ID from the related post
    post_id = getattr(instance, 'post_id', 'unknown')
    
    # Return path: user_id/posts/post_id/filename
    return f"{instance.user.id}/posts/{post_id}/{unique_filename}"