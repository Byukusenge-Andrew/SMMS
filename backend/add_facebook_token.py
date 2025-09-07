#!/usr/bin/env python
"""
Manually add Facebook token to user account for testing
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from django.contrib.auth.models import User
from apps.authentication.models import SocialMediaAccount as AuthSocialMediaAccount
from apps.integrations.models import SocialMediaAccount, SocialMediaPlatform
import requests

def add_facebook_token():
    """Add Facebook token to user account"""
    print("🔧 Adding Facebook Token to User Account")
    print("=" * 50)
    
    # Your Facebook token
    facebook_token = "EAAJotvnQpZA0BPeW2qQKZB906rDehEMcxTjc1yaXssHgHFZCtTlRajCzQ0eueui9UIMKGJ0BspfQFTCiMpPZBeXJ3ArCCZCI3MfGuFUcimUI2klTVx5kZAV2G8hWmZCI7uLdj8MiP1v63K4YcRZCadxQXKO3pQzW2BeVLXFhxftVpAk47nLBui6jI8SBmHq0CgZC7UZBzFpIFhb0YHwVaBfEpZBqZBaZBuFzv1lnTHC2WawZDZD"
    
    # Get user
    try:
        user = User.objects.get(id=3)
        print(f"✅ User: {user.email}")
    except User.DoesNotExist:
        print("❌ User not found")
        return
    
    # Get Facebook user data
    print("\n📋 Getting Facebook user data...")
    response = requests.get(f'https://graph.facebook.com/v18.0/me?access_token={facebook_token}&fields=id,name,email')
    
    if response.status_code != 200:
        print(f"❌ Failed to get Facebook user data: {response.text}")
        return
    
    fb_user_data = response.json()
    fb_user_id = fb_user_data.get('id')
    fb_name = fb_user_data.get('name')
    fb_email = fb_user_data.get('email')
    
    print(f"✅ Facebook User: {fb_name}")
    print(f"✅ Facebook ID: {fb_user_id}")
    print(f"✅ Facebook Email: {fb_email}")
    
    # Save to integrations SocialMediaAccount
    print("\n💾 Saving to integrations SocialMediaAccount...")
    try:
        integrated_account, created = SocialMediaAccount.objects.update_or_create(
            user=user,
            platform=SocialMediaPlatform.FACEBOOK,
            platform_user_id=fb_user_id,
            defaults={
                'username': fb_name or fb_email,
                'display_name': fb_name,
                'access_token': facebook_token,
                'refresh_token': None,
                'token_expires_at': None,
                'is_active': True,
            }
        )
        print(f"✅ Integration account {'created' if created else 'updated'}: {integrated_account.id}")
    except Exception as e:
        print(f"❌ Error saving integration account: {e}")
    
    # Save to authentication SocialMediaAccount
    print("\n💾 Saving to authentication SocialMediaAccount...")
    try:
        auth_account, created = AuthSocialMediaAccount.objects.update_or_create(
            user=user,
            platform='facebook',
            platform_user_id=fb_user_id,
            defaults={
                'username': fb_name or fb_email,
                'access_token': facebook_token,
                'refresh_token': None,
                'is_active': True,
            }
        )
        print(f"✅ Auth account {'created' if created else 'updated'}: {auth_account.id}")
    except Exception as e:
        print(f"❌ Error saving auth account: {e}")
    
    print("\n🎉 Facebook token added successfully!")
    print("=" * 50)
    print("📋 Next Steps:")
    print("1. Refresh the frontend integrations page")
    print("2. Facebook should now show 'Disconnect' instead of 'Connect'")
    print("3. You can test posting to Facebook")

if __name__ == '__main__':
    add_facebook_token()
