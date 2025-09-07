#!/usr/bin/env python
"""
Check Facebook token permissions and guide re-authorization if needed
"""
import os
import django
import requests

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from apps.integrations.models import SocialMediaAccount, SocialMediaPlatform
from django.contrib.auth.models import User

def check_facebook_permissions():
    """Check Facebook token permissions"""
    
    # Get user and Facebook account
    user = User.objects.get(id=3)
    facebook_accounts = SocialMediaAccount.objects.filter(
        user=user,
        platform=SocialMediaPlatform.FACEBOOK,
        is_active=True
    )
    
    if not facebook_accounts.exists():
        print("No Facebook accounts found")
        return
        
    account = facebook_accounts.first()
    access_token = account.access_token
    
    print(f"Checking permissions for Facebook account: {account.username}")
    
    # Check token permissions
    permissions_response = requests.get(
        "https://graph.facebook.com/v18.0/me/permissions",
        params={"access_token": access_token},
        timeout=30
    )
    
    if permissions_response.status_code == 200:
        permissions_data = permissions_response.json()
        permissions = permissions_data.get("data", [])
        
        print("\nCurrent permissions:")
        granted_permissions = []
        for perm in permissions:
            permission_name = perm.get("permission")
            status = perm.get("status")
            print(f"  {permission_name}: {status}")
            if status == "granted":
                granted_permissions.append(permission_name)
        
        # Check required permissions
        required_permissions = [
            "email", 
            "public_profile", 
            "pages_show_list", 
            "pages_read_engagement", 
            "pages_manage_posts"
        ]
        
        missing_permissions = [p for p in required_permissions if p not in granted_permissions]
        
        if missing_permissions:
            print(f"\nMissing required permissions: {', '.join(missing_permissions)}")
            print("User needs to re-authorize with new permissions.")
            
            # Provide re-authorization URL
            from django.conf import settings
            app_id = settings.SOCIAL_MEDIA_CONFIGS['FACEBOOK']['APP_ID']
            redirect_uri = settings.SOCIAL_MEDIA_CONFIGS['FACEBOOK']['REDIRECT_URI']
            scope = 'email,public_profile,pages_show_list,pages_read_engagement,pages_manage_posts,publish_to_groups'
            
            auth_url = (
                f"https://www.facebook.com/v18.0/dialog/oauth?"
                f"client_id={app_id}&"
                f"redirect_uri={redirect_uri}&"
                f"scope={scope}&"
                f"response_type=code"
            )
            
            print(f"\nRe-authorization URL:")
            print(auth_url)
        else:
            print("\nAll required permissions are granted!")
    else:
        print(f"Error checking permissions: {permissions_response.text}")
    
    # Check user's pages
    print("\nChecking user's Facebook pages...")
    pages_response = requests.get(
        "https://graph.facebook.com/v18.0/me/accounts",
        params={"access_token": access_token},
        timeout=30
    )
    
    if pages_response.status_code == 200:
        pages_data = pages_response.json()
        pages = pages_data.get("data", [])
        
        print(f"Found {len(pages)} Facebook pages:")
        for page in pages:
            print(f"  Page: {page.get('name')} (ID: {page.get('id')})")
            print(f"  Category: {page.get('category', 'Unknown')}")
            print(f"  Has page token: {'Yes' if page.get('access_token') else 'No'}")
            print("  ---")
    else:
        print(f"Error checking pages: {pages_response.text}")

if __name__ == '__main__':
    check_facebook_permissions()
