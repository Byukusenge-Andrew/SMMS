#!/usr/bin/env python
"""
Test LinkedIn verification fix
"""
import os
import sys
import django
from django.conf import settings

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from django.test import Client
from apps.authentication.models import User
from rest_framework.authtoken.models import Token
import json

def test_linkedin_verification():
    print("=== Testing LinkedIn Verification Fix ===")
    
    # Get user and token
    try:
        user = User.objects.get(email='byuridrew@gmail.com')
        token, _ = Token.objects.get_or_create(user=user)
        print(f"✓ User found: {user.email}")
        print(f"✓ Token: {token.key[:10]}...")
    except User.DoesNotExist:
        print("❌ User not found")
        return
    
    # Test LinkedIn verification
    client = Client()
    response = client.get(
        '/api/integrations/linkedin/verify/',
        HTTP_AUTHORIZATION=f'Token {token.key}'
    )
    
    print(f"\n📊 LinkedIn Verification Results:")
    print(f"Status Code: {response.status_code}")
    
    try:
        content = response.json()
        print(f"Response: {json.dumps(content, indent=2)}")
        
        if response.status_code == 400 and content.get('success') == False:
            print("✅ FIXED: LinkedIn correctly returns 400 for invalid/revoked token")
        elif response.status_code == 200 and content.get('success') == True:
            print("⚠️  LinkedIn shows as connected (token might be valid)")
        else:
            print("❓ Unexpected response")
            
    except Exception as e:
        print(f"Response body: {response.content}")
        print(f"Error parsing JSON: {e}")

if __name__ == "__main__":
    test_linkedin_verification()
