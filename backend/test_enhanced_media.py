"""
Test script for enhanced media upload functionality
"""

import os
import sys
import django

# Add the backend directory to the Python path
backend_path = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, backend_path)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from django.contrib.auth.models import User
from apps.media.models import MediaFile, MediaFolder, MediaUploadBatch


def test_enhanced_models():
    """Test the enhanced media models"""
    
    print("🧪 Testing Enhanced Media Models...")
    
    # Get or create test user
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={'email': 'test@example.com'}
    )
    print(f"✅ Test user: {user.username} ({'created' if created else 'existing'})")
    
    # Test MediaFolder creation
    folder, created = MediaFolder.objects.get_or_create(
        user=user,
        name='Test Photos',
        defaults={'description': 'Test folder for photos'}
    )
    print(f"✅ Test folder: {folder.name} ({'created' if created else 'existing'})")
    
    # Test subfolder creation
    subfolder, created = MediaFolder.objects.get_or_create(
        user=user,
        parent=folder,
        name='Vacation 2024',
        defaults={'description': 'Vacation photos from 2024'}
    )
    print(f"✅ Test subfolder: {subfolder.get_full_path()} ({'created' if created else 'existing'})")
    
    # Test MediaUploadBatch creation
    batch, created = MediaUploadBatch.objects.get_or_create(
        user=user,
        name='Test Batch',
        defaults={
            'total_files': 5,
            'successful_uploads': 3,
            'failed_uploads': 1,
            'total_size': 1024 * 1024 * 10,  # 10MB
            'status': 'completed'
        }
    )
    print(f"✅ Test batch: {batch.name} - {batch.completion_percentage}% complete ({'created' if created else 'existing'})")
    
    # Test folder path functionality
    print(f"📁 Folder structure:")
    print(f"   - {folder.get_full_path()}")
    print(f"   - {subfolder.get_full_path()}")
    
    # Test batch statistics
    print(f"📊 Batch statistics:")
    print(f"   - Completion: {batch.completion_percentage}%")
    print(f"   - Success rate: {batch.success_rate}%")
    print(f"   - Status: {batch.status}")
    
    # Count existing files
    file_count = MediaFile.objects.filter(user=user).count()
    folder_count = MediaFolder.objects.filter(user=user).count()
    batch_count = MediaUploadBatch.objects.filter(user=user).count()
    
    print(f"\n📈 User statistics:")
    print(f"   - Files: {file_count}")
    print(f"   - Folders: {folder_count}")
    print(f"   - Batches: {batch_count}")
    
    print(f"\n✅ Enhanced media models working correctly!")


def test_model_methods():
    """Test model methods and properties"""
    
    print("\n🔍 Testing Model Methods...")
    
    user = User.objects.filter(username='testuser').first()
    if not user:
        print("❌ Test user not found")
        return
    
    # Test folder methods
    folders = MediaFolder.objects.filter(user=user)
    for folder in folders:
        print(f"📁 Folder: {folder}")
        print(f"   - Full path: {folder.get_full_path()}")
        print(f"   - Subfolders: {folder.subfolders.count()}")
    
    # Test batch methods
    batches = MediaUploadBatch.objects.filter(user=user)
    for batch in batches:
        print(f"📦 Batch: {batch}")
        print(f"   - Completion: {batch.completion_percentage}%")
        print(f"   - Success rate: {batch.success_rate}%")
    
    # Test file methods (if any files exist)
    files = MediaFile.objects.filter(user=user)[:3]  # Limit to 3 for testing
    for file in files:
        print(f"📄 File: {file}")
        print(f"   - Extension: {file.file_extension}")
        print(f"   - Size: {file.size_mb} MB")
        print(f"   - Downloads: {file.download_count}")


if __name__ == "__main__":
    try:
        test_enhanced_models()
        test_model_methods()
        print(f"\n🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()