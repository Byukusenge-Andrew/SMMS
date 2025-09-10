#!/usr/bin/env python3

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from django.contrib.auth.models import User
from apps.authentication.models import UserProfile
from apps.core.models.payment_models import SubscriptionTier, UserSubscription

def test_profile_after_registration():
    print("🔍 QUICK TEST: Check latest registration")
    print("=" * 50)
    
    # Find the most recent api_test_user
    try:
        user = User.objects.filter(username="api_test_user").latest('date_joined')
        print(f"✅ Found latest user: {user.username} (ID: {user.id})")
        print(f"   Date joined: {user.date_joined}")
        
        # Check profile
        try:
            profile = user.profile
            profile.refresh_from_db()
            print(f"\n👤 USER PROFILE:")
            print(f"   Profile ID: {profile.id}")
            print(f"   Company Name: {profile.company_name}")
            print(f"   Subscription Tier ID: {profile.subscription_tier_id}")
            print(f"   Subscription Tier: {profile.subscription_tier}")
            print(f"   Is Trial Active: {profile.is_trial_active}")
            print(f"   Trial Start: {profile.trial_start_date}")
            print(f"   Trial End: {profile.trial_end_date}")
            
            if profile.subscription_tier_id:
                print(f"✅ SUCCESS: subscription_tier_id is set!")
            else:
                print(f"❌ PROBLEM: subscription_tier_id is still NULL")
                
        except Exception as e:
            print(f"❌ Error accessing profile: {e}")
            
        # Check subscription
        try:
            subscription = UserSubscription.objects.get(user=user)
            print(f"\n💳 USER SUBSCRIPTION:")
            print(f"   Subscription ID: {subscription.id}")
            print(f"   Tier: {subscription.tier.name}")
            print(f"   Status: {subscription.status}")
            print(f"   Trial End: {subscription.trial_end_date}")
            
        except UserSubscription.DoesNotExist:
            print(f"❌ No subscription found for user")
            
    except User.DoesNotExist:
        print("❌ No api_test_user found")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_profile_after_registration()
