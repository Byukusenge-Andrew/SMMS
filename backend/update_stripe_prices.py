#!/usr/bin/env python
"""
Script to update subscription tiers with Stripe price IDs
Run this after creating prices in Stripe dashboard
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

def update_stripe_prices():
    """Update subscription tiers with Stripe price IDs"""
    
    # TODO: Replace these with your actual Stripe price IDs after creating them
    # You'll get these from your Stripe dashboard after creating the prices
    stripe_prices = {
        'basic': {
            'monthly': 'price_REPLACE_WITH_BASIC_MONTHLY_PRICE_ID',
            'yearly': 'price_REPLACE_WITH_BASIC_YEARLY_PRICE_ID'
        },
        'pro': {
            'monthly': 'price_REPLACE_WITH_PRO_MONTHLY_PRICE_ID', 
            'yearly': 'price_REPLACE_WITH_PRO_YEARLY_PRICE_ID'
        },
        'enterprise': {
            'monthly': 'price_REPLACE_WITH_ENTERPRISE_MONTHLY_PRICE_ID',
            'yearly': 'price_REPLACE_WITH_ENTERPRISE_YEARLY_PRICE_ID'
        }
    }
    
    # Create/update subscription tiers
    tiers = [
        {
            'name': 'basic',
            'display_name': 'Basic Plan',
            'description': 'Perfect for individuals getting started with social media management',
            'price_monthly': Decimal('7.99'),
            'price_yearly': Decimal('79.90'),  # ~2 months free
            'stripe_price_id_monthly': stripe_prices['basic']['monthly'],
            'stripe_price_id_yearly': stripe_prices['basic']['yearly'],
            'max_social_accounts': 3,
            'max_scheduled_posts': 30,
            'max_team_members': 1,
            'analytics_retention_days': 30,
            'api_rate_limit': 1000,
            'gohighlevel_integration': False,
            'advanced_analytics': False,
            'priority_support': False,
            'white_label': False,
            'custom_branding': False,
            'bulk_upload_scheduling': True,
            'hashtag_suggestions': True,
            'best_time_insights': False,
            'approval_workflows': False,
            'sso_support': False,
            'two_factor_auth': True,
            'custom_integrations': False,
            'phone_support': False,
            'dedicated_account_manager': False,
            'is_active': True,
        },
        {
            'name': 'pro',
            'display_name': 'Professional',
            'description': 'Ideal for professionals and small businesses',
            'price_monthly': Decimal('14.99'),
            'price_yearly': Decimal('149.90'),  # ~2 months free
            'stripe_price_id_monthly': stripe_prices['pro']['monthly'],
            'stripe_price_id_yearly': stripe_prices['pro']['yearly'],
            'max_social_accounts': 10,
            'max_scheduled_posts': 100,
            'max_team_members': 3,
            'analytics_retention_days': 90,
            'api_rate_limit': 5000,
            'gohighlevel_integration': True,
            'advanced_analytics': True,
            'priority_support': True,
            'white_label': False,
            'custom_branding': True,
            'bulk_upload_scheduling': True,
            'hashtag_suggestions': True,
            'best_time_insights': True,
            'approval_workflows': True,
            'sso_support': False,
            'two_factor_auth': True,
            'custom_integrations': True,
            'phone_support': False,
            'dedicated_account_manager': False,
            'is_active': True,
        },
        {
            'name': 'enterprise',
            'display_name': 'Enterprise',
            'description': 'For large teams and agencies with advanced needs',
            'price_monthly': Decimal('19.99'),
            'price_yearly': Decimal('199.90'),  # ~2 months free
            'stripe_price_id_monthly': stripe_prices['enterprise']['monthly'],
            'stripe_price_id_yearly': stripe_prices['enterprise']['yearly'],
            'max_social_accounts': -1,  # Unlimited
            'max_scheduled_posts': -1,  # Unlimited
            'max_team_members': -1,     # Unlimited
            'analytics_retention_days': 365,
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
    
    updated_count = 0
    for tier_data in tiers:
        tier, created = SubscriptionTier.objects.update_or_create(
            name=tier_data['name'],
            defaults=tier_data
        )
        if created:
            updated_count += 1
            print(f"✓ Created subscription tier: {tier.display_name}")
        else:
            updated_count += 1
            print(f"✓ Updated subscription tier: {tier.display_name}")
        
        print(f"  - Monthly price: ${tier.price_monthly}")
        print(f"  - Stripe monthly price ID: {tier.stripe_price_id_monthly}")
    
    print(f"\nProcessed {updated_count} subscription tiers.")
    
    # Show current tiers
    print("\nCurrent subscription tiers:")
    for tier in SubscriptionTier.objects.all().order_by('price_monthly'):
        print(f"- {tier.display_name}: ${tier.price_monthly}/month")
        print(f"  Stripe monthly ID: {tier.stripe_price_id_monthly}")
        print(f"  Stripe yearly ID: {tier.stripe_price_id_yearly}")

if __name__ == '__main__':
    print("Updating subscription tiers with Stripe price IDs...")
    print("Note: Make sure to replace the placeholder price IDs with your actual Stripe price IDs")
    print()
    update_stripe_prices()
