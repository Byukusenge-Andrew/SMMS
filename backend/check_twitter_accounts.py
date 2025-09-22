#!/usr/bin/env python
"""Debug script to check Twitter accounts in database"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append('/d/SMMS/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')

django.setup()

from apps.integrations.models import IntegratedAccount, SocialMediaPlatform
from apps.analytics.models import SocialMediaAccount
from django.contrib.auth import get_user_model

User = get_user_model()

def check_twitter_accounts():
    print("=== Checking Twitter Accounts in Database ===")
    
    # Check IntegratedAccount model
    print("\n1. IntegratedAccount (integrations app):")
    twitter_accounts = IntegratedAccount.objects.filter(platform='twitter')
    print(f"Total Twitter accounts: {twitter_accounts.count()}")
    
    for account in twitter_accounts:
        print(f"  User: {account.user.username} (ID: {account.user.id})")
        print(f"  Platform User ID: {account.platform_user_id}")
        print(f"  Username: {account.username}")
        print(f"  Active: {account.is_active}")
        print(f"  Has Access Token: {'Yes' if account.access_token else 'No'}")
        print(f"  Token Length: {len(account.access_token) if account.access_token else 0}")
        print(f"  Created: {account.created_at}")
        print("  ---")
    
    # Check SocialMediaAccount model  
    print("\n2. SocialMediaAccount (analytics app):")
    try:
        twitter_platform = SocialMediaPlatform.objects.get(name='twitter')
        analytics_accounts = SocialMediaAccount.objects.filter(platform=twitter_platform)
        print(f"Total Twitter analytics accounts: {analytics_accounts.count()}")
        
        for account in analytics_accounts:
            print(f"  User: {account.user.username} (ID: {account.user.id})")
            print(f"  Platform User ID: {account.platform_user_id}")
            print(f"  Username: {account.username}")
            print(f"  Active: {account.is_active}")
            print(f"  Has Access Token: {'Yes' if account.access_token else 'No'}")
            print(f"  Token Length: {len(account.access_token) if account.access_token else 0}")
            print(f"  Created: {account.created_at}")
            print("  ---")
    except SocialMediaPlatform.DoesNotExist:
        print("  Twitter platform not found in SocialMediaPlatform table")
    
    # Check all users
    print(f"\n3. Total users in system: {User.objects.count()}")
    for user in User.objects.all():
        print(f"  User: {user.username} (ID: {user.id})")

if __name__ == "__main__":
    check_twitter_accounts()