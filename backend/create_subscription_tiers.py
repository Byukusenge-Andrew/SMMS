#!/usr/bin/env python
"""
Script to create default subscription tiers for the SMMS platform
"""

import os
import sys
import django
from decimal import Decimal

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from apps.core.models.payment_models import SubscriptionTier

def create_subscription_tiers():
    """Create default subscription tiers"""
    
    tiers = [
        {
            'name': 'free',
            'display_name': 'Starter',
            'description': 'Perfect for individuals and small creators getting started',
            'price_monthly': Decimal('0.00'),
            'price_yearly': Decimal('0.00'),
            'max_social_accounts': 3,
            'max_scheduled_posts': 10,
            'max_team_members': 1,
            'analytics_retention_days': 30,
            'api_rate_limit': 1000,
            'gohighlevel_integration': False,
            'advanced_analytics': False,
            'priority_support': False,
            'white_label': False,
            'custom_branding': False,
            'bulk_upload_scheduling': False,
            'hashtag_suggestions': False,
            'best_time_insights': False,
            'approval_workflows': False,
            'sso_support': False,
            'two_factor_auth': False,
            'custom_integrations': False,
            'phone_support': False,
            'dedicated_account_manager': False,
            'is_active': True,
        },
        {
            'name': 'professional',
            'display_name': 'Professional',
            'description': 'For growing businesses and marketing teams',
            'price_monthly': Decimal('29.00'),
            'price_yearly': Decimal('290.00'),  # 2 months free
            'max_social_accounts': -1,  # Unlimited
            'max_scheduled_posts': -1,  # Unlimited
            'max_team_members': 5,
            'analytics_retention_days': 365,
            'api_rate_limit': 5000,
            'gohighlevel_integration': False,
            'advanced_analytics': True,
            'priority_support': True,
            'white_label': False,
            'custom_branding': True,
            'bulk_upload_scheduling': True,
            'hashtag_suggestions': True,
            'best_time_insights': True,
            'approval_workflows': False,
            'sso_support': False,
            'two_factor_auth': True,
            'custom_integrations': False,
            'phone_support': False,
            'dedicated_account_manager': False,
            'is_active': True,
        },
        {
            'name': 'enterprise',
            'display_name': 'Enterprise',
            'description': 'For large organizations with advanced needs',
            'price_monthly': Decimal('99.00'),
            'price_yearly': Decimal('990.00'),  # 2 months free
            'max_social_accounts': -1,  # Unlimited
            'max_scheduled_posts': -1,  # Unlimited
            'max_team_members': -1,  # Unlimited
            'analytics_retention_days': -1,  # Unlimited
            'api_rate_limit': 20000,
            'gohighlevel_integration': True,
            'advanced_analytics': True,
            'priority_support': True,
            'white_label': True,
            'custom_branding': True,
            'bulk_upload_scheduling': True,
            'hashtag_suggestions': True,
            'best_time_insights': True,
            'approval_workflows': True,
            'sso_support': True,
            'two_factor_auth': True,
            'custom_integrations': True,
            'phone_support': True,
            'dedicated_account_manager': True,
            'is_active': True,
        },
    ]
    
    created_count = 0
    for tier_data in tiers:
        tier, created = SubscriptionTier.objects.get_or_create(
            name=tier_data['name'],
            defaults=tier_data
        )
        if created:
            created_count += 1
            print(f"✓ Created subscription tier: {tier.display_name}")
        else:
            print(f"- Subscription tier already exists: {tier.display_name}")
    
    print(f"\nCreated {created_count} new subscription tiers.")
    print("Subscription tiers setup complete!")

if __name__ == '__main__':
    create_subscription_tiers()
