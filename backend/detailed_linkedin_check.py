#!/usr/bin/env python3
"""
Check LinkedIn Token Binding in Database
"""
import os
import sys
import django

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from django.contrib.auth.models import User
from apps.integrations.models import SocialMediaAccount as IntegratedAccount, SocialMediaPlatform
from apps.authentication.models import SocialMediaAccount

def detailed_linkedin_check():
    """Detailed check of LinkedIn integration"""
    print("🔍 DETAILED LinkedIn Database Check")
    print("=" * 60)
    
    # Find the specific user from the logs (byuridrew@gmail.com)
    try:
        user = User.objects.get(email='byuridrew@gmail.com')
        print(f"\n👤 User Found: {user.username} (ID: {user.id})")
        print(f"   Email: {user.email}")
        print(f"   Active: {user.is_active}")
        print(f"   Last Login: {user.last_login}")
        
        # Check IntegratedAccount for this user
        print(f"\n📊 IntegratedAccounts for {user.username}:")
        integrated_accounts = IntegratedAccount.objects.filter(user=user)
        print(f"   Total accounts: {integrated_accounts.count()}")
        
        for account in integrated_accounts:
            print(f"   - Platform: {account.platform}")
            print(f"     Platform User ID: {account.platform_user_id}")
            print(f"     Username: {account.username}")
            print(f"     Display Name: {account.display_name}")
            print(f"     Access Token: {'✅ Present' if account.access_token else '❌ Missing'}")
            print(f"     Refresh Token: {'✅ Present' if account.refresh_token else '❌ Missing'}")
            print(f"     Token Expires: {account.token_expires_at}")
            print(f"     Active: {account.is_active}")
            print(f"     Created: {account.created_at}")
            print(f"     Updated: {account.updated_at}")
            print()
        
        # Check Analytics SocialMediaAccount for this user
        print(f"\n📈 Analytics SocialMediaAccounts for {user.username}:")
        analytics_accounts = SocialMediaAccount.objects.filter(user=user)
        print(f"   Total accounts: {analytics_accounts.count()}")
        
        for account in analytics_accounts:
            print(f"   - Platform: {account.platform.name}")
            print(f"     Platform User ID: {account.platform_user_id}")
            print(f"     Username: {account.username}")
            print(f"     Access Token: {'✅ Present' if account.access_token else '❌ Missing'}")
            print(f"     Refresh Token: {'✅ Present' if account.refresh_token else '❌ Missing'}")
            print(f"     Active: {account.is_active}")
            print()
    
    except User.DoesNotExist:
        print("❌ User byuridrew@gmail.com not found")
        
        # Show all users instead
        print("\n👥 All Users in Database:")
        users = User.objects.all()
        for user in users:
            print(f"   - {user.username} ({user.email}) - ID: {user.id}")
    
    # Summary of all LinkedIn accounts
    print(f"\n🔗 ALL LinkedIn Accounts Summary:")
    print("IntegratedAccount (apps.integrations):")
    linkedin_integrated = IntegratedAccount.objects.filter(platform='linkedin')
    for account in linkedin_integrated:
        token_status = "✅ Has tokens" if (account.access_token and account.refresh_token) else "❌ Missing tokens"
        print(f"   - {account.user.username}: {token_status}")
    
    print("Analytics SocialMediaAccount:")
    linkedin_analytics = SocialMediaAccount.objects.filter(platform='linkedin')
    for account in linkedin_analytics:
        token_status = "✅ Has tokens" if (account.access_token and account.refresh_token) else "❌ Missing tokens"
        print(f"   - {account.user.username}: {token_status}")
    
    print("\n" + "=" * 60)

if __name__ == '__main__':
    detailed_linkedin_check()
