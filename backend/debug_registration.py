#!/usr/bin/env python3
"""
Debug Registration Issue - Check User Profile Subscription Assignment
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from django.contrib.auth.models import User
from apps.authentication.models import UserProfile
from apps.authentication.serializers import UserRegistrationSerializer
from apps.core.models.payment_models import SubscriptionTier, UserSubscription
from django.utils import timezone

def debug_registration():
    print("🔍 DEBUGGING USER REGISTRATION ISSUE")
    print("=" * 60)
    
    # Clean up any existing test user
    test_username = "debug_user_test"
    test_email = "debug.test@example.com"
    
    try:
        existing_user = User.objects.get(username=test_username)
        print(f"⚠️  Deleting existing user: {test_username}")
        existing_user.delete()
    except User.DoesNotExist:
        pass
    
    # Check available subscription tiers first
    print("🔍 Available subscription tiers (active only):")
    all_tiers = SubscriptionTier.objects.filter(is_active=True)
    for tier in all_tiers:
        print(f"   • {tier.name} (ID: {tier.id})")
        print(f"     Price: ${tier.price_monthly}/month")
        print(f"     Description: {tier.description}")
    print()
    
    # Also check ALL subscription tiers (including inactive)
    print("🔍 ALL subscription tiers in database:")
    all_tiers_including_inactive = SubscriptionTier.objects.all()
    for tier in all_tiers_including_inactive:
        status = "✅ Active" if tier.is_active else "❌ Inactive"
        print(f"   • {tier.name} (ID: {tier.id}) - {status}")
        print(f"     Price: ${tier.price_monthly}/month")
    print()
    
    # Get Basic Plan subscription tier (try different approaches)
    basic_tier = None
    try:
        # Try exact name match first (including inactive)
        basic_tier = SubscriptionTier.objects.get(name="Basic Plan")
        print(f"✅ Found 'Basic Plan' tier by exact name (Active: {basic_tier.is_active})")
    except SubscriptionTier.DoesNotExist:
        try:
            # Try name containing 'basic' (including inactive)
            basic_tier = SubscriptionTier.objects.filter(name__icontains="basic").first()
            if basic_tier:
                print(f"✅ Found basic tier by name search: {basic_tier.name} (Active: {basic_tier.is_active})")
        except:
            pass
    
    if not basic_tier:
        # Just use any available tier for testing
        basic_tier = all_tiers_including_inactive.first()
        if basic_tier:
            print(f"⚠️  No 'Basic Plan' found, using first available tier: {basic_tier.name}")
        else:
            print("❌ No subscription tiers found at all!")
            return
    
    print(f"✅ Using subscription tier:")
    print(f"   ID: {basic_tier.id}")
    print(f"   Name: {basic_tier.name}")
    print(f"   Price: ${basic_tier.price_monthly}")
    print()
    
    print(f"✅ Using subscription tier:")
    print(f"   ID: {basic_tier.id}")
    print(f"   Name: {basic_tier.name}")
    print(f"   Price: ${basic_tier.price_monthly}")
    print()
    
    # Prepare registration data
    registration_data = {
        'username': test_username,
        'email': test_email,
        'password': 'testpass123',
        'password_confirm': 'testpass123',
        'first_name': 'Debug',
        'last_name': 'User',
        'company_name': 'Test Company',
        'subscription_tier_id': str(basic_tier.id)
    }
    
    print("📝 Registration data:")
    for key, value in registration_data.items():
        if 'password' in key:
            print(f"   {key}: {'*' * len(value)}")
        else:
            print(f"   {key}: {value}")
    print()
    
    # Test serializer
    serializer = UserRegistrationSerializer(data=registration_data)
    
    if serializer.is_valid():
        print("✅ Serializer validation passed")
        
        # Create user using serializer
        print("🚀 Creating user with serializer...")
        user = serializer.save()
        
        print(f"✅ User created: {user.username}")
        print()
        
        # Check UserProfile immediately after creation
        try:
            profile = UserProfile.objects.get(user=user)
            print("👤 USER PROFILE AFTER CREATION:")
            print(f"   Profile ID: {profile.id}")
            print(f"   Company Name: {profile.company_name}")
            print(f"   Subscription Tier ID: {profile.subscription_tier_id}")
            print(f"   Subscription Tier: {profile.subscription_tier}")
            print(f"   Is Trial Active: {profile.is_trial_active}")
            print(f"   Trial Start: {profile.trial_start_date}")
            print(f"   Trial End: {profile.trial_end_date}")
            print()
            
            # Check if subscription tier is actually set
            if profile.subscription_tier:
                print(f"✅ Subscription tier correctly assigned:")
                print(f"   Tier Name: {profile.subscription_tier.name}")
                print(f"   Tier Price: ${profile.subscription_tier.price_monthly}")
            else:
                print("❌ Subscription tier is NULL in profile!")
                print(f"   Expected: {basic_tier.name} (ID: {basic_tier.id})")
            print()
            
        except UserProfile.DoesNotExist:
            print("❌ UserProfile not found!")
            return
        
        # Check UserSubscription
        try:
            subscription = UserSubscription.objects.get(user=user)
            print("💳 USER SUBSCRIPTION RECORD:")
            print(f"   Subscription ID: {subscription.id}")
            print(f"   User: {subscription.user.username}")
            print(f"   Tier: {subscription.tier.name}")
            print(f"   Status: {subscription.status}")
            print(f"   Billing Period: {subscription.billing_period}")
            print(f"   Trial End: {subscription.trial_end_date}")
            print()
            
        except UserSubscription.DoesNotExist:
            print("❌ UserSubscription record not found!")
            return
        
        # Test the serializer create method step by step
        print("🔬 DEBUGGING SERIALIZER CREATE METHOD:")
        print("-" * 40)
        
        # Check what happens during profile save
        print("Testing profile save operation...")
        original_tier = profile.subscription_tier
        profile.subscription_tier = basic_tier
        profile.company_name = "Updated Test Company"
        profile.is_trial_active = True
        profile.trial_start_date = timezone.now()
        profile.trial_end_date = timezone.now() + timezone.timedelta(days=14)
        
        try:
            profile.save()
            print("✅ Profile save successful")
            
            # Refresh from database
            profile.refresh_from_db()
            print(f"   Subscription Tier after save: {profile.subscription_tier}")
            print(f"   Trial Active after save: {profile.is_trial_active}")
            
        except Exception as e:
            print(f"❌ Profile save failed: {e}")
    
    else:
        print("❌ Serializer validation failed:")
        for field, errors in serializer.errors.items():
            print(f"   {field}: {errors}")

if __name__ == "__main__":
    debug_registration()
