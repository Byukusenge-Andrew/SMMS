#!/usr/bin/env python3
"""
Twitter OAuth URL Tester
This script generates the exact authorization URL that would be sent to Twitter.
"""

import os
import sys
import django
import secrets
import json
import base64
import time
import hashlib
from urllib.parse import urlencode

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from django.conf import settings

def generate_twitter_oauth_url():
    """Generate Twitter OAuth URL for testing"""
    print("=== Twitter OAuth URL Generator ===\n")
    
    # Get settings
    client_id = getattr(settings, 'TWITTER_CLIENT_ID', '') or 'SVZ5M2lINmtzekVHa0t5ODJXVTI6MTpjaQ'
    redirect_uri = getattr(settings, 'TWITTER_REDIRECT_URI', '') or 'http://127.0.0.1:8000/api/integrations/twitter/callback/'
    scope = getattr(settings, 'TWITTER_SCOPES', '') or 'tweet.read tweet.write users.read offline.access'
    
    print(f"Client ID: {client_id}")
    print(f"Redirect URI: {redirect_uri}")
    print(f"Scopes: {scope}")
    print()
    
    # Generate PKCE parameters
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('utf-8')).digest()
    ).decode('utf-8').rstrip('=')
    
    # Generate state
    state_data = {
        'csrf_token': secrets.token_urlsafe(16),
        'user_id': 2,  # Test user ID
        'timestamp': int(time.time())
    }
    state_val = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
    
    print(f"Code Verifier: {code_verifier}")
    print(f"Code Challenge: {code_challenge}")
    print(f"State: {state_val}")
    print()
    
    # Build OAuth parameters
    params = {
        'response_type': 'code',
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'scope': scope,
        'state': state_val,
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256'
    }
    
    # Generate URL
    url = f"https://twitter.com/i/oauth2/authorize?{urlencode(params)}"
    
    print("=== Generated OAuth URL ===")
    print(url)
    print()
    
    print("=== URL Parameters ===")
    for key, value in params.items():
        print(f"{key}: {value}")
    print()
    
    print("=== Next Steps ===")
    print("1. Copy the redirect URI and add it to your Twitter app settings")
    print("2. Ensure OAuth 2.0 is enabled in your Twitter app")
    print("3. Test the URL in a browser (should redirect to Twitter OAuth page)")
    print("4. If you get 'Something went wrong', the redirect URI doesn't match")
    
    return url

if __name__ == '__main__':
    generate_twitter_oauth_url()