#!/usr/bin/env python3
"""
TikTok Integration Debug Script
Check the current state of TikTok integration for a user
"""

import os
import sys
import django

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.integrations.models import SocialMediaAccount, SocialMediaPlatform
from django.conf import settings

def debug_tiktok_integration(user_id=None):
    """Debug TikTok integration for a specific user"""
    print("=== TikTok Integration Debug ===\n")
    
    # Check TikTok configuration
    print("1. TikTok Configuration:")
    client_key = getattr(settings, 'TIKTOK_CLIENT_KEY', '') or ''
    client_secret = getattr(settings, 'TIKTOK_CLIENT_SECRET', '') or ''
    redirect_uri = getattr(settings, 'TIKTOK_REDIRECT_URI', '') or ''
    scopes = getattr(settings, 'TIKTOK_SCOPES', '') or ''
    
    print(f"   TIKTOK_CLIENT_KEY: {'✓ Set' if client_key else '✗ Missing'}")
    print(f"   TIKTOK_CLIENT_SECRET: {'✓ Set' if client_secret else '✗ Missing'}")
    print(f"   TIKTOK_REDIRECT_URI: {redirect_uri}")
    print(f"   TIKTOK_SCOPES: {scopes}")
    print()
    
    # Check database platforms
    print("2. Database Platforms:")
    try:
        platforms = SocialMediaPlatform.objects.all()
        for platform in platforms:
            print(f"   - {platform.name}")
        
        tiktok_platform = None
        try:
            tiktok_platform = SocialMediaPlatform.objects.get(name='tiktok')
            print(f"   ✓ TikTok platform exists: {tiktok_platform}")
        except SocialMediaPlatform.DoesNotExist:
            print("   ✗ TikTok platform not found in database")
        except Exception as e:
            print(f"   ⚠ Error checking TikTok platform: {e}")
    except Exception as e:
        print(f"   ⚠ Error listing platforms: {e}")
    print()
    
    # Check for user accounts
    if user_id:
        print(f"3. User {user_id} TikTok Accounts:")
        try:
            User = get_user_model()
            user = User.objects.get(id=user_id)
            print(f"   User: {user.username} (ID: {user.id})")
            
            # Check all social media accounts for this user
            all_accounts = SocialMediaAccount.objects.filter(user=user)
            print(f"   Total accounts: {all_accounts.count()}")
            
            for account in all_accounts:
                print(f"   - Platform: {account.platform}, Active: {account.is_active}, Username: {account.username}")
            
            # Check TikTok accounts specifically
            try:
                tiktok_accounts = SocialMediaAccount.objects.filter(
                    user=user,
                    platform='tiktok',  # Try string first
                    is_active=True
                )
                print(f"   TikTok accounts (string): {tiktok_accounts.count()}")
                
                if tiktok_platform:
                    tiktok_accounts_obj = SocialMediaAccount.objects.filter(
                        user=user,
                        platform=tiktok_platform,
                        is_active=True
                    )
                    print(f"   TikTok accounts (object): {tiktok_accounts_obj.count()}")
                    
            except Exception as e:
                print(f"   ⚠ Error checking TikTok accounts: {e}")
                
        except User.DoesNotExist:
            print(f"   ✗ User {user_id} not found")
        except Exception as e:
            print(f"   ⚠ Error checking user: {e}")
    else:
        print("3. User Accounts: (No user ID provided)")
    print()
    
    # Check TikTok service initialization
    print("4. TikTok Service Test:")
    try:
        from apps.integrations.services.tiktok_service import TikTokService
        service = TikTokService()
        auth_url = service.get_authorization_url(state="test_state")
        print(f"   ✓ Service initialized successfully")
        print(f"   ✓ Auth URL generated: {auth_url[:100]}...")
    except Exception as e:
        print(f"   ✗ Service initialization failed: {e}")
    print()
    
    print("5. Recommendations:")
    if not client_key or not client_secret:
        print("   - Configure TikTok credentials in environment variables")
    if not tiktok_platform:
        print("   - Create TikTok platform in database")
    print("   - Check that OAuth callback is properly configured")
    print("   - Verify redirect URI matches TikTok app settings")

if __name__ == '__main__':
    user_id = 2  # Default to user ID 2, change as needed
    if len(sys.argv) > 1:
        user_id = int(sys.argv[1])
    
    debug_tiktok_integration(user_id)