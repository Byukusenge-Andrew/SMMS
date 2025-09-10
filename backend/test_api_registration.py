#!/usr/bin/env python3
"""
Test Registration API Endpoint - Mimicking Frontend Behavior
"""

import os
import sys
import django
import requests
import json

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from django.contrib.auth.models import User
from apps.authentication.models import UserProfile
from apps.core.models.payment_models import SubscriptionTier, UserSubscription

def test_api_registration():
    print("🔍 TESTING API REGISTRATION ENDPOINT")
    print("=" * 60)
    
    # Clean up any existing test user
    test_username = "api_test_user"
    test_email = "api.test@example.com"
    
    try:
        existing_user = User.objects.get(username=test_username)
        print(f"⚠️  Deleting existing user: {test_username}")
        existing_user.delete()
    except User.DoesNotExist:
        pass
    
    # Get a subscription tier
    try:
        basic_tier = SubscriptionTier.objects.filter(name__icontains="basic", is_active=True).first()
        if not basic_tier:
            basic_tier = SubscriptionTier.objects.filter(is_active=True).first()
        
        print(f"✅ Using subscription tier:")
        print(f"   ID: {basic_tier.id}")
        print(f"   Name: {basic_tier.name}")
        print(f"   Price: ${basic_tier.price_monthly}")
        print()
    except Exception as e:
        print(f"❌ Error getting subscription tier: {e}")
        return
    
    # Prepare registration data (exactly as frontend would send)
    registration_data = {
        'username': test_username,
        'email': test_email,
        'password': 'testpass123',
        'password_confirm': 'testpass123',
        'first_name': 'API',
        'last_name': 'TestUser',
        'company_name': 'API Test Company',
        'subscription_tier_id': str(basic_tier.id)
    }
    
    print("📝 Registration data being sent to API:")
    for key, value in registration_data.items():
        if 'password' in key:
            print(f"   {key}: {'*' * len(value)}")
        else:
            print(f"   {key}: {value}")
    print()
    
    # Make API request to registration endpoint
    api_url = "http://127.0.0.1:8000/api/auth/register/"
    
    print(f"🚀 Making POST request to: {api_url}")
    
    try:
        response = requests.post(
            api_url,
            data=json.dumps(registration_data),
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            timeout=30
        )
        
        print(f"📊 Response Status: {response.status_code}")
        print(f"📊 Response Headers: {dict(response.headers)}")
        print()
        
        if response.status_code == 201:
            response_data = response.json()
            print("✅ Registration API call successful!")
            print("📄 Response data:")
            print(json.dumps(response_data, indent=2))
            print()
            
            # Now check what was actually created in the database
            # Add a small delay to ensure database transactions are complete
            import time
            time.sleep(0.5)
            
            try:
                created_user = User.objects.get(username=test_username)
                print(f"✅ User found in database: {created_user.username}")
                
                # Check UserProfile with explicit database refresh
                try:
                    profile = UserProfile.objects.get(user=created_user)
                    # Force refresh from database
                    profile.refresh_from_db()
                    
                    print("👤 USER PROFILE FROM API REGISTRATION:")
                    print(f"   Profile ID: {profile.id}")
                    print(f"   Company Name: {profile.company_name}")
                    print(f"   Subscription Tier ID: {profile.subscription_tier_id}")
                    print(f"   Subscription Tier: {profile.subscription_tier}")
                    print(f"   Subscription Tier FK ID: {profile.subscription_tier.id if profile.subscription_tier else 'None'}")
                    print(f"   Is Trial Active: {profile.is_trial_active}")
                    print(f"   Trial Start: {profile.trial_start_date}")
                    print(f"   Trial End: {profile.trial_end_date}")
                    print()
                    
                    if profile.subscription_tier_id is None:
                        print("❌ PROBLEM FOUND: subscription_tier_id is NULL in profile!")
                        print(f"   Expected: {basic_tier.id}")
                        print(f"   Expected Name: {basic_tier.name}")
                    else:
                        print("✅ subscription_tier_id is properly set in profile")
                        print(f"   Found ID: {profile.subscription_tier_id}")
                    
                except UserProfile.DoesNotExist:
                    print("❌ UserProfile not found!")
                
                # Check UserSubscription
                try:
                    subscription = UserSubscription.objects.get(user=created_user)
                    print("💳 USER SUBSCRIPTION FROM API REGISTRATION:")
                    print(f"   Subscription ID: {subscription.id}")
                    print(f"   User: {subscription.user.username}")
                    print(f"   Tier: {subscription.tier.name}")
                    print(f"   Status: {subscription.status}")
                    print(f"   Billing Period: {subscription.billing_period}")
                    print(f"   Trial End: {subscription.trial_end_date}")
                    print()
                    
                except UserSubscription.DoesNotExist:
                    print("❌ UserSubscription record not found!")
                    
            except User.DoesNotExist:
                print("❌ User not found in database after API call!")
                
        else:
            print(f"❌ Registration API call failed!")
            print(f"Response: {response.text}")
            
            try:
                error_data = response.json()
                print("Error details:")
                print(json.dumps(error_data, indent=2))
            except:
                print("Could not parse error response as JSON")
    
    except requests.exceptions.ConnectionError:
        print("❌ Connection error! Is the Django development server running?")
        print("Start it with: python manage.py runserver")
    except Exception as e:
        print(f"❌ Error making API request: {e}")

if __name__ == "__main__":
    test_api_registration()
