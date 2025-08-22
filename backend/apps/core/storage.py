"""
Supabase Storage Integration for Django
Handles file uploads to Supabase Storage buckets
"""

import logging
import mimetypes
import os
import uuid
from io import BytesIO
from typing import Optional, Tuple

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage, FileSystemStorage
from django.utils.deconstruct import deconstructible

from supabase import Client, create_client
import base64
import json

logger = logging.getLogger(__name__)


@deconstructible
class SupabaseStorage(Storage):
    """
    Custom Django Storage backend for Supabase Storage
    """

    def __init__(self):
        self.supabase_url = getattr(settings, "SUPABASE_URL", os.getenv("SUPABASE_URL"))
        # Prefer a dedicated service role key when present; fall back to SUPABASE_KEY
        service_role = getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
        fallback_key = getattr(settings, "SUPABASE_KEY", os.getenv("SUPABASE_KEY"))
        self.supabase_key = service_role or fallback_key
        self.bucket_name = getattr(settings, "SUPABASE_BUCKET", os.getenv("SUPABASE_BUCKET", "keativpictures"))
        # Local filesystem fallback storage
        self.local_storage = FileSystemStorage(location=getattr(settings, 'MEDIA_ROOT', None), base_url=getattr(settings, 'MEDIA_URL', '/media/'))

        if not self.supabase_url or not self.supabase_key:
            # If Supabase config is missing, we will rely entirely on local storage
            logger.warning("Supabase config missing; will use local FileSystemStorage for all media operations.")
            self.client = None  # type: ignore
            return

        self.client: Client = create_client(self.supabase_url, self.supabase_key)
        self._log_key_role_sanity()

    def _decode_jwt_payload(self, token: str) -> dict:
        try:
            parts = token.split(".")
            if len(parts) < 2:
                return {}
            # Base64 URL decode the payload (second part)
            padded = parts[1] + "=" * (-len(parts[1]) % 4)
            data = base64.urlsafe_b64decode(padded.encode("utf-8"))
            return json.loads(data.decode("utf-8"))
        except Exception:
            return {}

    def _log_key_role_sanity(self) -> None:
        """Log a helpful warning if the provided key is an anon key (will cause 403 for uploads unless policies allow)."""
        claims = self._decode_jwt_payload(self.supabase_key)
        role = claims.get("role") if isinstance(claims, dict) else None
        if role and role != "service_role":
            logger.warning(
                "Supabase key role is '%s'. For server-side uploads, use the service role key or set storage policies to allow inserts.",
                role,
            )

    def _save(self, name: str, content) -> str:
        """
        Save file to Supabase Storage
        """
        try:
            # Generate unique filename if needed
            if not name:
                name = f"{uuid.uuid4()}.jpg"

            # Ensure unique filename
            name = self._get_unique_name(name)

            # Read content
            if hasattr(content, "read"):
                file_data = content.read()
            else:
                file_data = content

            # If Supabase client is configured, try uploading there first
            if self.client is not None:
                response = self.client.storage.from_(self.bucket_name).upload(
                    path=name,
                    file=file_data,
                    file_options={"content-type": mimetypes.guess_type(name)[0] or "application/octet-stream"},
                )

                if getattr(response, "error", None):
                    raise Exception(f"Upload failed: {response.error}")

                logger.info(f"Successfully uploaded {name} to Supabase")
                return name

            # If no Supabase client, fall through to local
            raise Exception("Supabase client not configured")

        except Exception as e:
            # Fallback: save to local filesystem
            logger.error(f"Error uploading {name} to Supabase: {str(e)}")
            try:
                # Ensure folder structure exists and save locally
                local_name = name
                # Save using FileSystemStorage; wrap bytes in ContentFile
                saved_local_name = self.local_storage.save(local_name, ContentFile(file_data))
                logger.warning(f"Saved media to local storage as fallback: {saved_local_name}")
                # Prefix with 'local/' to allow url/exists/delete to route to local storage
                return f"local/{saved_local_name}"
            except Exception as le:
                logger.error(f"Local storage fallback failed for {name}: {le}")
                raise

    def _get_unique_name(self, name: str) -> str:
        """
        Generate a unique filename by checking if it exists
        """
        original_name = name
        counter = 1

        while self.exists(name):
            base, ext = os.path.splitext(original_name)
            name = f"{base}_{counter}{ext}"
            counter += 1

        return name

    def delete(self, name: str) -> bool:
        """
        Delete file from Supabase Storage
        """
        try:
            if name.startswith('local/'):
                return self.local_storage.delete(name.replace('local/', '', 1)) is None
            if self.client is None:
                return self.local_storage.delete(name) is None
            response = self.client.storage.from_(self.bucket_name).remove([name])

            if response.error:
                logger.error(f"Supabase delete error: {response.error}")
                return False

            logger.info(f"Successfully deleted {name} from Supabase")
            return True

        except Exception as e:
            logger.error(f"Error deleting {name} from Supabase: {str(e)}")
            return False

    def exists(self, name: str) -> bool:
        """
        Check if file exists in Supabase Storage
        """
        try:
            if name.startswith('local/'):
                return self.local_storage.exists(name.replace('local/', '', 1))
            if self.client is None:
                return self.local_storage.exists(name)
            directory = os.path.dirname(name) or ""
            basename = os.path.basename(name)
            response = self.client.storage.from_(self.bucket_name).list(path=directory)

            # storage3 may return a simple list or an object with .data/.error
            data = getattr(response, "data", response)
            error = getattr(response, "error", None)
            if error or not data:
                return False

            return any(item.get("name") == basename for item in data)

        except Exception as e:
            logger.error(f"Error checking if {name} exists: {str(e)}")
            return False

    def listdir(self, path: str) -> Tuple[list, list]:
        """
        List directories and files in the given path
        """
        try:
            response = self.client.storage.from_(self.bucket_name).list(path=path)

            if response.error:
                return [], []

            directories = []
            files = []

            for item in response.data:
                if item.get("id"):  # Files have id
                    files.append(item["name"])
                else:  # Directories don't have id
                    directories.append(item["name"])

            return directories, files

        except Exception as e:
            logger.error(f"Error listing directory {path}: {str(e)}")
            return [], []

    def size(self, name: str) -> int:
        """
        Get file size
        """
        try:
            if name.startswith('local/'):
                return self.local_storage.size(name.replace('local/', '', 1))
            if self.client is None:
                return self.local_storage.size(name)
            directory = os.path.dirname(name) or ""
            basename = os.path.basename(name)
            response = self.client.storage.from_(self.bucket_name).list(path=directory)

            data = getattr(response, "data", response)
            error = getattr(response, "error", None)
            if error or not data:
                return 0

            for item in data:
                if item.get("name") == basename:
                    return item.get("metadata", {}).get("size", 0)
            return 0

        except Exception as e:
            logger.error(f"Error getting size of {name}: {str(e)}")
            return 0

    def url(self, name: str) -> str:
        """
        Get public URL for the file
        """
        try:
            if name.startswith('local/'):
                local_name = name.replace('local/', '', 1)
                return self.local_storage.url(local_name)
            if self.client is None:
                return self.local_storage.url(name)
            response = self.client.storage.from_(self.bucket_name).get_public_url(name)
            return response

        except Exception as e:
            logger.error(f"Error getting URL for {name}: {str(e)}")
            return ""

    def get_accessed_time(self, name: str):
        """
        Not implemented for Supabase
        """
        raise NotImplementedError("Supabase storage doesn't support access time")

    def get_created_time(self, name: str):
        """
        Get file creation time
        """
        try:
            directory = os.path.dirname(name) or ""
            basename = os.path.basename(name)
            response = self.client.storage.from_(self.bucket_name).list(path=directory)

            data = getattr(response, "data", response)
            error = getattr(response, "error", None)
            if error or not data:
                return None

            for item in data:
                if item.get("name") == basename:
                    return item.get("created_at")
            return None

        except Exception as e:
            logger.error(f"Error getting creation time for {name}: {str(e)}")
            return None

    def get_modified_time(self, name: str):
        """
        Get file modification time
        """
        try:
            directory = os.path.dirname(name) or ""
            basename = os.path.basename(name)
            response = self.client.storage.from_(self.bucket_name).list(path=directory)

            data = getattr(response, "data", response)
            error = getattr(response, "error", None)
            if error or not data:
                return None

            for item in data:
                if item.get("name") == basename:
                    return item.get("created_at")
            return None

        except Exception as e:
            logger.error(f"Error getting modification time for {name}: {str(e)}")
            return None


class SupabaseMediaHandler:
    """
    Utility class for handling media uploads to Supabase
    """

    def __init__(self):
        self.storage = SupabaseStorage()

    def upload_image(self, image_file, folder: str = "images") -> Tuple[str, str]:
        """
        Upload an image file to Supabase
        Returns: (file_path, public_url)
        """
        try:
            # Generate filename
            file_extension = self._get_file_extension(image_file)
            filename = f"{folder}/{uuid.uuid4()}{file_extension}"

            # Save to Supabase
            saved_path = self.storage.save(filename, image_file)
            public_url = self.storage.url(saved_path)

            return saved_path, public_url

        except Exception as e:
            logger.error(f"Error uploading image: {str(e)}")
            raise

    def upload_post_media(self, media_file, post_id: str, media_type: str = "image") -> Tuple[str, str]:
        """
        Upload post media to Supabase
        Returns: (file_path, public_url)
        """
        try:
            # Generate filename with post organization
            file_extension = self._get_file_extension(media_file)
            filename = f"posts/{post_id}/{media_type}s/{uuid.uuid4()}{file_extension}"

            # Save to Supabase
            saved_path = self.storage.save(filename, media_file)
            public_url = self.storage.url(saved_path)

            return saved_path, public_url

        except Exception as e:
            logger.error(f"Error uploading post media: {str(e)}")
            raise

    def upload_user_avatar(self, avatar_file, user_id: str) -> Tuple[str, str]:
        """
        Upload user avatar to Supabase
        Returns: (file_path, public_url)
        """
        try:
            # Generate filename
            file_extension = self._get_file_extension(avatar_file)
            filename = f"avatars/{user_id}{file_extension}"

            # Delete existing avatar if it exists
            if self.storage.exists(filename):
                self.storage.delete(filename)

            # Save to Supabase
            saved_path = self.storage.save(filename, avatar_file)
            public_url = self.storage.url(saved_path)

            return saved_path, public_url

        except Exception as e:
            logger.error(f"Error uploading avatar: {str(e)}")
            raise

    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from Supabase
        """
        return self.storage.delete(file_path)

    def _get_file_extension(self, file) -> str:
        """
        Get file extension from uploaded file
        """
        if hasattr(file, "name") and file.name:
            return os.path.splitext(file.name)[1].lower()
        return ".jpg"  # Default extension


# Global instances (lazy initialization to avoid Django settings issues during import)
_supabase_storage = None
_supabase_media_handler = None

def get_supabase_storage():
    """Get or create the global supabase storage instance"""
    global _supabase_storage
    if _supabase_storage is None:
        _supabase_storage = SupabaseStorage()
    return _supabase_storage

def get_supabase_media_handler():
    """Get or create the global supabase media handler instance"""
    global _supabase_media_handler
    if _supabase_media_handler is None:
        _supabase_media_handler = SupabaseMediaHandler()
    return _supabase_media_handler
