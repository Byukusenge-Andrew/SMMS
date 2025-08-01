"""
Management command to create default rate limiting rules
"""

from django.core.management.base import BaseCommand

from apps.core.models import RateLimitRule


class Command(BaseCommand):
    help = "Create default rate limiting rules for different user types"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force creation even if rules already exist",
        )

    def handle(self, *args, **options):
        force = options["force"]

        # Default rules configuration
        default_rules = [
            {
                "name": "Anonymous Users Default",
                "user_type": "anonymous",
                "algorithm": "both",
                "bucket_capacity": 10,
                "refill_rate": 0.1,
                "max_requests": 20,
                "window_size": 3600,
            },
            {
                "name": "Authenticated Users Default",
                "user_type": "authenticated",
                "algorithm": "both",
                "bucket_capacity": 100,
                "refill_rate": 1.0,
                "max_requests": 1000,
                "window_size": 3600,
            },
            {
                "name": "Premium Users Default",
                "user_type": "premium",
                "algorithm": "both",
                "bucket_capacity": 500,
                "refill_rate": 5.0,
                "max_requests": 10000,
                "window_size": 3600,
            },
            {
                "name": "Admin Users Default",
                "user_type": "admin",
                "algorithm": "both",
                "bucket_capacity": 1000,
                "refill_rate": 10.0,
                "max_requests": 50000,
                "window_size": 3600,
            },
        ]

        created_count = 0
        updated_count = 0

        for rule_data in default_rules:
            user_type = rule_data["user_type"]

            # Check if rule already exists
            existing_rule = RateLimitRule.objects.filter(user_type=user_type, is_active=True).first()

            if existing_rule and not force:
                self.stdout.write(self.style.WARNING(f"Rule for {user_type} already exists. Use --force to update."))
                continue

            if existing_rule and force:
                # Update existing rule
                for key, value in rule_data.items():
                    setattr(existing_rule, key, value)
                existing_rule.save()
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(f"Updated rate limit rule for {user_type}"))
            else:
                # Create new rule
                RateLimitRule.objects.create(**rule_data)
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Created rate limit rule for {user_type}"))

        self.stdout.write(
            self.style.SUCCESS(f"Successfully created {created_count} and updated {updated_count} rate limit rules.")
        )
