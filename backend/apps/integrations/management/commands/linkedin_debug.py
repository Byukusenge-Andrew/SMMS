"""
Management command to help debug and clean up LinkedIn integrations
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.integrations.models import SocialMediaAccount, SocialMediaPlatform

User = get_user_model()


class Command(BaseCommand):
    help = 'Debug and manage LinkedIn integrations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all LinkedIn accounts',
        )
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Remove all LinkedIn accounts',
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Filter by user email or username',
        )

    def handle(self, *args, **options):
        if options['list']:
            self.list_linkedin_accounts(options.get('user'))
        elif options['clean']:
            self.clean_linkedin_accounts(options.get('user'))
        else:
            self.stdout.write(
                self.style.WARNING('Please specify --list or --clean')
            )

    def list_linkedin_accounts(self, user_filter=None):
        """List all LinkedIn accounts"""
        accounts = SocialMediaAccount.objects.filter(
            platform=SocialMediaPlatform.LINKEDIN
        )
        
        if user_filter:
            accounts = accounts.filter(
                models.Q(user__email__icontains=user_filter) |
                models.Q(user__username__icontains=user_filter)
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'Found {accounts.count()} LinkedIn accounts:')
        )
        
        for account in accounts:
            status = "✓ Active" if account.is_active else "✗ Inactive"
            token_status = "✓ Has token" if account.access_token else "✗ No token"
            
            self.stdout.write(
                f"  User: {account.user.email} ({account.user.username})\n"
                f"    Username: {account.username}\n"
                f"    Display Name: {account.display_name}\n"
                f"    Status: {status}\n"
                f"    Token: {token_status}\n"
                f"    Created: {account.created_at}\n"
                f"    ID: {account.id}\n"
            )

    def clean_linkedin_accounts(self, user_filter=None):
        """Remove LinkedIn accounts"""
        accounts = SocialMediaAccount.objects.filter(
            platform=SocialMediaPlatform.LINKEDIN
        )
        
        if user_filter:
            accounts = accounts.filter(
                models.Q(user__email__icontains=user_filter) |
                models.Q(user__username__icontains=user_filter)
            )
        
        count = accounts.count()
        if count == 0:
            self.stdout.write(
                self.style.WARNING('No LinkedIn accounts found to clean')
            )
            return
        
        # List accounts that will be deleted
        self.stdout.write(
            self.style.WARNING(f'Will delete {count} LinkedIn accounts:')
        )
        for account in accounts:
            self.stdout.write(f"  - {account.user.email}: {account.username}")
        
        # Confirm deletion
        confirm = input("Are you sure? (yes/no): ")
        if confirm.lower() == 'yes':
            accounts.delete()
            self.stdout.write(
                self.style.SUCCESS(f'Deleted {count} LinkedIn accounts')
            )
        else:
            self.stdout.write(
                self.style.ERROR('Cancelled')
            )