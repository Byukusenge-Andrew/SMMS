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
    Format: {user_uuid}/media/{filename}
    
    This ensures the first folder is the user UUID from their profile, 
    which provides better data organization and security.
    """
    # Get file extension
    name, ext = os.path.splitext(filename)
    
    # Generate unique filename to prevent conflicts
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    unique_filename = f"{name}_{timestamp}_{uuid.uuid4().hex[:8]}{ext}"
    
    # Get user UUID from profile, fallback to user ID if profile doesn't exist
    try:
        user_uuid = str(instance.user.profile.id)
    except AttributeError:
        # Fallback to user ID if profile doesn't exist yet
        user_uuid = str(instance.user.id)
    
    # Return path: user_uuid/media/filename
    return f"{user_uuid}/media/{unique_filename}"


def user_thumbnail_upload_path(instance, filename):
    """
    Generate upload path for user thumbnail files.
    Format: {user_uuid}/thumbnails/{filename}
    """
    # Get file extension
    name, ext = os.path.splitext(filename)
    
    # Generate unique filename
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    unique_filename = f"thumb_{name}_{timestamp}_{uuid.uuid4().hex[:8]}{ext}"
    
    # Get user UUID from profile, fallback to user ID if profile doesn't exist
    try:
        user_uuid = str(instance.user.profile.id)
    except AttributeError:
        # Fallback to user ID if profile doesn't exist yet
        user_uuid = str(instance.user.id)
    
    # Return path: user_uuid/thumbnails/filename
    return f"{user_uuid}/thumbnails/{unique_filename}"


def user_avatar_upload_path(instance, filename):
    """
    Generate upload path for user avatar files.
    Format: {user_uuid}/avatars/{filename}
    """
    # Get file extension
    _, ext = os.path.splitext(filename)
    
    # Use a consistent filename for avatars (one per user)
    avatar_filename = f"avatar{ext}"
    
    # Get user UUID from profile (for avatar uploads, profile should exist)
    try:
        user_uuid = str(instance.id)  # instance is UserProfile for avatars
    except AttributeError:
        # Fallback if something goes wrong
        user_uuid = str(instance.user.id if hasattr(instance, 'user') else 'unknown')
    
    # Return path: user_uuid/avatars/avatar.ext
    return f"{user_uuid}/avatars/{avatar_filename}"


def user_post_media_upload_path(instance, filename):
    """
    Generate upload path for post media files.
    Format: {user_uuid}/posts/{post_id}/{filename}
    """
    # Get file extension
    name, ext = os.path.splitext(filename)
    
    # Generate unique filename
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    unique_filename = f"{name}_{timestamp}_{uuid.uuid4().hex[:8]}{ext}"
    
    # Get user UUID from profile, fallback to user ID if profile doesn't exist
    try:
        user_uuid = str(instance.user.profile.id)
    except AttributeError:
        # Fallback to user ID if profile doesn't exist yet
        user_uuid = str(instance.user.id)
    
    # Get post ID from the related post
    post_id = getattr(instance, 'post_id', 'unknown')
    
    # Return path: user_uuid/posts/post_id/filename
    return f"{user_uuid}/posts/{post_id}/{unique_filename}"