#!/usr/bin/env python3
"""
Check and create subscription tiers
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from apps.core.models.payment_models import SubscriptionTier
from decimal import Decimal

def check_and_create_tiers():
    print("🔍 CHECKING SUBSCRIPTION TIERS")
    print("=" * 50)
    
    # Check all existing tiers
    existing_tiers = SubscriptionTier.objects.all()
    print(f"Found {existing_tiers.count()} existing subscription tiers:")
    
    for tier in existing_tiers:
        status = "✅ Active" if tier.is_active else "❌ Inactive"
        print(f"   • {tier.name} - ${tier.price_monthly}/month - {status}")
        print(f"     ID: {tier.id}")
        print(f"     Description: {tier.description}")
        print()
    
    # Define the tiers that should exist
    required_tiers = [
        {
            'name': 'Starter',
            'description': 'Perfect for individuals and small creators getting started',
            'price_monthly': Decimal('0.00'),
            'price_yearly': Decimal('0.00'),
            'max_social_accounts': 3,
            'max_posts_per_month': 10,
            'is_active': True
        },
        {
            'name': 'Basic Plan',
            'description': 'Perfect for individuals getting started with social media management',
            'price_monthly': Decimal('7.99'),
            'price_yearly': Decimal('79.90'),
            'max_social_accounts': 3,
            'max_posts_per_month': 30,
            'is_active': True
        },
        {
            'name': 'Professional',
            'description': 'Ideal for professionals and small businesses',
            'price_monthly': Decimal('14.99'),
            'price_yearly': Decimal('149.90'),
            'max_social_accounts': 10,
            'max_posts_per_month': 100,
            'is_active': True
        }
    ]
    
    print("🏗️  CREATING/UPDATING REQUIRED TIERS")
    print("=" * 50)
    
    for tier_data in required_tiers:
        tier, created = SubscriptionTier.objects.get_or_create(
            name=tier_data['name'],
            defaults=tier_data
        )
        
        if created:
            print(f"✅ Created tier: {tier.name}")
        else:
            # Update existing tier to ensure it's active and has correct data
            for key, value in tier_data.items():
                setattr(tier, key, value)
            tier.save()
            print(f"✅ Updated tier: {tier.name}")
        
        print(f"   ID: {tier.id}")
        print(f"   Price: ${tier.price_monthly}/month")
        print(f"   Active: {tier.is_active}")
        print()
    
    print("✅ All required subscription tiers are now available!")

if __name__ == "__main__":
    check_and_create_tiers()
