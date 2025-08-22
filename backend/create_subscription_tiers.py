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
            'display_name': 'Free Plan',
            'description': 'Basic social media management for individuals',
            'price_monthly': Decimal('0.00'),
            'price_yearly': Decimal('0.00'),
            'max_social_accounts': 2,
            'max_scheduled_posts': 10,
            'max_team_members': 1,
            'analytics_retention_days': 30,
            'api_rate_limit': 100,
            'gohighlevel_integration': False,
            'advanced_analytics': False,
            'priority_support': False,
            'white_label': False,
            'is_active': True,
        },
        {
            'name': 'basic',
            'display_name': 'Basic Plan',
            'description': 'Enhanced features for small businesses',
            'price_monthly': Decimal('29.99'),
            'price_yearly': Decimal('299.99'),
            'max_social_accounts': 5,
            'max_scheduled_posts': 100,
            'max_team_members': 3,
            'analytics_retention_days': 90,
            'api_rate_limit': 500,
            'gohighlevel_integration': False,
            'advanced_analytics': True,
            'priority_support': False,
            'white_label': False,
            'is_active': True,
        },
        {
            'name': 'professional',
            'display_name': 'Professional Plan',
            'description': 'Advanced features with GoHighLevel integration',
            'price_monthly': Decimal('79.99'),
            'price_yearly': Decimal('799.99'),
            'max_social_accounts': 15,
            'max_scheduled_posts': 500,
            'max_team_members': 10,
            'analytics_retention_days': 365,
            'api_rate_limit': 2000,
            'gohighlevel_integration': True,
            'advanced_analytics': True,
            'priority_support': True,
            'white_label': False,
            'is_active': True,
        },
        {
            'name': 'enterprise',
            'display_name': 'Enterprise Plan',
            'description': 'Complete solution with white-label options',
            'price_monthly': Decimal('199.99'),
            'price_yearly': Decimal('1999.99'),
            'max_social_accounts': -1,  # Unlimited
            'max_scheduled_posts': -1,  # Unlimited
            'max_team_members': -1,  # Unlimited
            'analytics_retention_days': -1,  # Unlimited
            'api_rate_limit': 10000,
            'gohighlevel_integration': True,
            'advanced_analytics': True,
            'priority_support': True,
            'white_label': True,
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
