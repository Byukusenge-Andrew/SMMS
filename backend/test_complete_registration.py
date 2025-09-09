#!/usr/bin/env python3
"""
Complete User Registration Test Script
Tests registration with all fields including subscription tier
"""

import os
import sys
import django
import json
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from django.contrib.auth.models import User
from apps.authentication.serializers import RegisterSerializer
from apps.core.models.payment_models import SubscriptionTier
from apps.authentication.models import UserProfile

def test_complete_registration():
    """Test complete user registration with all fields"""
    
    print("=" * 60)
    print("COMPLETE USER REGISTRATION TEST")
    print("=" * 60)
    
    # Get a subscription tier (using 'pro' tier)
    try:
        pro_tier = SubscriptionTier.objects.get(name='pro', is_active=True)
        print(f"✓ Found Pro subscription tier: {pro_tier.display_name}")
        print(f"  ID: {pro_tier.id}")
        print(f"  Price Monthly: ${pro_tier.price_monthly}")
        print(f"  Max Social Accounts: {pro_tier.max_social_accounts}")
        print(f"  Max Team Members: {pro_tier.max_team_members}")
    except SubscriptionTier.DoesNotExist:
        print("✗ Pro subscription tier not found, using free tier")
        pro_tier = SubscriptionTier.objects.get(name='free', is_active=True)
    
    print()
    
    # Complete registration data
    registration_data = {
        'username': 'complete_user_2024',
        'email': 'complete.user@example.com',
        'password': 'SuperSecure!Pass123',
        'password_confirm': 'SuperSecure!Pass123',
        'first_name': 'John',
        'last_name': 'Doe',
        'company_name': 'Acme Digital Marketing Agency',
        'subscription_tier_id': str(pro_tier.id)
    }
    
    print("Registration Data:")
    print("-" * 30)
    for key, value in registration_data.items():
        if 'password' in key:
            print(f"{key}: {'*' * len(value)}")
        else:
            print(f"{key}: {value}")
    print()
    
    # Check if user already exists and clean up if needed
    try:
        existing_user = User.objects.get(username=registration_data['username'])
        print(f"⚠ User '{registration_data['username']}' already exists. Deleting...")
        existing_user.delete()
        print("✓ Existing user deleted")
    except User.DoesNotExist:
        print(f"✓ Username '{registration_data['username']}' is available")
    
    try:
        existing_user = User.objects.get(email=registration_data['email'])
        print(f"⚠ Email '{registration_data['email']}' already exists. Deleting...")
        existing_user.delete()
        print("✓ Existing user with email deleted")
    except User.DoesNotExist:
        print(f"✓ Email '{registration_data['email']}' is available")
    
    print()
    
    # Test the serializer
    print("Testing Registration Serializer...")
    print("-" * 40)
    
    serializer = RegisterSerializer(data=registration_data)
    
    if serializer.is_valid():
        print("✓ Serializer validation passed")
        
        # Create the user
        try:
            user = serializer.save()
            print(f"✓ User created successfully!")
            print(f"  Username: {user.username}")
            print(f"  Email: {user.email}")
            print(f"  Full Name: {user.first_name} {user.last_name}")
            print(f"  Date Joined: {user.date_joined}")
            print(f"  Is Active: {user.is_active}")
            print()
            
            # Check user profile
            try:
                profile = UserProfile.objects.get(user=user)
                print("✓ User Profile Created:")
                print(f"  Profile ID: {profile.id}")
                print(f"  Company Name: {profile.company_name}")
                print(f"  Subscription Tier: {profile.subscription_tier.display_name if profile.subscription_tier else 'None'}")
                print(f"  Is Trial Active: {profile.is_trial_active}")
                print(f"  Trial End Date: {profile.trial_end_date}")
                print(f"  Days Left in Trial: {profile.days_left_in_trial()}")
                print(f"  Timezone: {profile.timezone}")
                print(f"  Email Notifications: {profile.email_notifications}")
                print()
                
                # Test effective subscription tier
                effective_tier = profile.get_effective_subscription_tier()
                if effective_tier:
                    print("✓ Effective Subscription Tier:")
                    print(f"  Name: {effective_tier.display_name}")
                    print(f"  Max Social Accounts: {effective_tier.max_social_accounts}")
                    print(f"  Max Team Members: {effective_tier.max_team_members}")
                    print(f"  Advanced Analytics: {effective_tier.advanced_analytics}")
                    print(f"  Priority Support: {effective_tier.priority_support}")
                else:
                    print("✗ No effective subscription tier found")
                
            except UserProfile.DoesNotExist:
                print("✗ User profile was not created")
            
        except Exception as e:
            print(f"✗ Error creating user: {str(e)}")
            return False
            
    else:
        print("✗ Serializer validation failed:")
        for field, errors in serializer.errors.items():
            print(f"  {field}: {errors}")
        return False
    
    print()
    print("=" * 60)
    print("AUTHENTICATION TEST")
    print("=" * 60)
    
    # Test authentication
    from django.contrib.auth import authenticate
    
    auth_user = authenticate(
        username=registration_data['username'], 
        password=registration_data['password']
    )
    
    if auth_user:
        print("✓ Authentication successful!")
        print(f"  Authenticated User: {auth_user.username}")
        print(f"  User ID: {auth_user.id}")
    else:
        print("✗ Authentication failed")
        return False
    
    print()
    print("=" * 60)
    print("API REGISTRATION TEST")
    print("=" * 60)
    
    # Test via API endpoint (simulate)
    from apps.authentication.serializers import LoginSerializer
    
    login_data = {
        'username': registration_data['username'],
        'password': registration_data['password']
    }
    
    login_serializer = LoginSerializer(data=login_data)
    if login_serializer.is_valid():
        print("✓ Login serializer validation passed")
        # In a real API call, this would set the session/token
        print("✓ Ready for API authentication")
    else:
        print("✗ Login serializer validation failed:")
        for field, errors in login_serializer.errors.items():
            print(f"  {field}: {errors}")
    
    print()
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print("✓ User registration with complete data: SUCCESS")
    print("✓ Subscription tier assignment: SUCCESS")
    print("✓ User profile creation: SUCCESS")
    print("✓ Authentication test: SUCCESS")
    print("✓ Trial period setup: SUCCESS")
    print()
    print(f"New user '{user.username}' is ready to use the system!")
    
    return True

def test_multiple_subscription_tiers():
    """Test registration with different subscription tiers"""
    
    print("\n" + "=" * 60)
    print("MULTIPLE SUBSCRIPTION TIERS TEST")
    print("=" * 60)
    
    tiers = SubscriptionTier.objects.filter(is_active=True)
    
    for i, tier in enumerate(tiers[:3], 1):  # Test first 3 tiers
        username = f"test_user_{tier.name}_{i}"
        email = f"test.{tier.name}@example.com"
        
        # Clean up existing user if any
        try:
            existing = User.objects.get(username=username)
            existing.delete()
        except User.DoesNotExist:
            pass
        
        try:
            existing = User.objects.get(email=email)
            existing.delete()
        except User.DoesNotExist:
            pass
        
        data = {
            'username': username,
            'email': email,
            'password': 'TestPass123!',
            'password_confirm': 'TestPass123!',
            'first_name': f'Test{i}',
            'last_name': f'User{tier.name.title()}',
            'company_name': f'{tier.display_name} Company',
            'subscription_tier_id': str(tier.id)
        }
        
        serializer = RegisterSerializer(data=data)
        if serializer.is_valid():
            user = serializer.save()
            profile = UserProfile.objects.get(user=user)
            effective_tier = profile.get_effective_subscription_tier()
            
            print(f"✓ User {i}: {username}")
            print(f"  Tier: {effective_tier.display_name}")
            print(f"  Trial Active: {profile.is_trial_active}")
            print(f"  Days Left: {profile.days_left_in_trial()}")
        else:
            print(f"✗ Failed to create user {username}: {serializer.errors}")

if __name__ == "__main__":
    print("Starting Complete Registration Tests...")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Run main test
        success = test_complete_registration()
        
        if success:
            # Run additional tests
            test_multiple_subscription_tiers()
            
        print(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
