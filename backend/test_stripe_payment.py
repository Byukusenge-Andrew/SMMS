#!/usr/bin/env python3
"""
Stripe Payment Integration Test Script
Tests all the production Stripe endpoints we created
"""

import requests
import json
import sys
import os

# Add the Django project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')

import django
django.setup()

from django.contrib.auth.models import User
from apps.billing.models import SubscriptionTier, UserSubscription

# Test configuration
BASE_URL = "http://127.0.0.1:8000"
TEST_USER_EMAIL = "test@example.com"
TEST_PASSWORD = "testpass123"

def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_result(test_name, success, message=""):
    """Print test result"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} - {test_name}")
    if message:
        print(f"    {message}")

def create_test_user():
    """Create a test user for authentication"""
    try:
        user, created = User.objects.get_or_create(
            email=TEST_USER_EMAIL,
            defaults={
                'username': TEST_USER_EMAIL,
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        if created:
            user.set_password(TEST_PASSWORD)
            user.save()
        return user
    except Exception as e:
        print(f"Error creating test user: {e}")
        return None

def get_auth_token():
    """Get authentication token for test user"""
    try:
        # First ensure user exists
        user = create_test_user()
        if not user:
            return None
            
        # Try different login payload formats
        login_payloads = [
            {'username': TEST_USER_EMAIL, 'password': TEST_PASSWORD},
            {'email': TEST_USER_EMAIL, 'password': TEST_PASSWORD},
        ]
        
        for payload in login_payloads:
            response = requests.post(f"{BASE_URL}/api/auth/login/", payload)
            
            if response.status_code == 200:
                data = response.json()
                token = data.get('access_token') or data.get('token') or data.get('access')
                if token:
                    return token
            elif response.status_code != 400:
                print(f"Login attempt failed: {response.status_code} - {response.text}")
        
        # Try token endpoint
        response = requests.post(f"{BASE_URL}/api/auth/token/", {
            'username': TEST_USER_EMAIL,
            'password': TEST_PASSWORD
        })
        
        if response.status_code == 200:
            data = response.json()
            return data.get('access') or data.get('token')
        
        print(f"All login attempts failed. Creating superuser for testing...")
        return None
        
    except Exception as e:
        print(f"Error getting auth token: {e}")
        return None

def test_subscription_tiers():
    """Test the subscription tiers endpoint"""
    print_section("Testing Subscription Tiers Endpoint")
    
    try:
        response = requests.get(f"{BASE_URL}/api/billing/api/subscription-tiers/")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('tiers'):
                tiers = data['tiers']
                print_result("Subscription Tiers List", True, f"Found {len(tiers)} tiers")
                
                # Display tier information
                for tier in tiers:
                    print(f"    📦 {tier['display_name']}: ${tier['price_monthly']}/month, ${tier['price_yearly']}/year")
                    
                return True
            else:
                print_result("Subscription Tiers List", False, "Invalid response format")
                return False
        else:
            print_result("Subscription Tiers List", False, f"HTTP {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print_result("Subscription Tiers List", False, f"Exception: {e}")
        return False

def test_checkout_session(auth_token):
    """Test creating a checkout session"""
    print_section("Testing Stripe Checkout Session")
    
    if not auth_token:
        print_result("Checkout Session", False, "No auth token available")
        return False
    
    try:
        # Get available tiers first
        tiers_response = requests.get(f"{BASE_URL}/api/billing/api/subscription-tiers/")
        if tiers_response.status_code != 200:
            print_result("Checkout Session", False, "Cannot fetch tiers for testing")
            return False
            
        tiers = tiers_response.json()['tiers']
        if not tiers:
            print_result("Checkout Session", False, "No tiers available")
            return False
            
        # Test with the first tier (Basic)
        test_tier = tiers[0]
        
        headers = {'Authorization': f'Bearer {auth_token}'}
        payload = {
            'tier_id': test_tier['id'],
            'billing_period': 'monthly'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/billing/stripe/checkout/",
            json=payload,
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('checkout_url'):
                print_result("Checkout Session Creation", True, "Checkout URL generated")
                print(f"    🔗 Checkout URL: {data['checkout_url']}")
                print(f"    💰 Tier: {test_tier['display_name']} - ${test_tier['price_monthly']}/month")
                return True
            else:
                print_result("Checkout Session Creation", False, "Invalid response format")
                return False
        else:
            print_result("Checkout Session Creation", False, f"HTTP {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print_result("Checkout Session Creation", False, f"Exception: {e}")
        return False

def test_subscription_status(auth_token):
    """Test subscription status endpoint"""
    print_section("Testing Subscription Status")
    
    if not auth_token:
        print_result("Subscription Status", False, "No auth token available")
        return False
    
    try:
        headers = {'Authorization': f'Bearer {auth_token}'}
        response = requests.get(f"{BASE_URL}/api/billing/api/subscription-status/", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                subscription = data.get('subscription')
                if subscription:
                    print_result("Subscription Status", True, f"Found subscription: {subscription['tier']['display_name']}")
                else:
                    print_result("Subscription Status", True, "No active subscription (expected for new user)")
                return True
            else:
                print_result("Subscription Status", False, "Invalid response format")
                return False
        else:
            print_result("Subscription Status", False, f"HTTP {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print_result("Subscription Status", False, f"Exception: {e}")
        return False

def test_customer_portal(auth_token):
    """Test customer portal endpoint"""
    print_section("Testing Customer Portal")
    
    if not auth_token:
        print_result("Customer Portal", False, "No auth token available")
        return False
    
    try:
        headers = {'Authorization': f'Bearer {auth_token}'}
        response = requests.post(f"{BASE_URL}/api/billing/stripe/customer-portal/", headers=headers)
        
        # This should fail for a user without a subscription, which is expected
        if response.status_code == 400:
            data = response.json()
            if "No subscription found" in data.get('error', ''):
                print_result("Customer Portal", True, "Correctly requires existing subscription")
                return True
        
        print_result("Customer Portal", False, f"Unexpected response: {response.status_code} - {response.text}")
        return False
    except Exception as e:
        print_result("Customer Portal", False, f"Exception: {e}")
        return False

def main():
    """Run all Stripe payment tests"""
    print_section("Stripe Payment Integration Test Suite")
    print("This will test all the production Stripe endpoints we created.")
    
    # Track test results
    results = []
    
    # Test 1: Subscription Tiers (no auth required)
    results.append(test_subscription_tiers())
    
    # Get authentication token
    print_section("Getting Authentication Token")
    auth_token = get_auth_token()
    if auth_token:
        print_result("Authentication", True, "Successfully obtained auth token")
    else:
        print_result("Authentication", False, "Failed to get auth token")
    
    # Test 2: Checkout Session (requires auth)
    results.append(test_checkout_session(auth_token))
    
    # Test 3: Subscription Status (requires auth)
    results.append(test_subscription_status(auth_token))
    
    # Test 4: Customer Portal (requires auth + subscription)
    results.append(test_customer_portal(auth_token))
    
    # Summary
    print_section("Test Results Summary")
    passed = sum(results)
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Your Stripe integration is working correctly.")
        print("\nNext Steps:")
        print("1. Visit the checkout URL generated above to test the full payment flow")
        print("2. Use Stripe test card: 4242 4242 4242 4242 (any future date, any CVC)")
        print("3. Complete the checkout to test webhooks")
    else:
        print("⚠️  Some tests failed. Check the error messages above.")
    
    return passed == total

if __name__ == "__main__":
    main()
