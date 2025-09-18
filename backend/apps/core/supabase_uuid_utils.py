"""
Utility functions for managing Supabase storage with UUID-based organization
"""

import logging
from typing import List, Dict, Optional
from django.contrib.auth.models import User
from apps.core.storage import SupabaseStorage

logger = logging.getLogger(__name__)


class SupabaseUUIDMigrator:
    """Helper class to migrate files from digit-based folders to UUID-based folders"""
    
    def __init__(self):
        self.storage = SupabaseStorage()
        
    def get_user_uuid_mapping(self) -> Dict[str, str]:
        """Get mapping of user digit IDs to UUIDs"""
        mapping = {}
        users = User.objects.select_related('profile').all()
        
        for user in users:
            try:
                if hasattr(user, 'profile') and user.profile:
                    mapping[str(user.id)] = str(user.profile.id)
                else:
                    logger.warning(f"User {user.id} has no profile - skipping")
            except Exception as e:
                logger.error(f"Error getting UUID for user {user.id}: {e}")
                
        return mapping
    
    def list_user_files(self, user_digit_id: str) -> List[str]:
        """List all files for a user by their digit ID"""
        try:
            if not self.storage.client:
                logger.error("Supabase client not configured")
                return []
                
            # List files in the user's folder
            response = self.storage.client.storage.from_(self.storage.bucket_name).list(
                path=user_digit_id
            )
            
            data = getattr(response, "data", response)
            error = getattr(response, "error", None)
            
            if error:
                logger.error(f"Error listing files for user {user_digit_id}: {error}")
                return []
                
            # Recursively get all files in subfolders
            files = []
            self._collect_files_recursive(user_digit_id, files)
            return files
            
        except Exception as e:
            logger.error(f"Error listing files for user {user_digit_id}: {e}")
            return []
    
    def _collect_files_recursive(self, path: str, files: List[str]) -> None:
        """Recursively collect all files in a path"""
        try:
            response = self.storage.client.storage.from_(self.storage.bucket_name).list(
                path=path
            )
            
            data = getattr(response, "data", response)
            error = getattr(response, "error", None)
            
            if error or not data:
                return
                
            for item in data:
                item_name = item.get("name", "")
                item_path = f"{path}/{item_name}" if path else item_name
                
                # Check if it's a file or folder
                if item.get("metadata") and item["metadata"].get("size") is not None:
                    # It's a file
                    files.append(item_path)
                else:
                    # It's a folder, recurse into it
                    self._collect_files_recursive(item_path, files)
                    
        except Exception as e:
            logger.error(f"Error collecting files in path {path}: {e}")
    
    def copy_file(self, source_path: str, dest_path: str) -> bool:
        """Copy file from source to destination in Supabase"""
        try:
            if not self.storage.client:
                return False
                
            # Download the file
            response = self.storage.client.storage.from_(self.storage.bucket_name).download(source_path)
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"Error downloading {source_path}: {response.error}")
                return False
                
            file_data = response if isinstance(response, bytes) else getattr(response, 'data', None)
            if not file_data:
                logger.error(f"No data received for {source_path}")
                return False
            
            # Upload to new location
            upload_response = self.storage.client.storage.from_(self.storage.bucket_name).upload(
                path=dest_path,
                file=file_data,
                file_options={"upsert": True}  # Overwrite if exists
            )
            
            if hasattr(upload_response, 'error') and upload_response.error:
                logger.error(f"Error uploading to {dest_path}: {upload_response.error}")
                return False
                
            logger.info(f"Successfully copied {source_path} to {dest_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error copying file from {source_path} to {dest_path}: {e}")
            return False
    
    def migrate_user_files(self, user_digit_id: str, user_uuid: str, dry_run: bool = True) -> Dict[str, int]:
        """Migrate all files for a user from digit ID folder to UUID folder"""
        results = {"success": 0, "failed": 0, "skipped": 0}
        
        try:
            files = self.list_user_files(user_digit_id)
            logger.info(f"Found {len(files)} files for user {user_digit_id}")
            
            for file_path in files:
                # Convert path from digit ID to UUID
                if file_path.startswith(user_digit_id + "/"):
                    new_path = file_path.replace(f"{user_digit_id}/", f"{user_uuid}/", 1)
                    
                    if dry_run:
                        logger.info(f"[DRY RUN] Would copy: {file_path} -> {new_path}")
                        results["success"] += 1
                    else:
                        if self.copy_file(file_path, new_path):
                            results["success"] += 1
                        else:
                            results["failed"] += 1
                else:
                    logger.warning(f"File path doesn't start with user ID: {file_path}")
                    results["skipped"] += 1
                    
        except Exception as e:
            logger.error(f"Error migrating files for user {user_digit_id}: {e}")
            results["failed"] += len(self.list_user_files(user_digit_id))
            
        return results
    
    def migrate_all_users(self, dry_run: bool = True) -> Dict[str, any]:
        """Migrate files for all users"""
        mapping = self.get_user_uuid_mapping()
        total_results = {"users_processed": 0, "total_success": 0, "total_failed": 0, "total_skipped": 0}
        
        logger.info(f"Starting migration for {len(mapping)} users (dry_run={dry_run})")
        
        for user_digit_id, user_uuid in mapping.items():
            logger.info(f"Processing user {user_digit_id} -> {user_uuid}")
            results = self.migrate_user_files(user_digit_id, user_uuid, dry_run)
            
            total_results["users_processed"] += 1
            total_results["total_success"] += results["success"]
            total_results["total_failed"] += results["failed"]
            total_results["total_skipped"] += results["skipped"]
            
            logger.info(f"User {user_digit_id} migration: {results}")
        
        return total_results


def get_user_uuid_from_digit_id(user_digit_id: int) -> Optional[str]:
    """Get user UUID from their digit ID"""
    try:
        user = User.objects.select_related('profile').get(id=user_digit_id)
        if hasattr(user, 'profile') and user.profile:
            return str(user.profile.id)
    except User.DoesNotExist:
        pass
    return None


def get_user_digit_id_from_uuid(user_uuid: str) -> Optional[int]:
    """Get user digit ID from their UUID"""
    try:
        from apps.authentication.models import UserProfile
        profile = UserProfile.objects.select_related('user').get(id=user_uuid)
        return profile.user.id
    except UserProfile.DoesNotExist:
        pass
    return None