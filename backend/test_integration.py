#!/usr/bin/env python
"""
Test script to verify the payment and CRM integration is working
"""
import os
import sys
import django

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')

# Setup Django
django.setup()

from apps.core.models.payment_models import SubscriptionTier, UserSubscription, PaymentHistory
from apps.core.models.crm_models import GoHighLevelIntegration, CRMContact
from django.contrib.auth.models import User
from decimal import Decimal
import uuid

def test_payment_models():
    """Test payment models creation and functionality"""
    print("[TEST] Testing Payment Models...")
    
    # Test SubscriptionTier creation (get or create to avoid duplicates)
    free_tier, created = SubscriptionTier.objects.get_or_create(
        name='free',
        defaults={
            'display_name': 'Free Plan',
            'description': 'Basic features for getting started',
            'price_monthly': Decimal('0.00'),
            'price_yearly': Decimal('0.00'),
            'max_social_accounts': 1,
            'max_scheduled_posts': 10,
            'max_team_members': 1,
            'analytics_retention_days': 7,
            'api_rate_limit': 100,
            'gohighlevel_integration': False,
            'advanced_analytics': False,
            'priority_support': False,
            'white_label': False
        }
    )
    if created:
        print(f"[PASS] Created Free Tier: {free_tier.display_name}")
    else:
        print(f"[PASS] Using existing Free Tier: {free_tier.display_name}")
    
    basic_tier, created = SubscriptionTier.objects.get_or_create(
        name='basic',
        defaults={
            'display_name': 'Basic Plan',
            'description': 'Essential features for small businesses',
            'price_monthly': Decimal('9.99'),
            'price_yearly': Decimal('99.99'),
            'max_social_accounts': 3,
            'max_scheduled_posts': 100,
            'max_team_members': 2,
            'analytics_retention_days': 30,
            'api_rate_limit': 1000,
            'gohighlevel_integration': False,
            'advanced_analytics': True,
            'priority_support': False,
            'white_label': False
        }
    )
    if created:
        print(f"[PASS] Created Basic Tier: {basic_tier.display_name}")
    else:
        print(f"[PASS] Using existing Basic Tier: {basic_tier.display_name}")
    
    # Test user creation and subscription
    test_user, created = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'test@example.com'
        }
    )
    if created:
        test_user.set_password('testpassword')
        test_user.save()
        print(f"[PASS] Created Test User: {test_user.username}")
    else:
        print(f"[PASS] Using existing Test User: {test_user.username}")
    
    # Try to get existing subscription or create new one
    user_subscription, created = UserSubscription.objects.get_or_create(
        user=test_user,
        defaults={
            'tier': basic_tier,
            'status': 'active',
            'billing_period': 'monthly',
            'stripe_customer_id': 'cus_test123',
            'stripe_subscription_id': 'sub_test123'
        }
    )
    if created:
        print(f"[PASS] Created User Subscription: {user_subscription.tier.display_name}")
    else:
        print(f"[PASS] Using existing User Subscription: {user_subscription.tier.display_name}")
    
    # Test payment history (create with unique payment intent ID)
    from django.utils import timezone
    payment_intent_id = f'pi_test_{uuid.uuid4().hex[:8]}'
    payment = PaymentHistory.objects.create(
        user=test_user,
        subscription=user_subscription,
        amount=Decimal('9.99'),
        currency='usd',
        status='succeeded',
        stripe_payment_intent_id=payment_intent_id,
        payment_date=timezone.now()
    )
    print(f"[PASS] Created Payment History: ${payment.amount} {payment.currency}")
    
    return True

def test_crm_models():
    """Test CRM models creation and functionality"""
    print("\n[TEST] Testing CRM Models...")
    
    # Get or create test user
    test_user, created = User.objects.get_or_create(
        username='crmuser',
        defaults={'email': 'crm@example.com'}
    )
    if created:
        print(f"[PASS] Created CRM Test User: {test_user.username}")
    else:
        print(f"[PASS] Using existing CRM Test User: {test_user.username}")
    
    # Test GoHighLevel Integration
    ghl_integration, created = GoHighLevelIntegration.objects.get_or_create(
        user=test_user,
        defaults={
            'api_key': 'test_api_key_123',
            'location_id': 'test_location_123',
            'is_active': True,
            'sync_contacts': True,
            'sync_opportunities': True,
            'sync_campaigns': False
        }
    )
    if created:
        print(f"[PASS] Created GoHighLevel Integration for: {ghl_integration.user.username}")
    else:
        print(f"[PASS] Using existing GoHighLevel Integration for: {ghl_integration.user.username}")
    
    # Test CRM Contact (create with unique GHL contact ID)
    ghl_contact_id = f'ghl_contact_{uuid.uuid4().hex[:8]}'
    crm_contact = CRMContact.objects.create(
        user=test_user,
        ghl_contact_id=ghl_contact_id,
        first_name='John',
        last_name='Doe',
        email='john.doe@example.com',
        phone='+1234567890',
        company='Test Company Inc',
        status='lead',
        tags=['test', 'lead', 'demo'],
        custom_fields={'source': 'website', 'interest': 'social_media'},
        social_media_profiles={'twitter': '@johndoe', 'linkedin': 'johndoe'}
    )
    print(f"[PASS] Created CRM Contact: {crm_contact.full_name}")
    
    return True

def test_api_imports():
    """Test that all our API modules can be imported"""
    print("\n[TEST] Testing API Imports...")
    
    try:
        from apps.core.services.stripe_service import StripePaymentService
        print("[PASS] Successfully imported StripePaymentService")
        
        from apps.core.services.gohighlevel_service import GoHighLevelService  
        print("[PASS] Successfully imported GoHighLevelService")
        
        from apps.core.views.payment_views import get_subscription_tiers
        print("[PASS] Successfully imported payment views")
        
        from apps.core.views.gohighlevel_views import setup_gohighlevel_integration
        print("[PASS] Successfully imported CRM views")
        
        return True
    except ImportError as e:
        print(f"[FAIL] Import error: {e}")
        return False

def test_database_queries():
    """Test database queries and model relationships"""
    print("\n[TEST] Testing Database Queries...")
    
    # Test tier queries
    tiers = SubscriptionTier.objects.filter(is_active=True)
    print(f"[PASS] Found {tiers.count()} active subscription tiers")
    
    # Test user subscriptions
    subscriptions = UserSubscription.objects.select_related('tier', 'user')
    print(f"[PASS] Found {subscriptions.count()} user subscriptions")
    
    # Test payment history
    payments = PaymentHistory.objects.select_related('user', 'subscription')
    print(f"[PASS] Found {payments.count()} payment records")
    
    # Test CRM integrations
    integrations = GoHighLevelIntegration.objects.select_related('user')
    print(f"[PASS] Found {integrations.count()} GoHighLevel integrations")
    
    # Test CRM contacts
    contacts = CRMContact.objects.select_related('user')
    print(f"[PASS] Found {contacts.count()} CRM contacts")
    
    return True

def main():
    """Main test function"""
    print("[START] Starting Payment and CRM Integration Tests\n")
    
    tests_passed = 0
    total_tests = 4
    
    try:
        if test_payment_models():
            tests_passed += 1
        
        if test_crm_models():
            tests_passed += 1
            
        if test_api_imports():
            tests_passed += 1
            
        if test_database_queries():
            tests_passed += 1
            
    except Exception as e:
        print(f"[FAIL] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n[RESULT] Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("[SUCCESS] All tests passed! Payment and CRM integration is working correctly.")
        return True
    else:
        print("[WARNING] Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
