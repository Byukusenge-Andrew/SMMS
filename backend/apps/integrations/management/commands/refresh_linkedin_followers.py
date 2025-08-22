"""
Management command to refresh LinkedIn follower counts
"""

import logging
from django.core.management.base import BaseCommand
from apps.integrations.models import SocialMediaAccount, SocialMediaPlatform
from apps.integrations.social_media_integrator import LinkedInIntegrator

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Refresh LinkedIn follower counts for all connected accounts'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='Refresh only for specific user ID',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
    
    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        user_id = options.get('user_id')
        
        # Get LinkedIn accounts
        queryset = SocialMediaAccount.objects.filter(
            platform=SocialMediaPlatform.LINKEDIN,
            is_active=True
        )
        
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        accounts = list(queryset)
        
        if not accounts:
            self.stdout.write(
                self.style.WARNING('No active LinkedIn accounts found')
            )
            return
        
        self.stdout.write(f'Found {len(accounts)} LinkedIn accounts to update')
        
        linkedin_integrator = LinkedInIntegrator()
        updated_count = 0
        
        for account in accounts:
            try:
                if dry_run:
                    self.stdout.write(f'[DRY RUN] Would update account: {account.username} (User: {account.user.email})')
                    continue
                
                # Get profile and prefer LinkedIn connection count
                result = linkedin_integrator.get_profile(account.access_token)
                
                if result.get('success'):
                    profile = result.get('profile', {})
                    new_connection_count = profile.get('connection_count', profile.get('follower_count', 0))
                    old_connection_count = account.followers_count or 0
                    
                    if new_connection_count != old_connection_count:
                        account.followers_count = new_connection_count
                        account.save(update_fields=['followers_count'])
                        
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Updated {account.username}: {old_connection_count} → {new_connection_count} connections'
                            )
                        )
                        updated_count += 1
                    else:
                        self.stdout.write(f'No change for {account.username}: {old_connection_count} connections')
                else:
                    error_msg = result.get('error', 'Unknown error')
                    self.stdout.write(
                        self.style.ERROR(f'Failed to update {account.username}: {error_msg}')
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error updating {account.username}: {str(e)}')
                )
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully updated {updated_count} LinkedIn accounts')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'[DRY RUN] Would update {len(accounts)} LinkedIn accounts')
            )
