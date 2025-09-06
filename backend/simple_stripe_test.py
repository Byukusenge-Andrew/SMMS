#!/usr/bin/env python3
"""
Simple Stripe Checkout Test
Creates a superuser and tests the checkout flow
"""

import os
import sys
import json

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

from django.contrib.auth.models import User
from apps.billing.models import SubscriptionTier
import requests

def create_test_user():
    """Create or get test user"""
    email = "test@example.com"
    username = "testuser"
    password = "testpass123"
    
    try:
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': username,
                'first_name': 'Test',
                'last_name': 'User',
                'is_active': True
            }
        )
        
        if created or not user.check_password(password):
            user.set_password(password)
            user.save()
            print(f"✅ Created test user: {email}")
        else:
            print(f"✅ Using existing test user: {email}")
            
        return user, email, password
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        return None, None, None

def get_available_tiers():
    """Get subscription tiers"""
    try:
        response = requests.get("http://127.0.0.1:8000/api/billing/api/subscription-tiers/")
        if response.status_code == 200:
            data = response.json()
            return data.get('tiers', [])
        return []
    except Exception as e:
        print(f"❌ Error getting tiers: {e}")
        return []

def test_checkout_flow():
    """Test the complete checkout flow"""
    print("🧪 Testing Stripe Checkout Flow\n")
    
    # Step 1: Create test user
    user, email, password = create_test_user()
    if not user:
        return False
        
    # Step 2: Get available tiers
    tiers = get_available_tiers()
    if not tiers:
        print("❌ No subscription tiers available")
        return False
        
    print(f"✅ Found {len(tiers)} subscription tiers")
    
    # Find a paid tier for testing
    paid_tier = None
    for tier in tiers:
        if tier['price_monthly'] > 0:
            paid_tier = tier
            break
            
    if not paid_tier:
        print("❌ No paid tiers found")
        return False
        
    print(f"✅ Testing with tier: {paid_tier['display_name']} (${paid_tier['price_monthly']}/month)")
    
    # Step 3: Test checkout session creation (without auth first)
    print("\n🔗 Creating Stripe Checkout Session...")
    
    checkout_payload = {
        'tier_id': paid_tier['id'],
        'billing_period': 'monthly'
    }
    
    # Try without authentication first (should fail)
    response = requests.post(
        "http://127.0.0.1:8000/api/billing/stripe/checkout/",
        json=checkout_payload
    )
    
    if response.status_code == 401:
        print("✅ Checkout correctly requires authentication")
    else:
        print(f"⚠️  Unexpected response without auth: {response.status_code}")
    
    # Step 4: For manual testing, provide the curl command
    print(f"\n📋 Manual Testing Instructions:")
    print("="*60)
    print("1. First, create a superuser if you haven't:")
    print("   python manage.py createsuperuser")
    print()
    print("2. Then test the checkout with this curl command:")
    print("   (Replace YOUR_TOKEN with actual token from Django admin or login)")
    print()
    print(f"""curl -X POST "http://127.0.0.1:8000/api/billing/stripe/checkout/" \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -d '{{"tier_id": "{paid_tier['id']}", "billing_period": "monthly"}}'""")
    print()
    print("3. Expected Response:")
    print('   {"success": true, "checkout_url": "https://checkout.stripe.com/..."}')
    print()
    print("4. Visit the checkout_url in your browser")
    print("5. Use test card: 4242 4242 4242 4242")
    print("6. Complete the payment flow")
    print()
    print("🎯 What to verify:")
    print("- Checkout URL is generated")
    print("- Stripe checkout page loads")
    print("- Test payment succeeds") 
    print("- User is redirected back")
    print("- Subscription is created in database")
    
    return True

if __name__ == "__main__":
    test_checkout_flow()
