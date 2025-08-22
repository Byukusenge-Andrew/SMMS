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
from apps.integrations.models import SocialMediaAccount

def test_linkedin_token():
    print("Testing LinkedIn access tokens...")
    
    # Get LinkedIn accounts
    linkedin_accounts = SocialMediaAccount.objects.filter(platform='linkedin', user_id=2)
    
    for account in linkedin_accounts:
        print(f"\n--- Testing Account {account.id} ---")
        print(f"User: {account.user.username}")
        print(f"Token length: {len(account.access_token)}")
        print(f"Token preview: {account.access_token[:20]}...")
        
        # Test the access token with LinkedIn's userinfo endpoint
        headers = {
            "Authorization": f"Bearer {account.access_token}",
            "User-Agent": "SMMS/1.0",
        }
        
        try:
            print("Making request to LinkedIn userinfo API...")
            response = requests.get(
                "https://api.linkedin.com/v2/userinfo",
                headers=headers,
                timeout=30
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                profile_data = response.json()
                print(f"✅ Token is valid!")
                print(f"Profile: {profile_data}")
            else:
                print(f"❌ Token failed!")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Exception occurred: {e}")

if __name__ == "__main__":
    test_linkedin_token()
