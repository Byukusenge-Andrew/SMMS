#!/usr/bin/env python3
"""
Check LinkedIn Data in Database
"""
import os
import sys
import django
from datetime import datetime

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from django.contrib.auth.models import User
from apps.integrations.models import SocialMediaAccount as IntegratedAccount, SocialMediaPlatform
from apps.authentication.models import SocialMediaAccount

def check_linkedin_data():
    """Check for LinkedIn data in the database"""
    print("🔍 Checking LinkedIn data in database...")
    print("=" * 50)
    
    # Check IntegratedAccount (integrations app)
    print("\n📊 IntegratedAccount (apps.integrations.models):")
    linkedin_integrated = IntegratedAccount.objects.filter(platform='linkedin')
    print(f"  Found {linkedin_integrated.count()} LinkedIn integrated accounts")
    
    for account in linkedin_integrated:
        print(f"  - User: {account.user.username} ({account.user.email})")
        print(f"    Platform User ID: {account.platform_user_id}")
        print(f"    Username: {account.username}")
        print(f"    Display Name: {account.display_name}")
        print(f"    Has Access Token: {'Yes' if account.access_token else 'No'}")
        print(f"    Has Refresh Token: {'Yes' if account.refresh_token else 'No'}")
        print(f"    Is Active: {account.is_active}")
        print(f"    Created: {account.created_at}")
        print(f"    Updated: {account.updated_at}")
        print()
    
    # Check SocialMediaAccount (authentication app)
    print("\n📈 SocialMediaAccount (apps.authentication.models):")
    linkedin_auth = SocialMediaAccount.objects.filter(platform='linkedin')
    print(f"  Found {linkedin_auth.count()} LinkedIn authentication accounts")
    
    for account in linkedin_auth:
        print(f"  - User: {account.user.username} ({account.user.email})")
        print(f"    Platform User ID: {account.platform_user_id}")
        print(f"    Username: {account.username}")
        print(f"    Has Access Token: {'Yes' if account.access_token else 'No'}")
        print(f"    Has Refresh Token: {'Yes' if account.refresh_token else 'No'}")
        print(f"    Is Active: {account.is_active}")
        print(f"    Created: {account.created_at}")
        print(f"    Updated: {account.updated_at}")
        print()
    
    # Check all users
    print("\n👥 All Users:")
    users = User.objects.all()
    for user in users:
        print(f"  - {user.username} ({user.email}) - ID: {user.id}")
    
    # Check all SocialMediaPlatforms
    print("\n🌐 All Social Media Platform Choices:")
    for choice in SocialMediaPlatform:
        print(f"  - {choice.label} (value: {choice.value})")
    
    print("\n" + "=" * 50)
    print("✅ Database check complete!")

if __name__ == '__main__':
    check_linkedin_data()
