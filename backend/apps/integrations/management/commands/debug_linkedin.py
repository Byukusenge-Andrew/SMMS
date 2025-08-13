"""
LinkedIn Integration Debugging and Troubleshooting Tool
"""

import logging
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.integrations.models import SocialMediaAccount, SocialMediaPlatform
from apps.integrations.social_media_integrator import LinkedInIntegrator

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Debug LinkedIn integration issues and provide solutions'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--user-email',
            type=str,
            help='Debug for specific user email',
        )
        parser.add_argument(
            '--fix-tokens',
            action='store_true',
            help='Attempt to fix expired/invalid tokens',
        )
        parser.add_argument(
            '--test-api',
            action='store_true',
            help='Test LinkedIn API connectivity',
        )
    
    def handle(self, *args, **options):
        user_email = options.get('user_email')
        fix_tokens = options.get('fix_tokens')
        test_api = options.get('test_api')
        
        self.stdout.write(
            self.style.SUCCESS('🔍 LinkedIn Integration Debug Tool')
        )
        self.stdout.write('=' * 50)
        
        if test_api:
            self._test_api_connectivity()
            return
        
        # Get users to debug
        if user_email:
            try:
                users = [User.objects.get(email=user_email)]
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'User with email {user_email} not found')
                )
                return
        else:
            # Get all users with LinkedIn accounts
            users = User.objects.filter(
                integrated_accounts__platform=SocialMediaPlatform.LINKEDIN
            ).distinct()
        
        if not users:
            self.stdout.write(
                self.style.WARNING('No users with LinkedIn accounts found')
            )
            return
        
        for user in users:
            self._debug_user_linkedin(user, fix_tokens)
    
    def _test_api_connectivity(self):
        """Test basic LinkedIn API connectivity"""
        self.stdout.write('Testing LinkedIn API connectivity...')
        
        linkedin = LinkedInIntegrator()
        
        # Test authorization URL generation
        try:
            auth_url = linkedin.get_authorization_url()
            if auth_url:
                self.stdout.write(
                    self.style.SUCCESS('✅ Authorization URL generation: OK')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('❌ Authorization URL generation: FAILED')
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Authorization URL generation: ERROR - {e}')
            )
        
        # Check environment variables
        import os
        env_vars = [
            'LINKEDIN_CLIENT_ID',
            'LINKEDIN_CLIENT_SECRET',
            'LINKEDIN_REDIRECT_URI'
        ]
        
        self.stdout.write('\nEnvironment Variables:')
        for var in env_vars:
            value = os.getenv(var)
            if value:
                masked_value = f"{value[:8]}..." if len(value) > 8 else value
                self.stdout.write(f'  ✅ {var}: {masked_value}')
            else:
                self.stdout.write(f'  ❌ {var}: NOT SET')
    
    def _debug_user_linkedin(self, user, fix_tokens=False):
        """Debug LinkedIn integration for a specific user"""
        self.stdout.write(f'\n👤 Debugging LinkedIn for: {user.email}')
        self.stdout.write('-' * 40)
        
        # Get LinkedIn accounts for user
        linkedin_accounts = SocialMediaAccount.objects.filter(
            user=user,
            platform=SocialMediaPlatform.LINKEDIN
        )
        
        if not linkedin_accounts.exists():
            self.stdout.write('  ❌ No LinkedIn accounts found')
            return
        
        for account in linkedin_accounts:
            self._debug_account(account, fix_tokens)
    
    def _debug_account(self, account, fix_tokens=False):
        """Debug a specific LinkedIn account"""
        self.stdout.write(f'\n📱 Account: {account.username or "Unknown"}')
        self.stdout.write(f'   Status: {"Active" if account.is_active else "Inactive"}')
        self.stdout.write(f'   Verified: {"Yes" if account.is_verified else "No"}')
        self.stdout.write(f'   Connections: {account.followers_count or 0}')  # Ensure label is consistent
        self.stdout.write(f'   Created: {account.connected_at}')

        # Test token validity
        linkedin = LinkedInIntegrator()

        if not account.access_token:
            self.stdout.write('  ❌ No access token found')
            if fix_tokens:
                self._suggest_token_fix(account)
            return

        # Test profile fetch
        try:
            result = linkedin.get_profile(account.access_token)

            if result.get('success'):
                profile = result.get('profile', {})
                self.stdout.write('  ✅ Token is valid')
                self.stdout.write(f'     Profile: {profile.get("name", "Unknown")}')
                self.stdout.write(f'     Connections: {profile.get("connection_count", profile.get("follower_count", 0))}')

                # Update follower count if different
                new_count = profile.get('follower_count', 0)
                if new_count != (account.followers_count or 0):
                    if fix_tokens:
                        account.followers_count = new_count
                        account.save(update_fields=['followers_count'])
                        self.stdout.write(f'  ✅ Updated follower count to {new_count}')
                    else:
                        self.stdout.write(f'  ⚠️  Follower count needs update: {account.followers_count or 0} → {new_count}')
                        self.stdout.write('     Run with --fix-tokens to update')
            else:
                error = result.get('error', 'Unknown error')
                self.stdout.write(f'  ❌ Token is invalid: {error}')

                if fix_tokens:
                    self._suggest_token_fix(account)

        except Exception as e:
            self.stdout.write(f'  ❌ Error testing token: {e}')
    
    def _suggest_token_fix(self, account):
        """Suggest fixes for token issues"""
        self.stdout.write('\n🔧 Suggested Fixes:')
        
        if not account.access_token:
            self.stdout.write('  1. Reconnect LinkedIn account through frontend')
            self.stdout.write('  2. Check OAuth flow is working correctly')
        else:
            # Check if token looks expired based on common error patterns
            self.stdout.write('  1. Token may be expired - user needs to reconnect')
            self.stdout.write('  2. Check if LinkedIn app credentials are correct')
            self.stdout.write('  3. Verify redirect URI matches LinkedIn app settings')
            self.stdout.write('  4. Check if user revoked app permissions')
        
        # Provide direct reconnection URL
        frontend_url = 'http://localhost:3000/dashboard/integrations'  # Adjust as needed
        self.stdout.write(f'\n🔗 Reconnection URL: {frontend_url}')
        
        self.stdout.write('\n📋 Debug Info for LinkedIn App:')
        self.stdout.write(f'   Account ID: {account.id}')
        self.stdout.write(f'   User ID: {account.user.id}')
        self.stdout.write(f'   Platform: {account.platform}')
        
        # Check for common "external member binding" issue
        metadata = getattr(account, 'metadata', None)
        if metadata and 'external member binding exists' in str(metadata):
            self.stdout.write('\n⚠️  EXTERNAL MEMBER BINDING DETECTED:')
            self.stdout.write('   This means the LinkedIn account is already connected to another app.')
            self.stdout.write('   Solution: User needs to disconnect from other apps first.')
            self.stdout.write('   Or use a different LinkedIn account.')
