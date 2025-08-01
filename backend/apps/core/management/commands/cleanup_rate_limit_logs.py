"""
Management command to clean up old rate limiting logs and generate statistics
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Avg, Count, Max
from django.utils import timezone

from apps.core.models import RateLimitLog, RateLimitStats


class Command(BaseCommand):
    help = "Clean up old rate limiting logs and generate hourly statistics"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Number of days to keep logs (default: 30)",
        )
        parser.add_argument(
            "--generate-stats",
            action="store_true",
            help="Generate statistics for the last 24 hours",
        )

    def handle(self, *args, **options):
        days_to_keep = options["days"]
        generate_stats = options["generate_stats"]

        # Clean up old logs
        cutoff_date = timezone.now() - timedelta(days=days_to_keep)
        deleted_count = RateLimitLog.objects.filter(timestamp__lt=cutoff_date).delete()[0]

        self.stdout.write(
            self.style.SUCCESS(f"Deleted {deleted_count} old rate limiting logs (older than {days_to_keep} days)")
        )

        # Generate statistics if requested
        if generate_stats:
            self._generate_hourly_stats()

    def _generate_hourly_stats(self):
        """Generate hourly statistics for the last 24 hours"""
        now = timezone.now()
        start_time = now - timedelta(hours=24)

        # Process each hour
        for hour_offset in range(24):
            hour_start = start_time + timedelta(hours=hour_offset)
            hour_end = hour_start + timedelta(hours=1)

            # Get logs for this hour
            hour_logs = RateLimitLog.objects.filter(timestamp__gte=hour_start, timestamp__lt=hour_end)

            if not hour_logs.exists():
                continue

            # Calculate statistics
            total_requests = hour_logs.count()
            allowed_requests = hour_logs.filter(action="allowed").count()
            denied_requests = hour_logs.filter(action="denied").count()
            burst_protections = hour_logs.filter(action="burst_protection").count()

            # By user type
            anonymous_requests = hour_logs.filter(user_type="anonymous").count()
            authenticated_requests = hour_logs.filter(user_type="authenticated").count()
            premium_requests = hour_logs.filter(user_type="premium").count()
            admin_requests = hour_logs.filter(user_type="admin").count()

            # Performance metrics
            avg_tokens = hour_logs.aggregate(avg=Avg("tokens_remaining"))["avg"] or 0.0

            avg_requests = hour_logs.aggregate(avg=Avg("requests_remaining"))["avg"] or 0.0

            # Create or update stats record
            stats, created = RateLimitStats.objects.get_or_create(
                date=hour_start.date(),
                hour=hour_start.hour,
                defaults={
                    "total_requests": total_requests,
                    "allowed_requests": allowed_requests,
                    "denied_requests": denied_requests,
                    "burst_protections": burst_protections,
                    "anonymous_requests": anonymous_requests,
                    "authenticated_requests": authenticated_requests,
                    "premium_requests": premium_requests,
                    "admin_requests": admin_requests,
                    "average_tokens_remaining": avg_tokens,
                    "average_requests_remaining": avg_requests,
                    "peak_requests_per_minute": 0,  # TODO: Calculate this
                },
            )

            if not created:
                # Update existing record
                stats.total_requests = total_requests
                stats.allowed_requests = allowed_requests
                stats.denied_requests = denied_requests
                stats.burst_protections = burst_protections
                stats.anonymous_requests = anonymous_requests
                stats.authenticated_requests = authenticated_requests
                stats.premium_requests = premium_requests
                stats.admin_requests = admin_requests
                stats.average_tokens_remaining = avg_tokens
                stats.average_requests_remaining = avg_requests
                stats.save()

            action = "Created" if created else "Updated"
            self.stdout.write(
                f'{action} stats for {hour_start.strftime("%Y-%m-%d %H:00")}: '
                f"{total_requests} requests, {denied_requests} denied"
            )

        self.stdout.write(self.style.SUCCESS("Successfully generated hourly statistics"))
