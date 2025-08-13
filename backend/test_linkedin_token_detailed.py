#!/usr/bin/env python3
import os
import sys
import django

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

import requests
import json
from apps.integrations.models import SocialMediaAccount

def test_linkedin_token_detailed():
    print("=== LinkedIn Token Diagnostic Test ===\n")
    
    # Get LinkedIn accounts
    linkedin_accounts = SocialMediaAccount.objects.filter(platform='linkedin', user_id=2)
    
    if not linkedin_accounts.exists():
        print("❌ No LinkedIn accounts found!")
        return
    
    for account in linkedin_accounts:
        print(f"--- Testing Account {account.id} ---")
        print(f"User: {account.user.username}")
        print(f"Platform: {account.platform}")
        print(f"Token length: {len(account.access_token)} characters")
        print(f"Token starts with: {account.access_token[:50]}...")
        print(f"Account connected: {account.connected_at}")
        
        # Test with LinkedIn's userinfo endpoint
        headers = {
            "Authorization": f"Bearer {account.access_token}",
            "User-Agent": "SMMS/1.0",
        }
        
        try:
            print("\n📞 Making request to LinkedIn userinfo API...")
            print(f"URL: https://api.linkedin.com/v2/userinfo")
            print(f"Headers: Authorization: Bearer {account.access_token[:10]}...")
            
            response = requests.get(
                "https://api.linkedin.com/v2/userinfo",
                headers=headers,
                timeout=30
            )
            
            print(f"\n📊 Response Details:")
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                try:
                    profile_data = response.json()
                    print(f"✅ Token is VALID!")
                    print(f"Profile Data: {json.dumps(profile_data, indent=2)}")
                except json.JSONDecodeError as e:
                    print(f"⚠️ Valid response but JSON decode error: {e}")
                    print(f"Raw response: {response.text}")
            else:
                print(f"❌ Token FAILED!")
                print(f"Error Response: {response.text}")
                
                # Try to parse error details
                try:
                    error_data = response.json()
                    print(f"Error JSON: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"Raw error text: {response.text}")
                    
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
        
        print(f"\n{'='*50}\n")

if __name__ == "__main__":
    test_linkedin_token_detailed()
