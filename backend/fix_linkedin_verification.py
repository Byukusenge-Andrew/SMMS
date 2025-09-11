#!/usr/bin/env python
"""
Fix LinkedIn Verification Issue
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from apps.integrations.models import SocialMediaAccount, SocialMediaPlatform
from apps.integrations.social_media_integrator import LinkedInIntegrator

def fix_linkedin_verification():
    print("🔧 FIXING LINKEDIN VERIFICATION")
    print("=" * 50)
    
    # Get the LinkedIn account
    account = SocialMediaAccount.objects.filter(platform=SocialMediaPlatform.LINKEDIN).first()
    if not account:
        print("❌ No LinkedIn account found")
        return
        
    print(f"Found account: {account.username}")
    print(f"Current verification status: {account.is_verified}")
    print(f"Has access token: {bool(account.access_token)}")
    
    # Test the LinkedIn API
    linkedin_integrator = LinkedInIntegrator()
    try:
        result = linkedin_integrator.get_profile(account.access_token)
        print(f"API Test Result Success: {result.get('success', False)}")
        
        if result.get('success'):
            print("✅ Token is working! Updating account verification...")
            profile = result.get('profile', {})
            
            # Update account info
            account.is_verified = True
            full_name = f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip()
            if full_name:
                account.display_name = full_name
            
            if profile.get('profile_picture'):
                account.profile_image_url = profile.get('profile_picture')
                
            connection_count = profile.get('connection_count', 0) or profile.get('follower_count', 0)
            account.followers_count = connection_count
            
            account.save()
            
            print("✅ Account updated successfully!")
            print(f"   Display Name: {account.display_name}")
            print(f"   Connection Count: {account.followers_count}")
            print(f"   Is Verified: {account.is_verified}")
            
        else:
            print("❌ Token verification failed")
            error_msg = result.get('error', 'Unknown error')
            print(f"   Error: {error_msg}")
            
            # Check if token needs refresh
            if 'expired' in error_msg.lower() or 'invalid' in error_msg.lower():
                print("   Token may need to be refreshed. User should reconnect.")
            
    except Exception as e:
        print(f"❌ Exception during API test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_linkedin_verification()
