#!/usr/bin/env python
"""
Test TikTok service configuration
"""
import os
import sys
import django

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from apps.integrations.services.tiktok_service import TikTokService
from urllib.parse import urlparse, parse_qs

def test_tiktok_config():
    """Test TikTok service configuration"""
    print("🔍 Testing TikTok service configuration...")
    
    try:
        service = TikTokService()
        
        if service._lazy_init():
            print("✅ TikTok Service Initialized Successfully!")
            print(f"🔑 Client Key: {service.client_key}")
            print(f"🔀 Redirect URI: {service.redirect_uri}")
            
            # Generate test auth URL
            auth_url = service.get_authorization_url('test_state_123')
            print(f"🔗 Generated Auth URL:")
            print(f"   {auth_url}")
            
            # Parse the URL to check parameters
            parsed_url = urlparse(auth_url)
            params = parse_qs(parsed_url.query)
            
            print("\n📋 URL Parameters:")
            for key, value in params.items():
                print(f"   {key}: {value[0] if value else 'None'}")
            
            # Check specific redirect_uri
            if 'redirect_uri' in params:
                redirect_uri = params['redirect_uri'][0]
                print(f"\n✅ Redirect URI found: {redirect_uri}")
                
                # Check if it matches expected format
                expected = "http://127.0.0.1:8000/api/integrations/tiktok/callback/"
                if redirect_uri == expected:
                    print("✅ Redirect URI matches expected format!")
                else:
                    print(f"⚠️  Redirect URI doesn't match expected:")
                    print(f"   Expected: {expected}")
                    print(f"   Actual:   {redirect_uri}")
            else:
                print("❌ No redirect_uri parameter found in URL!")
            
            return True
        else:
            print("❌ Failed to initialize TikTok service")
            return False
            
    except Exception as e:
        print(f"❌ Error testing TikTok config: {e}")
        return False

if __name__ == "__main__":
    success = test_tiktok_config()
    sys.exit(0 if success else 1)
