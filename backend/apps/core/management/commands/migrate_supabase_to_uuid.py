"""
Django management command to migrate Supabase storage from digit IDs to UUIDs
"""

from django.core.management.base import BaseCommand, CommandError
from apps.core.supabase_uuid_utils import SupabaseUUIDMigrator
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Migrate Supabase storage files from user digit IDs to UUIDs'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform a dry run without actually copying files',
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='Migrate files for specific user ID only',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose logging',
        )
    
    def handle(self, *args, **options):
        if options['verbose']:
            logging.basicConfig(level=logging.INFO)
            
        dry_run = options['dry_run']
        user_id = options.get('user_id')
        
        migrator = SupabaseUUIDMigrator()
        
        if not migrator.storage.client:
            raise CommandError("Supabase client not configured. Check your settings.")
        
        self.stdout.write(
            self.style.WARNING(f"Starting Supabase UUID migration (dry_run={dry_run})")
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING("This is a DRY RUN - no files will be actually copied")
            )
        
        try:
            if user_id:
                # Migrate specific user
                mapping = migrator.get_user_uuid_mapping()
                user_digit_id = str(user_id)
                
                if user_digit_id not in mapping:
                    raise CommandError(f"User {user_id} not found or has no profile")
                
                user_uuid = mapping[user_digit_id]
                self.stdout.write(f"Migrating user {user_digit_id} -> {user_uuid}")
                
                results = migrator.migrate_user_files(user_digit_id, user_uuid, dry_run)
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"User {user_id} migration completed: "
                        f"Success: {results['success']}, "
                        f"Failed: {results['failed']}, "
                        f"Skipped: {results['skipped']}"
                    )
                )
            else:
                # Migrate all users
                results = migrator.migrate_all_users(dry_run)
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Migration completed for {results['users_processed']} users: "
                        f"Total Success: {results['total_success']}, "
                        f"Total Failed: {results['total_failed']}, "
                        f"Total Skipped: {results['total_skipped']}"
                    )
                )
                
        except Exception as e:
            raise CommandError(f"Migration failed: {str(e)}")
        
        if not dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "Migration completed! Remember to:\n"
                    "1. Update your Supabase RLS policies to use UUIDs\n"
                    "2. Test file access with the new structure\n"
                    "3. Consider cleaning up old digit-based folders"
                )
            )