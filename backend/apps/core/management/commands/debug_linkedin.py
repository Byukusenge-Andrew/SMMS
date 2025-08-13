"""
LinkedIn Integration Debugging Guide and Utilities
Comprehensive solution for LinkedIn OAuth issues and debugging
"""

import logging
import requests
import json
from typing import Dict, Optional, Any
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class LinkedInDebugger:
    """Comprehensive LinkedIn integration debugging utility"""
    
    def __init__(self):
        self.client_id = settings.LINKEDIN_CLIENT_ID
        self.client_secret = settings.LINKEDIN_CLIENT_SECRET
        self.redirect_uri = settings.LINKEDIN_REDIRECT_URI
    
    def debug_oauth_error(self, error_response: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze LinkedIn OAuth error and provide debugging information"""
        
        error_code = error_response.get('error', 'unknown')
        error_description = error_response.get('error_description', 'No description')
        
        debug_info = {
            'error_code': error_code,
            'error_description': error_description,
            'likely_causes': [],
            'solutions': [],
            'debug_steps': []
        }
        
        # Analyze specific error types
        if 'external member binding exists' in error_description.lower():
            debug_info['likely_causes'] = [
                'LinkedIn account is already connected to another app',
                'Previous OAuth token is still active in LinkedIn',
                'User has multiple LinkedIn developer apps with conflicting permissions',
                'LinkedIn account was connected to a different version of this app'
            ]
            debug_info['solutions'] = [
                'User needs to revoke app permissions in LinkedIn settings',
                'Clear all existing SocialMediaAccount records for this user/platform',
                'Use LinkedIn App Management console to revoke tokens',
                'Wait 24-48 hours for LinkedIn cache to clear',
                'Try with a different LinkedIn account for testing'
            ]
            debug_info['debug_steps'] = [
                'Check LinkedIn App Management: https://www.linkedin.com/developers/apps',
                'Go to LinkedIn Privacy Settings > Applications',
                'Remove any existing app permissions',
                'Clear Django database records',
                'Retry OAuth flow'
            ]
        
        elif 'authorization code expired' in error_description.lower():
            debug_info['likely_causes'] = [
                'OAuth authorization code took too long to exchange',
                'Network delays in callback processing',
                'User navigated away and back to callback URL',
                'Code was already used once (codes are single-use)'
            ]
            debug_info['solutions'] = [
                'Retry OAuth flow immediately',
                'Optimize callback processing speed',
                'Implement retry mechanism with fresh auth code',
                'Check network connectivity and latency'
            ]
        
        elif 'redirect uri/code verifier does not match' in error_description.lower():
            debug_info['likely_causes'] = [
                'Redirect URI mismatch between app config and request',
                'PKCE code verifier missing or incorrect',
                'Session state lost between auth and callback',
                'App configuration changed since auth started'
            ]
            debug_info['solutions'] = [
                'Verify redirect URI matches exactly in LinkedIn app config',
                'Implement proper PKCE flow with code verifier storage',
                'Check session management and state persistence',
                'Ensure consistent app configuration'
            ]
        
        return debug_info
    
    def check_app_configuration(self) -> Dict[str, Any]:
        """Verify LinkedIn app configuration"""
        config_status = {
            'client_id': {
                'value': self.client_id[:10] + '...' if self.client_id else 'NOT_SET',
                'valid': bool(self.client_id and len(self.client_id) > 10)
            },
            'client_secret': {
                'value': '***SET***' if self.client_secret else 'NOT_SET',
                'valid': bool(self.client_secret and len(self.client_secret) > 10)
            },
            'redirect_uri': {
                'value': self.redirect_uri,
                'valid': bool(self.redirect_uri and self.redirect_uri.startswith('http'))
            }
        }
        
        return config_status
    
    def test_linkedin_api_connectivity(self) -> Dict[str, Any]:
        """Test basic connectivity to LinkedIn API"""
        try:
            # Test basic LinkedIn API endpoint
            response = requests.get(
                'https://api.linkedin.com/v2/people',
                timeout=10
            )
            
            return {
                'success': True,
                'status_code': response.status_code,
                'reachable': response.status_code in [401, 403],  # Expected without auth
                'response_headers': dict(response.headers),
                'message': 'LinkedIn API is reachable'
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'LinkedIn API connectivity failed'
            }
    
    def generate_debug_report(self, user: User, error_response: Optional[Dict] = None) -> str:
        """Generate comprehensive debug report"""
        
        report_lines = [
            "=" * 80,
            "LINKEDIN INTEGRATION DEBUG REPORT",
            "=" * 80,
            f"Generated for user: {user.username} ({user.email})",
            f"Timestamp: {logger.handlers[0].formatter.formatTime(logging.LogRecord('', 0, '', 0, '', (), None)) if logger.handlers else 'N/A'}",
            ""
        ]
        
        # App Configuration
        report_lines.append("APP CONFIGURATION:")
        report_lines.append("-" * 40)
        config = self.check_app_configuration()
        for key, info in config.items():
            status = "✓" if info['valid'] else "✗"
            report_lines.append(f"{status} {key.upper()}: {info['value']}")
        report_lines.append("")
        
        # API Connectivity
        report_lines.append("API CONNECTIVITY:")
        report_lines.append("-" * 40)
        connectivity = self.test_linkedin_api_connectivity()
        if connectivity['success']:
            report_lines.append(f"✓ LinkedIn API reachable (status: {connectivity['status_code']})")
        else:
            report_lines.append(f"✗ LinkedIn API unreachable: {connectivity['error']}")
        report_lines.append("")
        
        # User's LinkedIn Accounts
        report_lines.append("USER'S LINKEDIN ACCOUNTS:")
        report_lines.append("-" * 40)
        try:
            from apps.authentication.models import SocialMediaAccount
            linkedin_accounts = SocialMediaAccount.objects.filter(
                user=user,
                platform='linkedin'
            )
            
            if linkedin_accounts.exists():
                for account in linkedin_accounts:
                    report_lines.append(f"• Account: {account.username}")
                    report_lines.append(f"  Status: {'Active' if account.is_active else 'Inactive'}")
                    report_lines.append(f"  Created: {account.created_at}")
                    report_lines.append(f"  Token Status: {'Valid' if account.access_token else 'Missing'}")
            else:
                report_lines.append("No LinkedIn accounts found for user")
        except Exception as e:
            report_lines.append(f"Error checking accounts: {str(e)}")
        report_lines.append("")
        
        # Error Analysis
        if error_response:
            report_lines.append("ERROR ANALYSIS:")
            report_lines.append("-" * 40)
            debug_info = self.debug_oauth_error(error_response)
            
            report_lines.append(f"Error: {debug_info['error_code']}")
            report_lines.append(f"Description: {debug_info['error_description']}")
            report_lines.append("")
            
            if debug_info['likely_causes']:
                report_lines.append("Likely Causes:")
                for cause in debug_info['likely_causes']:
                    report_lines.append(f"• {cause}")
                report_lines.append("")
            
            if debug_info['solutions']:
                report_lines.append("Recommended Solutions:")
                for solution in debug_info['solutions']:
                    report_lines.append(f"• {solution}")
                report_lines.append("")
            
            if debug_info['debug_steps']:
                report_lines.append("Debug Steps:")
                for i, step in enumerate(debug_info['debug_steps'], 1):
                    report_lines.append(f"{i}. {step}")
                report_lines.append("")
        
        # Recommendations
        report_lines.extend([
            "GENERAL RECOMMENDATIONS:",
            "-" * 40,
            "1. Verify LinkedIn app settings match exactly:",
            "   - Redirect URI in app config",
            "   - Authorized scopes include 'r_liteprofile' and 'w_member_social'",
            "   - App is in production mode or whitelisted domains set",
            "",
            "2. For 'external member binding' errors:",
            "   - Have user revoke app permissions manually",
            "   - Clear database records and retry",
            "   - Wait 24-48 hours if issue persists",
            "",
            "3. Test with different LinkedIn accounts to isolate issue",
            "",
            "4. Monitor LinkedIn API status: https://status.linkedin.com/",
            "",
            "=" * 80
        ])
        
        return "\n".join(report_lines)


class Command(BaseCommand):
    """Django management command for LinkedIn debugging"""
    help = 'Debug LinkedIn integration issues'
    
    def add_arguments(self, parser):
        parser.add_argument('--user', type=str, help='Username or email to debug')
        parser.add_argument('--clear-tokens', action='store_true', help='Clear existing LinkedIn tokens')
        parser.add_argument('--test-config', action='store_true', help='Test LinkedIn app configuration')
    
    def handle(self, *args, **options):
        debugger = LinkedInDebugger()
        
        if options['test_config']:
            self.stdout.write("Testing LinkedIn app configuration...")
            config = debugger.check_app_configuration()
            
            for key, info in config.items():
                if info['valid']:
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ {key.upper()}: {info['value']}")
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f"✗ {key.upper()}: {info['value']}")
                    )
            
            connectivity = debugger.test_linkedin_api_connectivity()
            if connectivity['success']:
                self.stdout.write(
                    self.style.SUCCESS(f"✓ LinkedIn API connectivity: OK")
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f"✗ LinkedIn API connectivity: {connectivity['error']}")
                )
            return
        
        if options['user']:
            try:
                user = User.objects.get(
                    models.Q(username=options['user']) | 
                    models.Q(email=options['user'])
                )
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"User '{options['user']}' not found")
                )
                return
            
            if options['clear_tokens']:
                from apps.authentication.models import SocialMediaAccount
                deleted_count = SocialMediaAccount.objects.filter(
                    user=user,
                    platform='linkedin'
                ).delete()[0]
                
                self.stdout.write(
                    self.style.SUCCESS(f"Cleared {deleted_count} LinkedIn tokens for {user.username}")
                )
            
            # Generate debug report
            report = debugger.generate_debug_report(user)
            
            # Save to file
            filename = f'linkedin_debug_{user.username}.txt'
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report)
            
            self.stdout.write(report)
            self.stdout.write(
                self.style.SUCCESS(f"\nDebug report saved to: {filename}")
            )
        else:
            self.stdout.write(
                self.style.WARNING("Please specify a user with --user username_or_email")
            )
            self.stdout.write("Available options:")
            self.stdout.write("  --user <username_or_email>  Debug specific user")
            self.stdout.write("  --clear-tokens              Clear LinkedIn tokens for user")
            self.stdout.write("  --test-config               Test app configuration only")
