#!/usr/bin/env python
"""
TikTok OAuth Configuration Test

Test script to verify TikTok OAuth configuration and URL generation
"""

import os
import sys
import django
from urllib.parse import urlparse, parse_qs

# Add the project directory to Python path
sys.path.append('/d/SMMS/backend')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from apps.integrations.services.tiktok_service import TikTokService

def test_tiktok_oauth_config():
    """Test TikTok OAuth configuration"""
    print("=== TikTok OAuth Configuration Test ===")
    
    try:
        # Initialize TikTok service
        service = TikTokService()
        print(f"✓ TikTok service initialized")
        
        # Force initialization to check credentials
        if service._lazy_init():
            print(f"✓ TikTok credentials loaded successfully")
            print(f"  - Client Key: {service.client_key[:10]}..." if service.client_key else "  - Client Key: Not set")
            print(f"  - Client Secret: {'***' if service.client_secret else 'Not set'}")
            print(f"  - Redirect URI: {service.redirect_uri}")
        else:
            print("✗ Failed to load TikTok credentials")
            return False
        
        # Generate authorization URL
        state = "test_user_123_1234567890"
        auth_url = service.get_authorization_url(state=state)
        print(f"✓ Authorization URL generated")
        print(f"  URL: {auth_url}")
        
        # Parse and validate URL components
        parsed_url = urlparse(auth_url)
        query_params = parse_qs(parsed_url.query)
        
        print(f"\n=== URL Analysis ===")
        print(f"Base URL: {parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}")
        print(f"Parameters:")
        for key, value in query_params.items():
            print(f"  - {key}: {value[0]}")
        
        # Validate required parameters
        required_params = ['client_key', 'scope', 'response_type', 'redirect_uri', 'code_challenge', 'code_challenge_method', 'state']
        missing_params = []
        
        for param in required_params:
            if param not in query_params:
                missing_params.append(param)
        
        if missing_params:
            print(f"✗ Missing required parameters: {', '.join(missing_params)}")
            return False
        else:
            print(f"✓ All required OAuth parameters present")
        
        # Validate specific parameter values
        if query_params.get('response_type', [''])[0] != 'code':
            print(f"✗ Invalid response_type: {query_params.get('response_type', [''])[0]}")
            return False
        
        if query_params.get('code_challenge_method', [''])[0] != 'S256':
            print(f"✗ Invalid code_challenge_method: {query_params.get('code_challenge_method', [''])[0]}")
            return False
        
        redirect_uri = query_params.get('redirect_uri', [''])[0]
        if not redirect_uri.endswith('/api/integrations/tiktok/callback/'):
            print(f"✗ Invalid redirect URI: {redirect_uri}")
            return False
        
        print(f"✓ All parameter values are valid")
        
        print(f"\n=== Test Result ===")
        print(f"✓ TikTok OAuth configuration is correct!")
        return True
        
    except Exception as e:
        print(f"✗ TikTok OAuth test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_tiktok_oauth_config()
    sys.exit(0 if success else 1)