#!/usr/bin/env python
"""
Update subscription tiers with Stripe price IDs
"""

import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from apps.core.models.payment_models import SubscriptionTier

def update_stripe_price_ids():
    """Update subscription tiers with example Stripe price IDs"""
    
    # Professional tier - $29/month
    try:
        professional = SubscriptionTier.objects.get(name='professional')
        professional.stripe_price_id_monthly = 'price_keativ_professional_monthly'  # Replace with actual Stripe price ID
        professional.stripe_price_id_yearly = 'price_keativ_professional_yearly'    # Replace with actual Stripe price ID
        professional.save()
        print(f"Updated {professional.display_name}: monthly={professional.stripe_price_id_monthly}")
    except SubscriptionTier.DoesNotExist:
        print("Professional tier not found")
    
    # Enterprise tier - $99/month
    try:
        enterprise = SubscriptionTier.objects.get(name='enterprise')
        enterprise.stripe_price_id_monthly = 'price_keativ_enterprise_monthly'     # Replace with actual Stripe price ID
        enterprise.stripe_price_id_yearly = 'price_keativ_enterprise_yearly'       # Replace with actual Stripe price ID
        enterprise.save()
        print(f"Updated {enterprise.display_name}: monthly={enterprise.stripe_price_id_monthly}")
    except SubscriptionTier.DoesNotExist:
        print("Enterprise tier not found")
    
    # Free tier doesn't need price IDs
    try:
        free = SubscriptionTier.objects.get(name='free')
        print(f"Free tier: {free.display_name} - No price IDs needed")
    except SubscriptionTier.DoesNotExist:
        print("Free tier not found")
    
    print("\nAll subscription tiers:")
    for tier in SubscriptionTier.objects.all():
        print(f"- {tier.display_name} ({tier.name}): ${tier.price_monthly}/month")
        if tier.stripe_price_id_monthly:
            print(f"  Monthly Price ID: {tier.stripe_price_id_monthly}")
        if tier.stripe_price_id_yearly:
            print(f"  Yearly Price ID: {tier.stripe_price_id_yearly}")
        print()

if __name__ == '__main__':
    update_stripe_price_ids()
