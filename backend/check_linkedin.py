#!/usr/bin/env python
"""
Check LinkedIn Integration Status
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from apps.integrations.models import SocialMediaAccount, SocialMediaPlatform
from django.contrib.auth.models import User

def check_linkedin_accounts():
    print("🔍 CHECKING LINKEDIN ACCOUNTS")
    print("=" * 50)
    
    # Check LinkedIn accounts
    linkedin_accounts = SocialMediaAccount.objects.filter(platform=SocialMediaPlatform.LINKEDIN)
    print(f"LinkedIn accounts found: {linkedin_accounts.count()}")
    print()
    
    for account in linkedin_accounts:
        print(f"Account ID: {account.id}")
        print(f"User: {account.user.username}")
        print(f"Username: {account.username}")
        print(f"Display Name: {account.display_name}")
        print(f"Is Active: {account.is_active}")
        print(f"Is Verified: {account.is_verified}")
        print(f"Has Access Token: {bool(account.access_token)}")
        print(f"Access Token Length: {len(account.access_token) if account.access_token else 0}")
        print(f"Connected At: {account.connected_at}")
        print("-" * 30)
        
        # Test the verification manually
        if account.access_token:
            from apps.integrations.social_media_integrator import LinkedInIntegrator
            try:
                linkedin_integrator = LinkedInIntegrator()
                result = linkedin_integrator.get_profile(account.access_token)
                print(f"Manual verification test: {result.get('success', False)}")
                if result.get('success'):
                    profile = result.get('profile', {})
                    print(f"Profile Name: {profile.get('first_name', '')} {profile.get('last_name', '')}")
                    print(f"Connection Count: {profile.get('connection_count', 0)}")
                else:
                    print(f"Verification error: {result.get('error', 'Unknown error')}")
            except Exception as e:
                print(f"Manual verification failed: {e}")
        print("=" * 50)

if __name__ == "__main__":
    check_linkedin_accounts()
