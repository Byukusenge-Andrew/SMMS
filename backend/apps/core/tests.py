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
        
        self.assertEqual(str(tier), "Test Tier - $29.99/month")


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
            billing_period="monthly"
        )
        
        self.assertEqual(subscription.user, self.user)
        self.assertEqual(subscription.tier, self.tier)
        self.assertEqual(subscription.status, "active")
        self.assertEqual(subscription.billing_period, "monthly")
    
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
            status="succeeded"
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
            location_id="loc_test123",
            api_key="token_test123",
            is_active=True
        )
        
        self.assertEqual(integration.user, self.user)
        self.assertEqual(integration.location_id, "loc_test123")
        self.assertTrue(integration.is_active)
    
    def test_integration_string_representation(self):
        """Test string representation of GHL integration"""
        integration = GoHighLevelIntegration.objects.create(
            user=self.user,
            location_id="loc_test123",
            api_key="token_test123"
        )
        
        expected = f"{self.user.username} - GoHighLevel"
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
            location_id="loc_test123",
            api_key="token_test123"
        )
    
    def test_create_crm_contact(self):
        """Test creating CRM contact"""
        contact = CRMContact.objects.create(
            user=self.user,
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
        url = reverse('core:subscription_tiers')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['tiers']), 1)
        self.assertEqual(response.data['tiers'][0]['name'], 'professional')
    
    def test_get_current_subscription_no_subscription(self):
        """Test getting current subscription when user has none"""
        url = reverse('core:user_subscription')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['subscription'])
    
    def test_get_current_subscription_with_subscription(self):
        subscription = UserSubscription.objects.create(
            user=self.user,
            tier=self.tier,
            stripe_subscription_id="sub_test123",
            status="active"
        )
        
        url = reverse('core:user_subscription')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['subscription'])
        self.assertEqual(response.data['subscription']['tier']['name'], 'professional')
    
    @patch('apps.core.services.stripe_service.StripePaymentService.create_subscription')
    def test_create_checkout_session(self, mock_create_sub):
        """Test creating Stripe subscription"""
        mock_create_sub.return_value = {
            'success': True,
            'subscription_id': 'sub_test123',
            'status': 'active'
        }
        
        url = reverse('core:create_subscription')
        data = {
            'tier_id': self.tier.id,
            'billing_period': 'monthly'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])


class CRMAPITestCase(APITestCase):
    """Test CRM API endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
        # Create subscription for user to allow GHL integration access
        tier = SubscriptionTier.objects.create(
            name="professional",
            display_name="Professional",
            price_monthly=Decimal("29.99"),
            price_yearly=Decimal("299.99"),
            gohighlevel_integration=True,
            is_active=True
        )
        UserSubscription.objects.create(
            user=self.user,
            tier=tier,
            status="active"
        )
        
        self.integration = GoHighLevelIntegration.objects.create(
            user=self.user,
            location_id="loc_test123",
            api_key="token_test123",
            is_active=True
        )
        
        # Authenticate the user
        self.client.force_authenticate(user=self.user)
    
    def test_get_crm_contacts(self):
        """Test getting CRM contacts"""
        # Create test contact
        CRMContact.objects.create(
            user=self.user,
            ghl_contact_id="contact_test123",
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com"
        )
        
        url = reverse('core:get_contacts')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['first_name'], 'John')
    
    def test_get_integration_status(self):
        """Test getting CRM integration status"""
        url = reverse('core:ghl_integration')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['integration']['location_id'], 'loc_test123')
    
    def test_get_integration_status_no_integration(self):
        """Test getting integration status when no integration exists"""
        # Delete the integration
        self.integration.delete()
        
        url = reverse('core:ghl_integration')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data['success'])


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
            priority_support=False
        )
        
        self.pro_tier = SubscriptionTier.objects.create(
            name="professional",
            display_name="Professional", 
            price_monthly=Decimal("29.99"),
            price_yearly=Decimal("299.99"),
            max_social_accounts=10,
            gohighlevel_integration=True,
            advanced_analytics=True,
            priority_support=True
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
        
        url = reverse('core:stripe_webhook')
        response = self.client.post(
            url,
            data=json.dumps({'test': 'data'}),
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='test_signature'
        )
        
        # Should return 200 even if processing fails (to prevent retries)
        self.assertEqual(response.status_code, 200)


class LogVisualizerTestCase(TestCase):
    """Test Log Visualizer views and security controls"""

    def setUp(self):
        self.client = Client()
        # Normal user
        self.user = User.objects.create_user(
            username="normaluser",
            email="normal@example.com",
            password="password123"
        )
        # Staff user
        self.staff_user = User.objects.create_user(
            username="staffuser",
            email="staff@example.com",
            password="password123",
            is_staff=True
        )
        # Create a dummy log file to test with
        from apps.core.views.logs_views import LOGS_DIR, ALLOWED_LOG_FILES
        os.makedirs(LOGS_DIR, exist_ok=True)
        self.test_log_filename = "django.log"
        self.test_log_path = os.path.join(LOGS_DIR, self.test_log_filename)
        with open(self.test_log_path, 'w', encoding='utf-8') as f:
            f.write("2026-06-24 10:45:15 INFO Simple log line 1\n")
            f.write("2026-06-24 10:46:20 WARNING Warning log line 2\n")
            f.write("2026-06-24 10:47:30 ERROR Error log line 3\n")

    def test_anonymous_redirected(self):
        """Test that anonymous users are redirected to login"""
        # Test HTML page
        url = reverse('core:log-viewer-html')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)

        # Test list API
        url = reverse('core:log-list-api')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        # Test content API
        url = reverse('core:log-content-api', args=[self.test_log_filename])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_normal_user_redirected(self):
        """Test that authenticated non-staff users are redirected/blocked"""
        self.client.force_login(self.user)
        
        # Test HTML page
        url = reverse('core:log-viewer-html')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        # Test content API
        url = reverse('core:log-content-api', args=[self.test_log_filename])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_staff_user_access_html(self):
        """Test that staff members can access the log visualizer page"""
        self.client.force_login(self.staff_user)
        url = reverse('core:log-viewer-html')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/logs_visualizer.html")

    def test_staff_user_access_list_api(self):
        """Test that staff members can list logs"""
        self.client.force_login(self.staff_user)
        url = reverse('core:log-list-api')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(any(log['name'] == self.test_log_filename for log in data['logs']))

    def test_staff_user_access_content_api(self):
        """Test fetching log content with level and search filters"""
        self.client.force_login(self.staff_user)
        
        # Basic content fetch
        url = reverse('core:log-content-api', args=[self.test_log_filename])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(len(data['lines']), 3)

        # Filter by ERROR level
        response = self.client.get(url, {'level': 'ERROR'})
        data = response.json()
        self.assertEqual(len(data['lines']), 1)
        self.assertIn("Error log line 3", data['lines'][0])

        # Filter by search string
        response = self.client.get(url, {'search': 'Warning'})
        data = response.json()
        self.assertEqual(len(data['lines']), 1)
        self.assertIn("Warning log line 2", data['lines'][0])

    def test_path_traversal_blocked(self):
        """Test that directory traversal in log filename parameters is blocked"""
        self.client.force_login(self.staff_user)
        # Attempt traversal
        url = reverse('core:log-content-api', args=["../../manage.py"])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['success'])

    def test_clear_log_api(self):
        """Test clearing a log file"""
        self.client.force_login(self.staff_user)
        url = reverse('core:log-clear-api', args=[self.test_log_filename])
        
        # Must be POST
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)
        
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        
        # Verify file is empty
        with open(self.test_log_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertEqual(content, "")

    def test_download_log_api(self):
        """Test downloading a log file"""
        self.client.force_login(self.staff_user)
        url = reverse('core:log-download-api', args=[self.test_log_filename])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain')
        self.assertIn('attachment', response['Content-Disposition'])

