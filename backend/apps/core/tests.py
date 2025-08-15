"""
Tests for core app - Payment and CRM functionality
"""
import json
from decimal import Decimal
from unittest.mock import Mock, patch

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from .models import (
    SubscriptionTier, 
    UserSubscription, 
    PaymentHistory, 
    GoHighLevelIntegration,
    CRMContact
)

User = get_user_model()


class SubscriptionTierModelTest(TestCase):
    """Test SubscriptionTier model functionality"""
    
    def test_create_subscription_tier(self):
        """Test creating a subscription tier"""
        tier = SubscriptionTier.objects.create(
            name="test_tier",
            display_name="Test Tier",
            description="A test subscription tier",
            price_monthly=Decimal("29.99"),
            price_yearly=Decimal("299.99"),
            max_social_accounts=5,
            max_scheduled_posts=100,
            max_team_members=3,
            analytics_retention_days=30,
            gohighlevel_integration=True,
            advanced_analytics=True,
            priority_support=False,
            white_label=False,
            api_access=True,
            is_active=True
        )
        
        self.assertEqual(tier.name, "test_tier")
        self.assertEqual(tier.display_name, "Test Tier")
        self.assertEqual(tier.price_monthly, Decimal("29.99"))
        self.assertTrue(tier.gohighlevel_integration)
        self.assertTrue(tier.is_active)
    
    def test_tier_string_representation(self):
        """Test string representation of tier"""
        tier = SubscriptionTier.objects.create(
            name="test_tier",
            display_name="Test Tier",
            price_monthly=Decimal("29.99"),
            price_yearly=Decimal("299.99")
        )
        
        self.assertEqual(str(tier), "Test Tier")


class UserSubscriptionModelTest(TestCase):
    """Test UserSubscription model functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
        self.tier = SubscriptionTier.objects.create(
            name="professional",
            display_name="Professional",
            price_monthly=Decimal("29.99"),
            price_yearly=Decimal("299.99")
        )
    
    def test_create_user_subscription(self):
        """Test creating a user subscription"""
        subscription = UserSubscription.objects.create(
            user=self.user,
            tier=self.tier,
            stripe_subscription_id="sub_test123",
            status="active",
            billing_cycle="monthly"
        )
        
        self.assertEqual(subscription.user, self.user)
        self.assertEqual(subscription.tier, self.tier)
        self.assertEqual(subscription.status, "active")
        self.assertEqual(subscription.billing_cycle, "monthly")
    
    def test_subscription_string_representation(self):
        """Test string representation of subscription"""
        subscription = UserSubscription.objects.create(
            user=self.user,
            tier=self.tier,
            stripe_subscription_id="sub_test123",
            status="active"
        )
        
        expected = f"{self.user.username} - {self.tier.display_name} (active)"
        self.assertEqual(str(subscription), expected)


class PaymentHistoryModelTest(TestCase):
    """Test PaymentHistory model functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
        self.tier = SubscriptionTier.objects.create(
            name="professional",
            display_name="Professional", 
            price_monthly=Decimal("29.99"),
            price_yearly=Decimal("299.99")
        )
        
        self.subscription = UserSubscription.objects.create(
            user=self.user,
            tier=self.tier,
            stripe_subscription_id="sub_test123",
            status="active"
        )
    
    def test_create_payment_history(self):
        """Test creating payment history record"""
        payment = PaymentHistory.objects.create(
            user=self.user,
            subscription=self.subscription,
            stripe_payment_intent_id="pi_test123",
            amount=Decimal("29.99"),
            currency="usd",
            status="succeeded",
            description="Monthly subscription payment"
        )
        
        self.assertEqual(payment.user, self.user)
        self.assertEqual(payment.amount, Decimal("29.99"))
        self.assertEqual(payment.currency, "usd")
        self.assertEqual(payment.status, "succeeded")


class GoHighLevelIntegrationModelTest(TestCase):
    """Test GoHighLevelIntegration model functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com", 
            password="testpass123"
        )
    
    def test_create_ghl_integration(self):
        """Test creating GoHighLevel integration"""
        integration = GoHighLevelIntegration.objects.create(
            user=self.user,
            ghl_location_id="loc_test123",
            access_token="token_test123",
            refresh_token="refresh_test123",
            is_active=True
        )
        
        self.assertEqual(integration.user, self.user)
        self.assertEqual(integration.ghl_location_id, "loc_test123")
        self.assertTrue(integration.is_active)
    
    def test_integration_string_representation(self):
        """Test string representation of GHL integration"""
        integration = GoHighLevelIntegration.objects.create(
            user=self.user,
            ghl_location_id="loc_test123",
            access_token="token_test123"
        )
        
        expected = f"GoHighLevel - {self.user.username} (loc_test123)"
        self.assertEqual(str(integration), expected)


class CRMContactModelTest(TestCase):
    """Test CRMContact model functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
        self.integration = GoHighLevelIntegration.objects.create(
            user=self.user,
            ghl_location_id="loc_test123",
            access_token="token_test123"
        )
    
    def test_create_crm_contact(self):
        """Test creating CRM contact"""
        contact = CRMContact.objects.create(
            user=self.user,
            integration=self.integration,
            ghl_contact_id="contact_test123",
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="+1234567890",
            tags=["lead", "social_media"],
            custom_fields={"source": "instagram", "budget": "5000"}
        )
        
        self.assertEqual(contact.user, self.user)
        self.assertEqual(contact.first_name, "John")
        self.assertEqual(contact.last_name, "Doe")
        self.assertEqual(contact.email, "john.doe@example.com")
        self.assertIn("lead", contact.tags)
        self.assertEqual(contact.custom_fields["source"], "instagram")
    
    def test_contact_string_representation(self):
        """Test string representation of CRM contact"""
        contact = CRMContact.objects.create(
            user=self.user,
            integration=self.integration,
            ghl_contact_id="contact_test123",
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com"
        )
        
        expected = "John Doe (john.doe@example.com)"
        self.assertEqual(str(contact), expected)


class PaymentAPITestCase(APITestCase):
    """Test Payment API endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
        self.tier = SubscriptionTier.objects.create(
            name="professional",
            display_name="Professional",
            price_monthly=Decimal("29.99"),
            price_yearly=Decimal("299.99"),
            is_active=True
        )
        
        # Authenticate the user
        self.client.force_authenticate(user=self.user)
    
    def test_get_subscription_tiers(self):
        """Test getting available subscription tiers"""
        url = reverse('core:subscription-tiers')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'professional')
    
    def test_get_current_subscription_no_subscription(self):
        """Test getting current subscription when user has none"""
        url = reverse('core:current-subscription')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['subscription'])
    
    def test_get_current_subscription_with_subscription(self):
        """Test getting current subscription when user has one"""
        subscription = UserSubscription.objects.create(
            user=self.user,
            tier=self.tier,
            stripe_subscription_id="sub_test123",
            status="active"
        )
        
        url = reverse('core:current-subscription')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['subscription'])
        self.assertEqual(response.data['subscription']['tier']['name'], 'professional')
    
    @patch('stripe.checkout.Session.create')
    def test_create_checkout_session(self, mock_stripe_session):
        """Test creating Stripe checkout session"""
        # Mock Stripe response
        mock_stripe_session.return_value = Mock(
            id='cs_test123',
            url='https://checkout.stripe.com/pay/cs_test123'
        )
        
        url = reverse('core:create-checkout-session')
        data = {
            'tier_id': self.tier.id,
            'billing_cycle': 'monthly'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('checkout_url', response.data)
        self.assertIn('session_id', response.data)


class CRMAPITestCase(APITestCase):
    """Test CRM API endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
        self.integration = GoHighLevelIntegration.objects.create(
            user=self.user,
            ghl_location_id="loc_test123",
            access_token="token_test123",
            is_active=True
        )
        
        # Authenticate the user
        self.client.force_authenticate(user=self.user)
    
    def test_get_crm_contacts(self):
        """Test getting CRM contacts"""
        # Create test contact
        CRMContact.objects.create(
            user=self.user,
            integration=self.integration,
            ghl_contact_id="contact_test123",
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com"
        )
        
        url = reverse('core:crm-contacts')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['first_name'], 'John')
    
    def test_get_integration_status(self):
        """Test getting CRM integration status"""
        url = reverse('core:crm-integration-status')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_connected'])
        self.assertEqual(response.data['location_id'], 'loc_test123')
    
    def test_get_integration_status_no_integration(self):
        """Test getting integration status when no integration exists"""
        # Delete the integration
        self.integration.delete()
        
        url = reverse('core:crm-integration-status')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_connected'])
        self.assertIsNone(response.data['location_id'])


class FeatureAccessTest(TestCase):
    """Test feature access based on subscription tiers"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
        # Create different tiers
        self.free_tier = SubscriptionTier.objects.create(
            name="free",
            display_name="Free",
            price_monthly=Decimal("0.00"),
            price_yearly=Decimal("0.00"),
            max_social_accounts=3,
            gohighlevel_integration=False,
            advanced_analytics=False,
            priority_support=False,
            api_access=False
        )
        
        self.pro_tier = SubscriptionTier.objects.create(
            name="professional",
            display_name="Professional", 
            price_monthly=Decimal("29.99"),
            price_yearly=Decimal("299.99"),
            max_social_accounts=10,
            gohighlevel_integration=True,
            advanced_analytics=True,
            priority_support=True,
            api_access=True
        )
    
    def test_free_tier_limitations(self):
        """Test that free tier has proper limitations"""
        subscription = UserSubscription.objects.create(
            user=self.user,
            tier=self.free_tier,
            status="active"
        )
        
        self.assertEqual(subscription.tier.max_social_accounts, 3)
        self.assertFalse(subscription.tier.gohighlevel_integration)
        self.assertFalse(subscription.tier.advanced_analytics)
        self.assertFalse(subscription.tier.api_access)
    
    def test_pro_tier_features(self):
        """Test that pro tier has advanced features"""
        subscription = UserSubscription.objects.create(
            user=self.user,
            tier=self.pro_tier,
            status="active"
        )
        
        self.assertEqual(subscription.tier.max_social_accounts, 10)
        self.assertTrue(subscription.tier.gohighlevel_integration)
        self.assertTrue(subscription.tier.advanced_analytics)
        self.assertTrue(subscription.tier.api_access)


class WebhookTest(TestCase):
    """Test Stripe webhook handling"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
        self.tier = SubscriptionTier.objects.create(
            name="professional",
            display_name="Professional",
            price_monthly=Decimal("29.99"),
            price_yearly=Decimal("299.99")
        )
    
    @patch('stripe.Webhook.construct_event')
    def test_webhook_subscription_created(self, mock_construct_event):
        """Test webhook handling for subscription creation"""
        # Mock webhook event
        mock_event = {
            'type': 'customer.subscription.created',
            'data': {
                'object': {
                    'id': 'sub_test123',
                    'customer': 'cus_test123',
                    'status': 'active',
                    'current_period_start': 1692057600,
                    'current_period_end': 1694736000,
                    'items': {
                        'data': [{
                            'price': {
                                'id': 'price_test123'
                            }
                        }]
                    }
                }
            }
        }
        
        mock_construct_event.return_value = mock_event
        
        url = reverse('core:stripe-webhook')
        response = self.client.post(
            url,
            data=json.dumps({'test': 'data'}),
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='test_signature'
        )
        
        # Should return 200 even if processing fails (to prevent retries)
        self.assertEqual(response.status_code, 200)
