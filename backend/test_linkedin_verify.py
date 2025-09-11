#!/usr/bin/env python
"""
Test LinkedIn Verify Endpoint
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from django.contrib.auth.models import User
from django.test import RequestFactory
from rest_framework.authtoken.models import Token
from apps.integrations.views_linkedin import verify_linkedin_credentials
from apps.integrations.models import SocialMediaAccount, SocialMediaPlatform

def test_verify_endpoint():
    print("🔍 TESTING LINKEDIN VERIFY ENDPOINT")
    print("=" * 50)
    
    # Get the user who has LinkedIn connected
    account = SocialMediaAccount.objects.filter(platform=SocialMediaPlatform.LINKEDIN).first()
    if not account:
        print("❌ No LinkedIn account found")
        return
        
    user = account.user
    print(f"Testing for user: {user.username}")
    print(f"Account verification status: {account.is_verified}")
    
    # Get or create token for the user
    token, created = Token.objects.get_or_create(user=user)
    print(f"User token: {token.key}")
    
    # Create a fake request with proper authentication
    factory = RequestFactory()
    request = factory.get('/api/integrations/linkedin/verify/')
    request.user = user
    
    # Add the authentication token to the request
    from rest_framework.authtoken.models import Token
    from django.http import HttpRequest
    
    # Simulate the TokenAuthentication middleware
    request.META['HTTP_AUTHORIZATION'] = f'Token {token.key}'
    
    # Call the verify endpoint directly
    try:
        response = verify_linkedin_credentials(request)
        print(f"Response Status: {response.status_code}")
        print(f"Response Data: {response.data}")
        
        if response.status_code == 200:
            print("✅ Verify endpoint working correctly!")
        else:
            print("❌ Verify endpoint still failing")
            print(f"Error: {response.data.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Exception in verify endpoint: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_verify_endpoint()
