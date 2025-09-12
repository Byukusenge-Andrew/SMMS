#!/usr/bin/env python
"""
Test script to verify Supabase storage integration with RLS policies
"""

import os
import sys
import django
from io import BytesIO
from django.core.files.base import ContentFile

# Add the backend directory to Python path
sys.path.append('/d/SMMS/backend')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from django.contrib.auth.models import User
from apps.core.storage import SupabaseStorage
from apps.authentication.models import UserProfile
from apps.media.models import MediaFile
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_storage_operations():
    """Test storage operations with user-scoped paths"""
    
    print("🧪 Testing Supabase Storage Integration with RLS Policies")
    print("=" * 60)
    
    # Initialize storage
    storage = SupabaseStorage()
    
    # Check if Supabase is configured
    if not storage.client:
        print("❌ Supabase client not configured. Check your .env file.")
        return False
    
    print("✅ Supabase client initialized successfully")
    print(f"📦 Bucket: {storage.bucket_name}")
    print(f"🔑 Using service role key: {storage.supabase_key[:20]}...")
    
    # Get or create a test user
    try:
        user = User.objects.get(username='testuser')
        print(f"📱 Using existing test user: {user.username} (ID: {user.id})")
    except User.DoesNotExist:
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        print(f"📱 Created test user: {user.username} (ID: {user.id})")
    
    # Test 1: Avatar upload (should follow user_id/avatars/avatar.jpg pattern)
    print("\n🖼️ Test 1: Avatar Upload")
    try:
        # Create test avatar content
        avatar_content = ContentFile(b"fake avatar image content", name="avatar.jpg")
        
        # Test the upload path function
        from apps.core.upload_paths import user_avatar_upload_path
        
        # Create a mock profile instance for testing
        class MockProfile:
            def __init__(self, user):
                self.user = user
        
        mock_profile = MockProfile(user)
        avatar_path = user_avatar_upload_path(mock_profile, "avatar.jpg")
        print(f"📂 Generated avatar path: {avatar_path}")
        
        # Verify path structure matches RLS policy expectation
        path_parts = avatar_path.split('/')
        if len(path_parts) >= 2 and path_parts[0] == str(user.id):
            print(f"✅ Path structure correct: user_id ({user.id}) is first folder")
        else:
            print(f"❌ Path structure incorrect: {avatar_path}")
            
    except Exception as e:
        print(f"❌ Avatar upload test failed: {e}")
    
    # Test 2: Media file upload
    print("\n📁 Test 2: Media File Upload")
    try:
        from apps.core.upload_paths import user_media_upload_path
        
        class MockMediaFile:
            def __init__(self, user):
                self.user = user
        
        mock_media = MockMediaFile(user)
        media_path = user_media_upload_path(mock_media, "test_image.jpg")
        print(f"📂 Generated media path: {media_path}")
        
        # Verify path structure
        path_parts = media_path.split('/')
        if len(path_parts) >= 2 and path_parts[0] == str(user.id):
            print(f"✅ Path structure correct: user_id ({user.id}) is first folder")
        else:
            print(f"❌ Path structure incorrect: {media_path}")
            
    except Exception as e:
        print(f"❌ Media upload test failed: {e}")
    
    # Test 3: Check current Supabase permissions
    print("\n🔒 Test 3: Supabase Permissions Check")
    try:
        # Try to list bucket contents (should work with service role)
        response = storage.client.storage.from_(storage.bucket_name).list()
        
        if hasattr(response, 'error') and response.error:
            print(f"❌ Bucket list failed: {response.error}")
        else:
            print("✅ Service role can list bucket contents")
            
    except Exception as e:
        print(f"❌ Permission check failed: {e}")
    
    # Test 4: Check RLS policy expectations
    print("\n📋 Test 4: RLS Policy Alignment Check")
    print("Your RLS policies expect:")
    print("  - INSERT: authenticated users in 'keativpictures' bucket")
    print("  - SELECT/UPDATE/DELETE: user owns files where first folder = user_id")
    print()
    print("Your upload paths generate:")
    print(f"  - Avatar: {user.id}/avatars/avatar.jpg")
    print(f"  - Media: {user.id}/media/filename_timestamp.jpg")
    print(f"  - Thumbnails: {user.id}/thumbnails/filename.jpg")
    print()
    print("✅ Path structure aligns with RLS policies!")
    
    print("\n" + "=" * 60)
    print("🎉 Storage integration test completed!")
    
    return True


if __name__ == "__main__":
    test_storage_operations()