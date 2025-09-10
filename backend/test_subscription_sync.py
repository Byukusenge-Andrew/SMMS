#!/usr/bin/env python
"""
Test script to verify user subscription data sync between UserProfile and UserSubscription tables
"""

import os
import django
import sys
from datetime import datetime

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from django.contrib.auth.models import User
from apps.authentication.models import UserProfile
from apps.authentication.serializers import UserRegistrationSerializer
from apps.core.models.payment_models import SubscriptionTier, UserSubscription

def test_subscription_sync():
    print("🧪 Testing User Subscription Data Sync")
    print("=" * 50)
    
    # Get a paid subscription tier
    pro_tier = SubscriptionTier.objects.filter(
        name__icontains="pro", 
        is_active=True,
        price_monthly__gt=0
    ).first()
    
    if not pro_tier:
        print("❌ No paid subscription tier found")
        return
    
    print(f"✅ Using subscription tier: {pro_tier.name} (${pro_tier.price_monthly}/month)")
    
    # Test user data
    test_username = "sync_test_user"
    test_email = "sync.test@example.com"
    
    # Clean up any existing test user
    User.objects.filter(username=test_username).delete()
    User.objects.filter(email=test_email).delete()
    
    # Registration data
    registration_data = {
        'username': test_username,
        'email': test_email,
        'password': 'TestPassword123!',
        'password_confirm': 'TestPassword123!',
        'first_name': 'Sync',
        'last_name': 'Test',
        'company_name': 'Test Sync Company',
        'subscription_tier_id': str(pro_tier.id)
    }
    
    print(f"\n📝 Creating user with subscription tier: {pro_tier.id}")
    
    # Use the serializer to create user
    serializer = UserRegistrationSerializer(data=registration_data)
    
    if serializer.is_valid():
        user = serializer.save()
        print(f"✅ User created: {user.username}")
        
        # Check UserProfile
        try:
            profile = UserProfile.objects.get(user=user)
            print(f"\n👤 UserProfile Data:")
            print(f"   Company: {profile.company_name}")
            print(f"   Subscription Tier: {profile.subscription_tier}")
            print(f"   Subscription Tier ID: {profile.subscription_tier.id if profile.subscription_tier else 'None'}")
            print(f"   Trial Active: {profile.is_trial_active}")
            print(f"   Trial End: {profile.trial_end_date}")
            
        except UserProfile.DoesNotExist:
            print("❌ UserProfile not found!")
            return
        
        # Check UserSubscription
        try:
            subscription = UserSubscription.objects.get(user=user)
            print(f"\n💳 UserSubscription Data:")
            print(f"   Tier: {subscription.tier}")
            print(f"   Tier ID: {subscription.tier.id if subscription.tier else 'None'}")
            print(f"   Status: {subscription.status}")
            print(f"   Trial End: {subscription.trial_end_date}")
            print(f"   Start Date: {subscription.start_date}")
            
        except UserSubscription.DoesNotExist:
            print("❌ UserSubscription not found!")
            return
        
        # Verify sync
        profile_tier_id = str(profile.subscription_tier.id) if profile.subscription_tier else None
        subscription_tier_id = str(subscription.tier.id) if subscription.tier else None
        
        print(f"\n🔄 Sync Verification:")
        print(f"   Profile Tier ID: {profile_tier_id}")
        print(f"   Subscription Tier ID: {subscription_tier_id}")
        print(f"   Requested Tier ID: {str(pro_tier.id)}")
        
        if profile_tier_id == subscription_tier_id == str(pro_tier.id):
            print("✅ SUCCESS: All subscription data is synced correctly!")
        else:
            print("❌ FAILED: Subscription data is NOT synced!")
            
        # Check trial dates sync
        if profile.trial_end_date and subscription.trial_end_date:
            if profile.trial_end_date == subscription.trial_end_date:
                print("✅ Trial dates are synced")
            else:
                print("❌ Trial dates are NOT synced")
                print(f"   Profile trial end: {profile.trial_end_date}")
                print(f"   Subscription trial end: {subscription.trial_end_date}")
        
    else:
        print(f"❌ Serializer validation failed: {serializer.errors}")

if __name__ == "__main__":
    test_subscription_sync()
