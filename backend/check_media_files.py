#!/usr/bin/env python
"""Debug script to check media file deletion"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append('/d/SMMS/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')

django.setup()

from apps.media.models import MediaFile
from django.contrib.auth import get_user_model

User = get_user_model()

def check_media_files():
    print("=== Checking Media Files in Database ===")
    
    # Get total counts
    total_files = MediaFile.objects.count()
    total_users = User.objects.count()
    print(f"Total media files: {total_files}")
    print(f"Total users: {total_users}")
    
    # Check files per user
    for user in User.objects.all():
        user_files = MediaFile.objects.filter(user=user)
        print(f"\nUser: {user.username} (ID: {user.id})")
        print(f"Number of files: {user_files.count()}")
        
        # Show some file details
        for file in user_files[:5]:  # Show first 5 files
            print(f"\n  File ID: {file.id}")
            print(f"  Name: {file.name}")
            print(f"  Type: {file.file_type}")
            print(f"  Created: {file.created_at}")
            # Check ownership fields
            print(f"  User ID on file: {file.user_id}")

if __name__ == "__main__":
    check_media_files()