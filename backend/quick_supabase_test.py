#!/usr/bin/env python
"""
Quick test to check if Supabase authentication is working with the updated service role key
"""

import os
import sys
import django
from io import BytesIO

# Add the backend directory to Python path
sys.path.append('d:/SMMS/backend')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from apps.core.storage import SupabaseStorage
from django.core.files.base import ContentFile
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_supabase_auth():
    """Test if Supabase authentication is working"""
    
    print("🔧 Testing Supabase Authentication")
    print("=" * 50)
    
    # Initialize storage
    storage = SupabaseStorage()
    
    # Check if client is initialized
    if not storage.client:
        print("❌ Supabase client not initialized. Check .env configuration.")
        return False
    
    print("✅ Supabase client initialized")
    print(f"🔑 Using key: {storage.supabase_key[:20]}...")
    print(f"📦 Bucket: {storage.bucket_name}")
    
    # Test authentication by trying to list bucket contents
    try:
        print("\n🧪 Testing bucket access...")
        response = storage.client.storage.from_(storage.bucket_name).list()
        
        if hasattr(response, 'error') and response.error:
            print(f"❌ Bucket access failed: {response.error}")
            return False
        else:
            print("✅ Bucket access successful!")
            data = getattr(response, 'data', response)
            print(f"📁 Found {len(data) if data else 0} items in bucket")
            return True
            
    except Exception as e:
        print(f"❌ Authentication test failed: {e}")
        return False

def test_file_upload():
    """Test actual file upload to Supabase"""
    
    print("\n🔧 Testing File Upload")
    print("=" * 30)
    
    storage = SupabaseStorage()
    
    if not storage.client:
        print("❌ Cannot test upload - Supabase client not available")
        return False
    
    # Create a test file
    test_content = b"Test avatar content for profile picture"
    test_file = ContentFile(test_content, name="test_avatar.jpg")
    
    try:
        # Test the upload using user-scoped path
        test_path = "999/avatars/test_avatar.jpg"  # Using user ID 999 for testing
        
        print(f"📤 Attempting upload to: {test_path}")
        saved_path = storage._save(test_path, test_file)
        
        if saved_path.startswith('local/'):
            print(f"❌ File saved to local storage (fallback): {saved_path}")
            print("   This means Supabase upload failed")
            return False
        else:
            print(f"✅ File successfully uploaded to Supabase: {saved_path}")
            
            # Clean up - delete the test file
            try:
                storage.delete(saved_path)
                print("🗑️ Test file cleaned up")
            except:
                print("⚠️ Could not clean up test file")
            
            return True
            
    except Exception as e:
        print(f"❌ Upload test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Quick Supabase Authentication & Upload Test")
    print("=" * 60)
    
    # Test 1: Authentication
    auth_works = test_supabase_auth()
    
    # Test 2: File Upload (only if auth works)
    if auth_works:
        upload_works = test_file_upload()
        
        if upload_works:
            print("\n🎉 SUCCESS: Supabase is working correctly!")
            print("   Your profile pictures should now upload to Supabase")
        else:
            print("\n⚠️ PARTIAL: Auth works but upload fails")
            print("   Check RLS policies or service role permissions")
    else:
        print("\n❌ FAILED: Authentication not working")
        print("   Profile pictures will save to local storage as fallback")
        
    print("\n" + "=" * 60)