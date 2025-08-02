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
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible

from supabase import Client, create_client

logger = logging.getLogger(__name__)


@deconstructible
class SupabaseStorage(Storage):
    """
    Custom Django Storage backend for Supabase Storage
    """

    def __init__(self):
        self.supabase_url = getattr(settings, "SUPABASE_URL", os.getenv("SUPABASE_URL"))
        self.supabase_key = getattr(settings, "SUPABASE_KEY", os.getenv("SUPABASE_KEY"))
        self.bucket_name = getattr(settings, "SUPABASE_BUCKET", os.getenv("SUPABASE_BUCKET", "keativpictures"))

        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")

        self.client: Client = create_client(self.supabase_url, self.supabase_key)

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

            # Upload to Supabase
            response = self.client.storage.from_(self.bucket_name).upload(
                path=name,
                file=file_data,
                file_options={"content-type": mimetypes.guess_type(name)[0] or "application/octet-stream"},
            )

            if response.error:
                logger.error(f"Supabase upload error: {response.error}")
                raise Exception(f"Upload failed: {response.error}")

            logger.info(f"Successfully uploaded {name} to Supabase")
            return name

        except Exception as e:
            logger.error(f"Error uploading {name} to Supabase: {str(e)}")
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
            response = self.client.storage.from_(self.bucket_name).list(
                path=os.path.dirname(name) or "", search=os.path.basename(name)
            )

            if response.error:
                return False

            return len(response.data) > 0

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
            response = self.client.storage.from_(self.bucket_name).list(
                path=os.path.dirname(name) or "", search=os.path.basename(name)
            )

            if response.error or not response.data:
                return 0

            file_info = response.data[0]
            return file_info.get("metadata", {}).get("size", 0)

        except Exception as e:
            logger.error(f"Error getting size of {name}: {str(e)}")
            return 0

    def url(self, name: str) -> str:
        """
        Get public URL for the file
        """
        try:
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
            response = self.client.storage.from_(self.bucket_name).list(
                path=os.path.dirname(name) or "", search=os.path.basename(name)
            )

            if response.error or not response.data:
                return None

            file_info = response.data[0]
            return file_info.get("created_at")

        except Exception as e:
            logger.error(f"Error getting creation time for {name}: {str(e)}")
            return None

    def get_modified_time(self, name: str):
        """
        Get file modification time
        """
        try:
            response = self.client.storage.from_(self.bucket_name).list(
                path=os.path.dirname(name) or "", search=os.path.basename(name)
            )

            if response.error or not response.data:
                return None

            file_info = response.data[0]
            return file_info.get("updated_at")

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


# Global instance
supabase_media_handler = SupabaseMediaHandler()
