"""
Django management command to clean up old digit-based folders in Supabase
Run this AFTER successfully migrating to UUID-based structure and verifying everything works
"""

from django.core.management.base import BaseCommand, CommandError
from apps.core.supabase_uuid_utils import SupabaseUUIDMigrator
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clean up old digit-based folders in Supabase after UUID migration'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform a dry run without actually deleting files',
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='Clean up files for specific user ID only',
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm you want to delete the old files (required for actual deletion)',
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
        confirm = options['confirm']
        
        if not dry_run and not confirm:
            raise CommandError(
                "You must use --confirm flag to actually delete files. "
                "Use --dry-run to see what would be deleted first."
            )
        
        migrator = SupabaseUUIDMigrator()
        
        if not migrator.storage.client:
            raise CommandError("Supabase client not configured. Check your settings.")
        
        self.stdout.write(
            self.style.WARNING(f"Starting cleanup of old digit-based folders (dry_run={dry_run})")
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING("This is a DRY RUN - no files will be actually deleted")
            )
        else:
            self.stdout.write(
                self.style.ERROR("WARNING: This will PERMANENTLY DELETE old files!")
            )
        
        try:
            if user_id:
                # Clean up specific user
                self._cleanup_user_files(migrator, str(user_id), dry_run)
            else:
                # Clean up all users
                mapping = migrator.get_user_uuid_mapping()
                total_deleted = 0
                
                for user_digit_id in mapping.keys():
                    deleted = self._cleanup_user_files(migrator, user_digit_id, dry_run)
                    total_deleted += deleted
                
                self.stdout.write(
                    self.style.SUCCESS(f"Cleanup completed. Total files processed: {total_deleted}")
                )
                
        except Exception as e:
            raise CommandError(f"Cleanup failed: {str(e)}")
    
    def _cleanup_user_files(self, migrator, user_digit_id: str, dry_run: bool) -> int:
        """Clean up files for a specific user"""
        try:
            files = migrator.list_user_files(user_digit_id)
            
            if not files:
                self.stdout.write(f"No files found for user {user_digit_id}")
                return 0
            
            self.stdout.write(f"Found {len(files)} files for user {user_digit_id}")
            
            deleted_count = 0
            for file_path in files:
                if dry_run:
                    self.stdout.write(f"[DRY RUN] Would delete: {file_path}")
                    deleted_count += 1
                else:
                    try:
                        response = migrator.storage.client.storage.from_(
                            migrator.storage.bucket_name
                        ).remove([file_path])
                        
                        if hasattr(response, 'error') and response.error:
                            self.stdout.write(
                                self.style.ERROR(f"Error deleting {file_path}: {response.error}")
                            )
                        else:
                            self.stdout.write(f"Deleted: {file_path}")
                            deleted_count += 1
                            
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"Error deleting {file_path}: {e}")
                        )
            
            return deleted_count
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error cleaning up user {user_digit_id}: {e}")
            )
            return 0