"""Consolidated rate limit schema refactor.

Combines the rename/removal/addition operations into a single migration to
avoid duplicate rename operations that caused FieldDoesNotExist errors.
Data from old per-hour stats table is dropped (acceptable for refactor).
"""

from django.db import migrations, models
import django.utils.timezone
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_subscriptiontier_gohighlevelintegration_and_more"),
    ]

    operations = [
        # Rename timestamp -> blocked_at
        migrations.RenameField(
            model_name="ratelimitlog",
            old_name="timestamp",
            new_name="blocked_at",
        ),
        # Rename requests_remaining -> requests_in_window to match model
        migrations.RenameField(
            model_name="ratelimitlog",
            old_name="requests_remaining",
            new_name="requests_in_window",
        ),
        migrations.AlterField(
            model_name="ratelimitlog",
            name="blocked_at",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        # Drop old stats model first
        migrations.DeleteModel(name="RateLimitStats"),
        # Create new stats model
        migrations.CreateModel(
            name="RateLimitStats",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                (
                    "period_type",
                    models.CharField(
                        max_length=10,
                        choices=[("hourly", "Hourly"), ("daily", "Daily"), ("weekly", "Weekly")],
                        default="hourly",
                    ),
                ),
                ("period_start", models.DateTimeField(default=django.utils.timezone.now)),
                ("period_end", models.DateTimeField(default=django.utils.timezone.now)),
                ("total_requests", models.BigIntegerField(default=0)),
                ("blocked_requests", models.BigIntegerField(default=0)),
                ("unique_ips", models.IntegerField(default=0)),
                ("unique_users", models.IntegerField(default=0)),
                ("top_blocked_endpoints", models.JSONField(default=list, blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now_add=False, auto_now=True)),
            ],
            options={
                "verbose_name": "Rate Limit Stats",
                "verbose_name_plural": "Rate Limit Stats",
                "ordering": ["-period_start"],
                "unique_together": {("period_type", "period_start")},
            },
        ),
        # Log adjustments
        migrations.RemoveField(model_name="ratelimitlog", name="action"),
        migrations.RemoveField(model_name="ratelimitlog", name="algorithm_used"),
        migrations.RemoveField(model_name="ratelimitlog", name="metadata"),
        migrations.RemoveField(model_name="ratelimitlog", name="user_type"),
        migrations.RemoveIndex(model_name="ratelimitlog", name="core_rateli_timesta_e4f58f_idx"),
        migrations.RemoveIndex(model_name="ratelimitlog", name="core_rateli_user_id_b44c8e_idx"),
        migrations.RemoveIndex(model_name="ratelimitlog", name="core_rateli_ip_addr_33bdf6_idx"),
        migrations.AddField(
            model_name="ratelimitlog",
            name="block_type",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("token_bucket", "Token Bucket"),
                    ("sliding_window", "Sliding Window"),
                    ("both", "Both"),
                ],
                default="both",
            ),
        ),
        migrations.AddField(
            model_name="ratelimitlog",
            name="rule_applied",
            field=models.ForeignKey(null=True, on_delete=models.SET_NULL, to="core.ratelimitrule"),
        ),
        migrations.AddIndex(
            model_name="ratelimitlog",
            index=models.Index(fields=["ip_address", "-blocked_at"], name="core_rateli_ip_addr_e7d153_idx"),
        ),
        migrations.AddIndex(
            model_name="ratelimitlog",
            index=models.Index(fields=["user", "-blocked_at"], name="core_rateli_user_id_95e702_idx"),
        ),
        migrations.AddIndex(
            model_name="ratelimitlog",
            index=models.Index(fields=["endpoint", "-blocked_at"], name="core_rateli_endpoin_32652c_idx"),
        ),
    ]
