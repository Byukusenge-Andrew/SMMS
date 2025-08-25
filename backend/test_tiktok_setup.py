#!/usr/bin/env python
"""
Simple test script for TikTok integration setup
"""

import os
import django
import sys

# Add the backend directory to the path
backend_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_path)

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

def test_tiktok_imports():
    """Test that all TikTok integration components can be imported"""
    try:
        print("Testing TikTok service import...")
        from apps.integrations.services.tiktok_service import TikTokService
        print("✅ TikTok service imported successfully")
        
        print("Testing TikTok models import...")
        from apps.integrations.models import TikTokPost
        print("✅ TikTok models imported successfully")
        
        print("Testing TikTok serializers import...")
        from apps.integrations.serializers import TikTokPostSerializer
        print("✅ TikTok serializers imported successfully")
        
        print("Testing TikTok views import...")
        from apps.integrations.tiktok_views import tiktok_auth_url
        print("✅ TikTok views imported successfully")
        
        print("\n🎉 All TikTok integration components imported successfully!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_tiktok_service():
    """Test TikTok service initialization"""
    try:
        from apps.integrations.services.tiktok_service import TikTokService
        service = TikTokService()
        print("✅ TikTok service initialized successfully")
        return True
    except Exception as e:
        print(f"❌ TikTok service initialization failed: {e}")
        return False

if __name__ == '__main__':
    print("🧪 Testing TikTok Integration Setup\n")
    
    import_success = test_tiktok_imports()
    if not import_success:
        sys.exit(1)
    
    service_success = test_tiktok_service()
    if not service_success:
        sys.exit(1)
    
    print("\n✨ TikTok integration is ready!")
