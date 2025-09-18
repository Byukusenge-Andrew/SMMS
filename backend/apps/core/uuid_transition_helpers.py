"""
Helper functions for managing the transition from digit ID to UUID-based file organization
"""

import logging
from typing import Optional
from django.contrib.auth.models import User
from apps.core.storage import SupabaseStorage

logger = logging.getLogger(__name__)


def get_user_storage_path(user: User, folder: str = "") -> str:
    """
    Get the storage path for a user, preferring UUID but falling back to digit ID
    
    Args:
        user: Django User instance
        folder: Optional subfolder name (e.g., 'media', 'avatars', 'thumbnails')
    
    Returns:
        Storage path string
    """
    try:
        # Try to get UUID from user profile
        if hasattr(user, 'profile') and user.profile:
            user_identifier = str(user.profile.id)
        else:
            # Fallback to digit ID
            user_identifier = str(user.id)
            logger.warning(f"User {user.id} has no profile, using digit ID for storage path")
    except Exception as e:
        # Final fallback to digit ID
        user_identifier = str(user.id)
        logger.error(f"Error getting UUID for user {user.id}: {e}, using digit ID")
    
    if folder:
        return f"{user_identifier}/{folder}"
    return user_identifier


def find_user_file_path(user: User, filename: str, subfolders: list = None) -> Optional[str]:
    """
    Find a file for a user, checking both UUID and digit ID paths
    
    Args:
        user: Django User instance
        filename: Name of the file to find
        subfolders: List of subfolders to check (e.g., ['media', 'avatars'])
    
    Returns:
        Full path to the file if found, None otherwise
    """
    storage = SupabaseStorage()
    
    if not storage.client:
        return None
    
    if subfolders is None:
        subfolders = ['media', 'avatars', 'thumbnails', 'posts']
    
    # Get both possible user identifiers
    identifiers = []
    
    # Add UUID if available
    try:
        if hasattr(user, 'profile') and user.profile:
            identifiers.append(str(user.profile.id))
    except Exception:
        pass
    
    # Add digit ID as fallback
    identifiers.append(str(user.id))
    
    # Check each identifier and subfolder combination
    for user_id in identifiers:
        for subfolder in subfolders:
            potential_path = f"{user_id}/{subfolder}/{filename}"
            
            try:
                if storage.exists(potential_path):
                    logger.info(f"Found file at: {potential_path}")
                    return potential_path
            except Exception as e:
                logger.debug(f"Error checking path {potential_path}: {e}")
    
    # Check root user folders too
    for user_id in identifiers:
        potential_path = f"{user_id}/{filename}"
        try:
            if storage.exists(potential_path):
                logger.info(f"Found file at: {potential_path}")
                return potential_path
        except Exception as e:
            logger.debug(f"Error checking path {potential_path}: {e}")
    
    logger.warning(f"File {filename} not found for user {user.id}")
    return None


def migrate_user_profile_if_needed(user: User) -> bool:
    """
    Ensure user has a profile with UUID, create if missing
    
    Args:
        user: Django User instance
        
    Returns:
        True if profile exists or was created, False on error
    """
    try:
        if not hasattr(user, 'profile') or not user.profile:
            from apps.authentication.models import UserProfile
            profile = UserProfile.objects.create(user=user)
            logger.info(f"Created profile with UUID {profile.id} for user {user.id}")
            return True
        return True
    except Exception as e:
        logger.error(f"Error creating profile for user {user.id}: {e}")
        return False


def get_file_url_with_fallback(user: User, file_path: str) -> Optional[str]:
    """
    Get file URL, checking both UUID and digit ID paths
    
    Args:
        user: Django User instance
        file_path: Relative file path
        
    Returns:
        Full URL to the file if found, None otherwise
    """
    storage = SupabaseStorage()
    
    # If the file_path already exists as-is, return its URL
    try:
        if storage.exists(file_path):
            return storage.url(file_path)
    except Exception:
        pass
    
    # Extract filename from path
    filename = file_path.split('/')[-1] if '/' in file_path else file_path
    
    # Try to find the file using our search function
    found_path = find_user_file_path(user, filename)
    
    if found_path:
        try:
            return storage.url(found_path)
        except Exception as e:
            logger.error(f"Error getting URL for {found_path}: {e}")
    
    return None