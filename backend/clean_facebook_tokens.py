#!/usr/bin/env python
"""
Clean up invalid Facebook tokens and prepare for re-authorization
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from apps.integrations.models import SocialMediaAccount, SocialMediaPlatform
from apps.authentication.models import SocialMediaAccount as AuthSocialMediaAccount
from django.contrib.auth.models import User

def clean_facebook_tokens():
    """Clean up invalid Facebook tokens"""
    
    user = User.objects.get(id=3)
    print(f"Cleaning Facebook tokens for user: {user.username}")
    
    # Check integrations app Facebook accounts
    fb_accounts_integrated = SocialMediaAccount.objects.filter(
        user=user,
        platform=SocialMediaPlatform.FACEBOOK
    )
    
    print(f"Found {fb_accounts_integrated.count()} Facebook accounts in integrations app")
    
    for account in fb_accounts_integrated:
        print(f"  Account: {account.username}")
        print(f"  Token length: {len(account.access_token) if account.access_token else 0}")
        print(f"  Is active: {account.is_active}")
        
        # Optionally deactivate the account (don't delete, just mark inactive)
        if account.access_token:
            print(f"  Deactivating account {account.username} due to invalid token")
            account.is_active = False
            account.save()
    
    # Check authentication app Facebook accounts
    fb_accounts_auth = AuthSocialMediaAccount.objects.filter(
        user=user,
        platform__icontains='facebook'
    )
    
    print(f"Found {fb_accounts_auth.count()} Facebook accounts in auth app")
    
    for account in fb_accounts_auth:
        print(f"  Account: {account.username}")
        print(f"  Platform: {account.platform}")
        print(f"  Is active: {account.is_active}")
        
        if account.access_token:
            print(f"  Deactivating account {account.username} due to invalid token")
            account.is_active = False
            account.save()
    
    print("\n=== Next Steps ===")
    print("1. Go to the integrations page: http://localhost:5173/integrations")
    print("2. Click 'Connect' for Facebook (should show Connect since we deactivated accounts)")
    print("3. Complete the OAuth flow with the new permissions")
    print("4. The new token will include:")
    print("   - pages_manage_posts")
    print("   - pages_read_engagement")
    print("   - pages_show_list")
    print("5. Make sure you have a Facebook Page to post to")

if __name__ == '__main__':
    clean_facebook_tokens()
