#!/usr/bin/env python3
"""
Debug Twitter OAuth 2.0 Configuration
This script helps identify issues with Twitter OAuth setup
"""

import os
import sys
import django
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from django.conf import settings
import requests
from urllib.parse import urlencode

def test_twitter_oauth_config():
    """Test Twitter OAuth 2.0 configuration and identify issues."""
    
    print("=== Twitter OAuth 2.0 Configuration Debug ===\n")
    
    # Check environment variables
    client_id = getattr(settings, 'TWITTER_CLIENT_ID', '')
    client_secret = getattr(settings, 'TWITTER_CLIENT_SECRET', '')
    redirect_uri = getattr(settings, 'TWITTER_REDIRECT_URI', '')
    scopes = getattr(settings, 'TWITTER_SCOPES', '')
    
    print("1. Configuration Check:")
    print(f"   ✓ Client ID: {client_id[:10]}..." if client_id else "   ✗ Client ID: Not configured")
    print(f"   ✓ Client Secret: {client_secret[:10]}..." if client_secret else "   ✗ Client Secret: Not configured")
    print(f"   ✓ Redirect URI: {redirect_uri}" if redirect_uri else "   ✗ Redirect URI: Not configured")
    print(f"   ✓ Scopes: {scopes}" if scopes else "   ✗ Scopes: Not configured")
    print()
    
    if not all([client_id, client_secret, redirect_uri]):
        print("❌ Missing required configuration. Please check your .env file.")
        return False
    
    # Test OAuth URL generation
    print("2. OAuth URL Generation:")
    auth_params = {
        'response_type': 'code',
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'scope': scopes,
        'state': 'test_state_12345'
    }
    
    auth_url = f"https://twitter.com/i/oauth2/authorize?{urlencode(auth_params)}"
    print(f"   Authorization URL: {auth_url}")
    print()
    
    # Test Twitter API endpoint accessibility
    print("3. Twitter API Accessibility Test:")
    try:
        # Test if we can reach Twitter's OAuth endpoint
        response = requests.get("https://api.twitter.com/2/oauth2/token", timeout=10)
        print(f"   ✓ Twitter API reachable (Status: {response.status_code})")
    except requests.exceptions.RequestException as e:
        print(f"   ✗ Twitter API unreachable: {e}")
        return False
    
    print()
    
    # Validation checklist
    print("4. Common Issues Checklist:")
    print("   Please verify in your Twitter Developer Portal:")
    print("   □ App exists and is active")
    print("   □ Client ID matches exactly (case-sensitive)")
    print("   □ Redirect URI is whitelisted exactly as:", redirect_uri)
    print("   □ App has 'Read and Write' permissions")
    print("   □ OAuth 2.0 is enabled for the app")
    print("   □ App is not in 'Development' mode restricting access")
    print()
    
    # Specific error guidance
    print("5. 'invalid_request' Error Causes:")
    print("   Most common reasons for this error:")
    print("   • Redirect URI mismatch (Twitter is very strict about exact matches)")
    print("   • Invalid or expired Client ID")
    print("   • App not properly configured for OAuth 2.0")
    print("   • Missing required app permissions")
    print("   • App in restricted mode")
    print()
    
    print("6. Next Steps:")
    print("   1. Double-check redirect URI in Twitter Developer Portal")
    print("   2. Ensure app has OAuth 2.0 enabled")
    print("   3. Verify app permissions include necessary scopes")
    print("   4. Try regenerating Client ID/Secret if still failing")
    print()
    
    return True

if __name__ == "__main__":
    test_twitter_oauth_config()