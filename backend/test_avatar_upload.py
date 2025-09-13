#!/usr/bin/env python
"""
Test profile picture upload to verify Supabase integration
"""

import os
import sys
import django
from django.core.files.base import ContentFile

# Add the backend directory to Python path and setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')

try:
    django.setup()
    
    from django.contrib.auth.models import User
    from apps.authentication.models import UserProfile
    from apps.core.storage import SupabaseStorage
    
    print("🧪 Testing Profile Picture Upload to Supabase")
    print("=" * 60)
    
    # Get or create a test user
    user, created = User.objects.get_or_create(
        username='test_avatar_user',
        defaults={
            'email': 'test_avatar@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        }
    )
    
    if created:
        print(f"📱 Created test user: {user.username} (ID: {user.id})")
    else:
        print(f"📱 Using existing test user: {user.username} (ID: {user.id})")
    
    # Get or create user profile
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    if created:
        print(f"👤 Created user profile for {user.username}")
    else:
        print(f"👤 Using existing profile for {user.username}")
    
    # Create a fake avatar file
    fake_avatar_content = b"fake avatar image content for testing"
    avatar_file = ContentFile(fake_avatar_content, name="test_avatar.jpg")
    
    print(f"\n📂 Expected upload path: {user.id}/avatars/avatar.jpg")
    
    # Test the upload
    print("\n🔄 Uploading avatar...")
    
    # Save the avatar to the profile
    profile.avatar.save("test_avatar.jpg", avatar_file, save=True)
    
    print(f"✅ Avatar saved! Path: {profile.avatar.name}")
    print(f"🌐 Avatar URL: {profile.avatar.url}")
    
    # Check if it's stored in Supabase (not prefixed with 'local/')
    if profile.avatar.name.startswith('local/'):
        print("❌ Avatar was saved to local storage (fallback)")
        print("   This means Supabase upload failed")
    else:
        print("✅ Avatar was saved to Supabase storage!")
        print("   File organization follows user-scoped structure")
    
    # Verify the file exists in Supabase
    storage = SupabaseStorage()
    if storage.exists(profile.avatar.name):
        print("✅ File exists in Supabase storage")
    else:
        print("❌ File not found in Supabase storage")
    
    print("\n" + "=" * 60)
    print("🎉 Profile picture upload test completed!")
    
except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()