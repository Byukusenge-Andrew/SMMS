#!/usr/bin/env python3
"""
Twitter OAuth Configuration Checker
This script helps verify that your Twitter app is properly configured for OAuth 2.0.
"""

import os
import sys
import django
from django.conf import settings

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

def check_twitter_config():
    """Check Twitter OAuth configuration"""
    print("=== Twitter OAuth 2.0 Configuration Check ===\n")
    
    # Check required settings
    client_id = getattr(settings, 'TWITTER_CLIENT_ID', '')
    client_secret = getattr(settings, 'TWITTER_CLIENT_SECRET', '')
    redirect_uri = getattr(settings, 'TWITTER_REDIRECT_URI', '')
    scopes = getattr(settings, 'TWITTER_SCOPES', '')
    
    print("1. Environment Variables:")
    print(f"   TWITTER_CLIENT_ID: {'✓ Set' if client_id else '✗ Missing'}")
    print(f"   TWITTER_CLIENT_SECRET: {'✓ Set' if client_secret else '✗ Missing'}")
    print(f"   TWITTER_REDIRECT_URI: {redirect_uri or 'Using default'}")
    print(f"   TWITTER_SCOPES: {scopes or 'Using default'}")
    print()
    
    print("2. Configuration Details:")
    if client_id:
        print(f"   Client ID: {client_id[:10]}...{client_id[-5:] if len(client_id) > 15 else client_id}")
    if client_secret:
        print(f"   Client Secret: {client_secret[:5]}...{client_secret[-5:] if len(client_secret) > 10 else '***'}")
    print(f"   Redirect URI: {redirect_uri}")
    print(f"   Scopes: {scopes}")
    print()
    
    print("3. Twitter App Configuration Requirements:")
    print("   ✓ Your Twitter app must have OAuth 2.0 enabled")
    print("   ✓ Add this redirect URI to your Twitter app settings:")
    print(f"     {redirect_uri}")
    print("   ✓ Enable these permissions in your Twitter app:")
    print("     - Read (for tweet.read and users.read)")
    print("     - Write (for tweet.write)")
    print("   ✓ Your app must support PKCE (this is now implemented)")
    print()
    
    print("4. Common Issues:")
    print("   - Ensure redirect URI exactly matches what's in Twitter app settings")
    print("   - Check that OAuth 2.0 is enabled (not just OAuth 1.0a)")
    print("   - Verify your app has the required permissions")
    print("   - Make sure your Twitter app is not in 'Restricted' mode")
    print()
    
    # Check if all required settings are present
    if client_id and client_secret:
        print("✓ Configuration appears complete!")
        print("\nNext steps:")
        print("1. Verify the redirect URI in your Twitter app matches exactly")
        print("2. Test the OAuth flow")
        print("3. Check Twitter app permissions and OAuth 2.0 settings")
    else:
        print("✗ Configuration incomplete - missing required environment variables")
        return False
    
    return True

if __name__ == '__main__':
    check_twitter_config()