#!/usr/bin/env python3
"""
Create Stripe prices for the subscription tiers
"""

import stripe
import os
import sys
import django
from decimal import Decimal

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from django.conf import settings
from apps.core.models.payment_models import SubscriptionTier

# Set your Stripe secret key
stripe.api_key = settings.STRIPE_SECRET_KEY

def create_stripe_prices():
    """Create Stripe prices for each product"""
    
    # Your existing product IDs from Stripe
    products = {
        'basic': 'prod_Sz0AbTVu3hHRht',      # Basic plan
        'pro': 'prod_Sz0A4zh4XGVdNI',        # professional  
        'enterprise': 'prod_Sz0Buj9mERDy7W', # Enterprise
    }
    
    prices = {
        'basic': {'amount': 799, 'display': '$7.99'},        # $7.99 in cents
        'pro': {'amount': 1499, 'display': '$14.99'},       # $14.99 in cents
        'enterprise': {'amount': 1999, 'display': '$19.99'} # $19.99 in cents
    }
    
    created_prices = {}
    
    print("Creating Stripe prices...")
    
    for tier_name, product_id in products.items():
        try:
            # Create monthly price
            monthly_price = stripe.Price.create(
                product=product_id,
                unit_amount=prices[tier_name]['amount'],
                currency='usd',
                recurring={'interval': 'month'},
                lookup_key=f'{tier_name}_monthly',
                nickname=f'{tier_name.title()} Monthly'
            )
            
            created_prices[f'{tier_name}_monthly'] = monthly_price.id
            print(f"✓ Created {tier_name.title()} monthly price: {monthly_price.id} ({prices[tier_name]['display']}/month)")
            
            # Create yearly price (with 2 months free discount)
            yearly_amount = prices[tier_name]['amount'] * 10  # 10 months instead of 12
            yearly_price = stripe.Price.create(
                product=product_id,
                unit_amount=yearly_amount,
                currency='usd',
                recurring={'interval': 'year'},
                lookup_key=f'{tier_name}_yearly',
                nickname=f'{tier_name.title()} Yearly'
            )
            
            created_prices[f'{tier_name}_yearly'] = yearly_price.id
            print(f"✓ Created {tier_name.title()} yearly price: {yearly_price.id} (${yearly_amount/100:.2f}/year)")
            
        except stripe.error.StripeError as e:
            print(f"✗ Error creating price for {tier_name}: {e}")
    
    return created_prices

def update_django_tiers(price_ids):
    """Update Django subscription tiers with Stripe price IDs"""
    
    tier_data = {
        'basic': {
            'name': 'basic',
            'display_name': 'Basic Plan',
            'description': 'Perfect for individuals getting started with social media management',
            'price_monthly': Decimal('7.99'),
            'price_yearly': Decimal('79.90'),
            'max_social_accounts': 3,
            'max_scheduled_posts': 30,
            'max_team_members': 1,
            'analytics_retention_days': 30,
            'api_rate_limit': 1000,
        },
        'pro': {
            'name': 'pro',
            'display_name': 'Professional',
            'description': 'Ideal for professionals and small businesses',
            'price_monthly': Decimal('14.99'),
            'price_yearly': Decimal('149.90'),
            'max_social_accounts': 10,
            'max_scheduled_posts': 100,
            'max_team_members': 3,
            'analytics_retention_days': 90,
            'api_rate_limit': 5000,
            'gohighlevel_integration': True,
            'advanced_analytics': True,
            'priority_support': True,
            'custom_branding': True,
            'bulk_upload_scheduling': True,
            'hashtag_suggestions': True,
            'best_time_insights': True,
            'approval_workflows': True,
            'two_factor_auth': True,
            'custom_integrations': True,
        },
        'enterprise': {
            'name': 'enterprise',
            'display_name': 'Enterprise',
            'description': 'For large teams and agencies with advanced needs',
            'price_monthly': Decimal('19.99'),
            'price_yearly': Decimal('199.90'),
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
        },
    }
    
    print("\nUpdating Django subscription tiers...")
    
    for tier_name, data in tier_data.items():
        # Add Stripe price IDs
        data['stripe_price_id_monthly'] = price_ids.get(f'{tier_name}_monthly', '')
        data['stripe_price_id_yearly'] = price_ids.get(f'{tier_name}_yearly', '')
        data['is_active'] = True
        
        tier, created = SubscriptionTier.objects.update_or_create(
            name=tier_name,
            defaults=data
        )
        
        action = "Created" if created else "Updated"
        print(f"✓ {action} {tier.display_name}")
        print(f"  Monthly: {tier.stripe_price_id_monthly}")
        print(f"  Yearly: {tier.stripe_price_id_yearly}")

def main():
    print("Setting up Stripe subscriptions for Keativ...")
    print("=" * 50)
    
    # Create prices in Stripe
    price_ids = create_stripe_prices()
    
    if price_ids:
        # Update Django models
        update_django_tiers(price_ids)
        
        print("\n" + "=" * 50)
        print("✓ Setup complete!")
        print("\nNext steps:")
        print("1. Test the checkout flow")
        print("2. Set up webhook endpoints")
        print("3. Test with Stripe test cards")
        
        print("\nStripe Price IDs created:")
        for name, price_id in price_ids.items():
            print(f"  {name}: {price_id}")
    else:
        print("✗ Failed to create prices. Check your Stripe configuration.")

if __name__ == '__main__':
    main()
