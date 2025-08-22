"""
Stripe payment service for subscription management
"""
import logging
import stripe
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from typing import Dict, Optional, Any

from ..models.payment_models import SubscriptionTier, UserSubscription, PaymentHistory

logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')


class StripePaymentService:
    """Service class for handling Stripe payments and subscriptions"""
    
    def __init__(self):
        self.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')
        self.publishable_key = getattr(settings, 'STRIPE_PUBLISHABLE_KEY', '')
        self.webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
        
        if not self.api_key:
            logger.warning("Stripe API key not configured")
    
    def create_customer(self, user: User) -> Optional[str]:
        """Create a Stripe customer for the user"""
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=f"{user.first_name} {user.last_name}".strip() or user.username,
                metadata={
                    'user_id': str(user.id),
                    'username': user.username,
                }
            )
            logger.info(f"Created Stripe customer {customer.id} for user {user.username}")
            return customer.id
            
        except stripe.StripeError as e:
            logger.error(f"Failed to create Stripe customer for user {user.username}: {e}")
            return None
    
    def get_or_create_customer(self, user: User) -> Optional[str]:
        """Get existing customer or create new one"""
        # Check if user already has a subscription with customer ID
        try:
            subscription = UserSubscription.objects.get(user=user)
            if subscription.stripe_customer_id:
                # Verify customer exists in Stripe
                try:
                    stripe.Customer.retrieve(subscription.stripe_customer_id)
                    return subscription.stripe_customer_id
                except stripe.StripeError:
                    logger.warning(f"Stripe customer {subscription.stripe_customer_id} not found, creating new one")
        except UserSubscription.DoesNotExist:
            pass
        
        # Create new customer
        return self.create_customer(user)
    
    def create_subscription(
        self, 
        user: User, 
        tier: SubscriptionTier, 
        billing_period: str = 'monthly',
        payment_method_id: str = None,
        trial_days: int = None
    ) -> Dict[str, Any]:
        """Create a Stripe subscription"""
        try:
            # Get or create customer
            customer_id = self.get_or_create_customer(user)
            if not customer_id:
                return {"success": False, "error": "Failed to create customer"}
            
            # Get the appropriate price ID
            price_id = (tier.stripe_price_id_monthly if billing_period == 'monthly' 
                       else tier.stripe_price_id_yearly)
            
            if not price_id:
                return {"success": False, "error": f"No Stripe price ID configured for {tier.name} {billing_period}"}
            
            # Prepare subscription parameters
            subscription_params = {
                'customer': customer_id,
                'items': [{'price': price_id}],
                'payment_behavior': 'default_incomplete',
                'payment_settings': {'save_default_payment_method': 'on_subscription'},
                'expand': ['latest_invoice.payment_intent'],
                'metadata': {
                    'user_id': str(user.id),
                    'tier_name': tier.name,
                    'billing_period': billing_period,
                }
            }
            
            # Add trial if specified
            if trial_days:
                subscription_params['trial_period_days'] = trial_days
            
            # Add payment method if provided
            if payment_method_id:
                subscription_params['default_payment_method'] = payment_method_id
            
            # Create subscription
            stripe_subscription = stripe.Subscription.create(**subscription_params)
            
            # Create or update user subscription
            user_subscription, created = UserSubscription.objects.get_or_create(
                user=user,
                defaults={
                    'tier': tier,
                    'stripe_customer_id': customer_id,
                    'stripe_subscription_id': stripe_subscription.id,
                    'status': 'inactive',
                    'billing_period': billing_period,
                    'start_date': timezone.now(),
                }
            )
            
            if not created:
                # Update existing subscription
                user_subscription.tier = tier
                user_subscription.stripe_customer_id = customer_id
                user_subscription.stripe_subscription_id = stripe_subscription.id
                user_subscription.billing_period = billing_period
                user_subscription.status = 'inactive'
                user_subscription.save()
            
            # Set trial end date if trial is active
            if trial_days:
                user_subscription.trial_end_date = timezone.now() + timezone.timedelta(days=trial_days)
                user_subscription.status = 'trialing'
                user_subscription.save()
            
            logger.info(f"Created subscription {stripe_subscription.id} for user {user.username}")
            
            return {
                "success": True,
                "subscription_id": stripe_subscription.id,
                "client_secret": stripe_subscription.latest_invoice.payment_intent.client_secret,
                "status": stripe_subscription.status,
            }
            
        except stripe.StripeError as e:
            logger.error(f"Failed to create subscription for user {user.username}: {e}")
            return {"success": False, "error": str(e)}
    
    def cancel_subscription(self, user: User, immediately: bool = False) -> Dict[str, Any]:
        """Cancel a user's subscription"""
        try:
            subscription = UserSubscription.objects.get(user=user)
            
            if not subscription.stripe_subscription_id:
                return {"success": False, "error": "No active Stripe subscription found"}
            
            if immediately:
                # Cancel immediately
                stripe.Subscription.delete(subscription.stripe_subscription_id)
                subscription.status = 'canceled'
                subscription.end_date = timezone.now()
            else:
                # Cancel at period end
                stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    cancel_at_period_end=True
                )
                subscription.status = 'canceled'
            
            subscription.save()
            
            logger.info(f"Canceled subscription for user {user.username}")
            return {"success": True, "message": "Subscription canceled"}
            
        except UserSubscription.DoesNotExist:
            return {"success": False, "error": "No subscription found"}
        except stripe.StripeError as e:
            logger.error(f"Failed to cancel subscription for user {user.username}: {e}")
            return {"success": False, "error": str(e)}
    
    def update_subscription(self, user: User, new_tier: SubscriptionTier, billing_period: str = None) -> Dict[str, Any]:
        """Update a user's subscription tier"""
        try:
            subscription = UserSubscription.objects.get(user=user)
            
            if not subscription.stripe_subscription_id:
                return {"success": False, "error": "No active Stripe subscription found"}
            
            # Get current subscription from Stripe
            stripe_subscription = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
            
            # Determine billing period
            if not billing_period:
                billing_period = subscription.billing_period
            
            # Get new price ID
            new_price_id = (new_tier.stripe_price_id_monthly if billing_period == 'monthly' 
                           else new_tier.stripe_price_id_yearly)
            
            if not new_price_id:
                return {"success": False, "error": f"No Stripe price ID configured for {new_tier.name} {billing_period}"}
            
            # Update subscription
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                items=[{
                    'id': stripe_subscription['items']['data'][0]['id'],
                    'price': new_price_id,
                }],
                proration_behavior='create_prorations',
            )
            
            # Update local subscription
            subscription.tier = new_tier
            subscription.billing_period = billing_period
            subscription.save()
            
            logger.info(f"Updated subscription for user {user.username} to {new_tier.name}")
            return {"success": True, "message": "Subscription updated"}
            
        except UserSubscription.DoesNotExist:
            return {"success": False, "error": "No subscription found"}
        except stripe.StripeError as e:
            logger.error(f"Failed to update subscription for user {user.username}: {e}")
            return {"success": False, "error": str(e)}
    
    def handle_webhook(self, payload: bytes, sig_header: str) -> Dict[str, Any]:
        """Handle Stripe webhook events"""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
        except ValueError:
            logger.error("Invalid payload in Stripe webhook")
            return {"success": False, "error": "Invalid payload"}
        except stripe.SignatureVerificationError:
            logger.error("Invalid signature in Stripe webhook")
            return {"success": False, "error": "Invalid signature"}
        
        # Handle the event
        if event['type'] == 'invoice.payment_succeeded':
            self._handle_payment_succeeded(event['data']['object'])
        elif event['type'] == 'invoice.payment_failed':
            self._handle_payment_failed(event['data']['object'])
        elif event['type'] == 'customer.subscription.updated':
            self._handle_subscription_updated(event['data']['object'])
        elif event['type'] == 'customer.subscription.deleted':
            self._handle_subscription_deleted(event['data']['object'])
        else:
            logger.info(f"Unhandled Stripe webhook event: {event['type']}")
        
        return {"success": True}
    
    def _handle_payment_succeeded(self, invoice):
        """Handle successful payment"""
        try:
            subscription_id = invoice.get('subscription')
            if not subscription_id:
                return
            
            user_subscription = UserSubscription.objects.get(
                stripe_subscription_id=subscription_id
            )
            
            # Update subscription status
            user_subscription.status = 'active'
            user_subscription.last_payment_date = timezone.now()
            
            # Set next payment date
            if invoice.get('next_payment_attempt'):
                user_subscription.next_payment_date = timezone.datetime.fromtimestamp(
                    invoice['next_payment_attempt'], tz=timezone.utc
                )
            
            user_subscription.save()
            
            # Record payment history
            PaymentHistory.objects.create(
                user=user_subscription.user,
                subscription=user_subscription,
                stripe_payment_intent_id=invoice.get('payment_intent', ''),
                stripe_invoice_id=invoice.get('id', ''),
                amount=Decimal(str(invoice.get('amount_paid', 0) / 100)),  # Convert cents to dollars
                currency=invoice.get('currency', 'USD').upper(),
                status='succeeded',
                payment_date=timezone.now()
            )
            
            logger.info(f"Payment succeeded for subscription {subscription_id}")
            
        except UserSubscription.DoesNotExist:
            logger.error(f"User subscription not found for Stripe subscription {subscription_id}")
        except Exception as e:
            logger.error(f"Error handling payment success: {e}")
    
    def _handle_payment_failed(self, invoice):
        """Handle failed payment"""
        try:
            subscription_id = invoice.get('subscription')
            if not subscription_id:
                return
            
            user_subscription = UserSubscription.objects.get(
                stripe_subscription_id=subscription_id
            )
            
            # Update subscription status
            user_subscription.status = 'past_due'
            user_subscription.save()
            
            # Record payment history
            PaymentHistory.objects.create(
                user=user_subscription.user,
                subscription=user_subscription,
                stripe_payment_intent_id=invoice.get('payment_intent', ''),
                stripe_invoice_id=invoice.get('id', ''),
                amount=Decimal(str(invoice.get('amount_due', 0) / 100)),
                currency=invoice.get('currency', 'USD').upper(),
                status='failed',
                payment_date=timezone.now()
            )
            
            logger.warning(f"Payment failed for subscription {subscription_id}")
            
        except UserSubscription.DoesNotExist:
            logger.error(f"User subscription not found for Stripe subscription {subscription_id}")
        except Exception as e:
            logger.error(f"Error handling payment failure: {e}")
    
    def _handle_subscription_updated(self, subscription):
        """Handle subscription updates"""
        try:
            user_subscription = UserSubscription.objects.get(
                stripe_subscription_id=subscription['id']
            )
            
            # Update status based on Stripe status
            stripe_status = subscription['status']
            if stripe_status == 'active':
                user_subscription.status = 'active'
            elif stripe_status == 'past_due':
                user_subscription.status = 'past_due'
            elif stripe_status == 'canceled':
                user_subscription.status = 'canceled'
            elif stripe_status == 'unpaid':
                user_subscription.status = 'unpaid'
            elif stripe_status == 'trialing':
                user_subscription.status = 'trialing'
            
            user_subscription.save()
            
            logger.info(f"Updated subscription {subscription['id']} status to {stripe_status}")
            
        except UserSubscription.DoesNotExist:
            logger.error(f"User subscription not found for Stripe subscription {subscription['id']}")
        except Exception as e:
            logger.error(f"Error handling subscription update: {e}")
    
    def _handle_subscription_deleted(self, subscription):
        """Handle subscription deletion"""
        try:
            user_subscription = UserSubscription.objects.get(
                stripe_subscription_id=subscription['id']
            )
            
            user_subscription.status = 'canceled'
            user_subscription.end_date = timezone.now()
            user_subscription.save()
            
            logger.info(f"Subscription {subscription['id']} deleted")
            
        except UserSubscription.DoesNotExist:
            logger.error(f"User subscription not found for Stripe subscription {subscription['id']}")
        except Exception as e:
            logger.error(f"Error handling subscription deletion: {e}")
    
    def get_subscription_details(self, user: User) -> Dict[str, Any]:
        """Get detailed subscription information"""
        try:
            subscription = UserSubscription.objects.get(user=user)
            
            # Get Stripe subscription details
            stripe_subscription = None
            if subscription.stripe_subscription_id:
                try:
                    stripe_subscription = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
                except stripe.StripeError:
                    logger.warning(f"Could not retrieve Stripe subscription {subscription.stripe_subscription_id}")
            
            # Get recent payments
            recent_payments = PaymentHistory.objects.filter(
                user=user
            ).order_by('-payment_date')[:5]
            
            return {
                "success": True,
                "subscription": {
                    "tier": subscription.tier.name,
                    "display_name": subscription.tier.display_name,
                    "status": subscription.status,
                    "billing_period": subscription.billing_period,
                    "start_date": subscription.start_date,
                    "end_date": subscription.end_date,
                    "trial_end_date": subscription.trial_end_date,
                    "next_payment_date": subscription.next_payment_date,
                    "is_active": subscription.is_active,
                    "is_trial": subscription.is_trial,
                    "days_until_renewal": subscription.days_until_renewal,
                },
                "stripe_details": stripe_subscription,
                "recent_payments": [
                    {
                        "amount": payment.amount,
                        "currency": payment.currency,
                        "status": payment.status,
                        "date": payment.payment_date,
                    }
                    for payment in recent_payments
                ]
            }
            
        except UserSubscription.DoesNotExist:
            return {"success": False, "error": "No subscription found"}
        except Exception as e:
            logger.error(f"Error getting subscription details for user {user.username}: {e}")
            return {"success": False, "error": str(e)}
