"""
Complete billing views with dashboard endpoint
"""

import stripe
import uuid
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.request import Request

# Import from billing models
from .models import PaymentMethod, Invoice
# Import from core models
from apps.core.models.payment_models import SubscriptionTier, UserSubscription, PaymentHistory
from .serializers import (
    SubscriptionTierSerializer, UserSubscriptionSerializer, PaymentHistorySerializer,
    InvoiceSerializer, PaymentMethodSerializer, BillingDashboardSerializer,
    SubscriptionChangeSerializer, PaymentMethodCreateSerializer
)

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

# Configure logging
logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def billing_dashboard(request: Request):
    """Get complete billing dashboard data"""
    try:
        # Get current subscription
        current_subscription = UserSubscription.objects.select_related('tier').get(user=request.user)
    except UserSubscription.DoesNotExist:
        # Create free tier subscription if none exists
        free_tier = SubscriptionTier.objects.get(name='free')
        current_subscription = UserSubscription.objects.create(
            user=request.user,
            tier=free_tier,
            status='active'
        )
    
    # Get payment methods
    payment_methods = PaymentMethod.objects.filter(user=request.user).order_by('-is_default', '-created_at')
    
    # Get recent payments (last 10)
    recent_payments = PaymentHistory.objects.filter(user=request.user).order_by('-payment_date')[:10]
    
    # Get upcoming invoices
    upcoming_invoices = Invoice.objects.filter(
        user=request.user, 
        status__in=['draft', 'open']
    ).order_by('due_date')[:5]
    
    # Get available tiers
    available_tiers = SubscriptionTier.objects.filter(is_active=True).order_by('price_monthly')
    
    dashboard_data = {
        'current_subscription': current_subscription,
        'payment_methods': payment_methods,
        'recent_payments': recent_payments,
        'upcoming_invoices': upcoming_invoices,
        'available_tiers': available_tiers
    }
    
    serializer = BillingDashboardSerializer(dashboard_data)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def subscription_tiers(request: Request):
    """Get all available subscription tiers"""
    tiers = SubscriptionTier.objects.filter(is_active=True).order_by('price_monthly')
    serializer = SubscriptionTierSerializer(tiers, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def current_subscription(request: Request):
    """Get current user subscription"""
    try:
        subscription = UserSubscription.objects.select_related('tier').get(user=request.user)
        serializer = UserSubscriptionSerializer(subscription)
        return Response(serializer.data)
    except UserSubscription.DoesNotExist:
        return Response({'error': 'No active subscription found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_subscription(request: Request):
    """Create or change subscription"""
    serializer = SubscriptionChangeSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    tier_id = serializer.validated_data['tier_id']
    billing_period = serializer.validated_data['billing_period']
    
    try:
        tier = SubscriptionTier.objects.get(id=tier_id)
        
        # Get or create Stripe customer
        customer = get_or_create_stripe_customer(request.user)
        
        # Get current subscription
        try:
            current_sub = UserSubscription.objects.get(user=request.user)
            # Cancel current Stripe subscription if exists
            if current_sub.stripe_subscription_id:
                stripe.Subscription.cancel(current_sub.stripe_subscription_id)
        except UserSubscription.DoesNotExist:
            current_sub = None
        
        # Create new subscription for paid tiers
        if tier.name != 'free':
            # Get default payment method
            try:
                payment_method = PaymentMethod.objects.get(user=request.user, is_default=True)
                
                # Create Stripe subscription
                price_amount = tier.price_yearly if billing_period == 'yearly' else tier.price_monthly
                
                stripe_subscription = stripe.Subscription.create(
                    customer=customer.id,
                    items=[{
                        'price_data': {
                            'currency': 'usd',
                            'product': tier.stripe_product_id,
                            'unit_amount': int(price_amount * 100),  # Convert to cents
                            'recurring': {
                                'interval': 'year' if billing_period == 'yearly' else 'month'
                            }
                        }
                    }],
                    default_payment_method=payment_method.stripe_payment_method_id,
                )
                
                stripe_subscription_id = stripe_subscription.id
            except PaymentMethod.DoesNotExist:
                return Response({'error': 'No payment method found'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            stripe_subscription_id = None
        
        # Update or create subscription
        if current_sub:
            current_sub.tier = tier
            current_sub.billing_period = billing_period
            current_sub.stripe_subscription_id = stripe_subscription_id
            current_sub.status = 'active'
            current_sub.start_date = timezone.now()
            current_sub.save()
        else:
            current_sub = UserSubscription.objects.create(
                user=request.user,
                tier=tier,
                billing_period=billing_period,
                stripe_subscription_id=stripe_subscription_id,
                status='active'
            )
        
        serializer = UserSubscriptionSerializer(current_sub)
        return Response(serializer.data)
        
    except SubscriptionTier.DoesNotExist:
        return Response({'error': 'Invalid subscription tier'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def cancel_subscription(request: Request):
    """Cancel current subscription"""
    try:
        subscription = UserSubscription.objects.get(user=request.user)
        
        if subscription.stripe_subscription_id:
            # Cancel Stripe subscription
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True
            )
            
        subscription.cancel_at_period_end = True
        subscription.save()
        
        return Response({'message': 'Subscription will be cancelled at period end'})
        
    except UserSubscription.DoesNotExist:
        return Response({'error': 'No active subscription found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def payment_history(request: Request):
    """Get payment history"""
    payments = PaymentHistory.objects.filter(user=request.user).order_by('-payment_date')
    serializer = PaymentHistorySerializer(payments, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def invoices(request: Request):
    """Get user invoices"""
    invoices_qs = Invoice.objects.filter(user=request.user).order_by('-invoice_date')
    serializer = InvoiceSerializer(invoices_qs, many=True)
    return Response(serializer.data)


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def payment_methods(request: Request):
    """Get or add payment methods"""
    if request.method == 'GET':
        methods = PaymentMethod.objects.filter(user=request.user)
        serializer = PaymentMethodSerializer(methods, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = PaymentMethodCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        stripe_payment_method_id = serializer.validated_data['stripe_payment_method_id']
        is_default = serializer.validated_data['is_default']
        
        try:
            # Get Stripe payment method details
            payment_method = stripe.PaymentMethod.retrieve(stripe_payment_method_id)
            
            # Create payment method record
            pm = PaymentMethod.objects.create(
                user=request.user,
                stripe_payment_method_id=stripe_payment_method_id,
                type=payment_method.type,
                is_default=is_default,
                last_four=payment_method.card.last4 if payment_method.type == 'card' else '',
                brand=payment_method.card.brand if payment_method.type == 'card' else '',
                exp_month=payment_method.card.exp_month if payment_method.type == 'card' else None,
                exp_year=payment_method.card.exp_year if payment_method.type == 'card' else None,
            )
            
            # If this is default, make others non-default
            if is_default:
                PaymentMethod.objects.filter(user=request.user).exclude(id=pm.id).update(is_default=False)
            
            serializer = PaymentMethodSerializer(pm)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except stripe.error.StripeError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_payment_method(request: Request, method_id: uuid.UUID):
    """Delete a payment method"""
    try:
        method = PaymentMethod.objects.get(id=method_id, user=request.user)
        
        # Detach from Stripe
        stripe.PaymentMethod.detach(method.stripe_payment_method_id)
        
        # Delete local record
        method.delete()
        
        return Response({'message': 'Payment method deleted'})
        
    except PaymentMethod.DoesNotExist:
        return Response({'error': 'Payment method not found'}, status=status.HTTP_404_NOT_FOUND)
    except stripe.error.StripeError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_stripe_customer(request: Request):
    """Create or get Stripe customer"""
    customer = get_or_create_stripe_customer(request.user)
    return Response({'customer_id': customer.id})


@api_view(['POST'])
def stripe_webhook(request: Request):
    """Handle Stripe webhooks"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
    
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        return Response({'error': 'Invalid payload'}, status=status.HTTP_400_BAD_REQUEST)
    except stripe.error.SignatureVerificationError:
        return Response({'error': 'Invalid signature'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Handle the event
    if event['type'] == 'payment_intent.succeeded':
        handle_payment_succeeded(event['data']['object'])
    elif event['type'] == 'invoice.payment_succeeded':
        handle_invoice_payment_succeeded(event['data']['object'])
    elif event['type'] == 'customer.subscription.deleted':
        handle_subscription_cancelled(event['data']['object'])
    
    return Response({'received': True})


# Helper functions
def get_or_create_stripe_customer(user):
    """Get or create Stripe customer for user"""
    try:
        subscription = UserSubscription.objects.get(user=user)
        if subscription.stripe_customer_id:
            return stripe.Customer.retrieve(subscription.stripe_customer_id)
    except UserSubscription.DoesNotExist:
        pass
    
    # Create new customer
    customer = stripe.Customer.create(
        email=user.email,
        name=f"{user.first_name} {user.last_name}".strip() or user.username,
        metadata={'user_id': str(user.id)}
    )
    
    # Update or create subscription with customer ID
    subscription, created = UserSubscription.objects.get_or_create(
        user=user,
        defaults={'stripe_customer_id': customer.id}
    )
    if not created:
        subscription.stripe_customer_id = customer.id
        subscription.save()
    
    return customer


def handle_payment_succeeded(payment_intent):
    """Handle successful payment"""
    customer_id = payment_intent.get('customer')
    amount = payment_intent.get('amount', 0) / 100  # Convert from cents
    
    try:
        subscription = UserSubscription.objects.get(stripe_customer_id=customer_id)
        PaymentHistory.objects.create(
            user=subscription.user,
            amount=amount,
            currency=payment_intent.get('currency', 'usd'),
            status='completed',
            stripe_payment_intent_id=payment_intent['id'],
            description=f"Payment for {subscription.tier.display_name} subscription",
            payment_date=timezone.now()
        )
    except UserSubscription.DoesNotExist:
        pass


def handle_invoice_payment_succeeded(invoice):
    """Handle successful invoice payment"""
    customer_id = invoice.get('customer')
    
    try:
        subscription = UserSubscription.objects.get(stripe_customer_id=customer_id)
        
        # Update invoice status
        try:
            local_invoice = Invoice.objects.get(stripe_invoice_id=invoice['id'])
            local_invoice.status = 'paid'
            local_invoice.paid_at = timezone.now()
            local_invoice.save()
        except Invoice.DoesNotExist:
            # Create invoice record
            Invoice.objects.create(
                user=subscription.user,
                subscription=subscription,
                stripe_invoice_id=invoice['id'],
                invoice_number=invoice.get('number', ''),
                status='paid',
                subtotal=invoice.get('subtotal', 0) / 100,
                total=invoice.get('total', 0) / 100,
                amount_paid=invoice.get('amount_paid', 0) / 100,
                amount_due=invoice.get('amount_due', 0) / 100,
                currency=invoice.get('currency', 'usd'),
                invoice_date=timezone.datetime.fromtimestamp(invoice.get('created', 0)),
                due_date=timezone.datetime.fromtimestamp(invoice.get('due_date', 0)),
                paid_at=timezone.now(),
                hosted_invoice_url=invoice.get('hosted_invoice_url', ''),
                invoice_pdf_url=invoice.get('invoice_pdf', '')
            )
            
    except UserSubscription.DoesNotExist:
        pass


def handle_subscription_cancelled(subscription):
    """Handle cancelled subscription"""
    stripe_subscription_id = subscription['id']
    
    try:
        user_subscription = UserSubscription.objects.get(stripe_subscription_id=stripe_subscription_id)
        user_subscription.status = 'canceled'
        user_subscription.end_date = timezone.now()
        user_subscription.save()
    except UserSubscription.DoesNotExist:
        pass


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_checkout_session(request: Request):
    """Create Stripe checkout session for subscription upgrade"""
    try:
        tier_id = request.data.get('tier_id')
        billing_period = request.data.get('billing_period', 'monthly')
        success_url = request.data.get('success_url')
        cancel_url = request.data.get('cancel_url')
        
        if not tier_id:
            return Response({'error': 'tier_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            tier = SubscriptionTier.objects.get(id=tier_id, is_active=True)
        except SubscriptionTier.DoesNotExist:
            return Response({'error': 'Invalid subscription tier'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get price ID based on billing period
        price_id = tier.stripe_price_id_monthly if billing_period == 'monthly' else tier.stripe_price_id_yearly
        if not price_id:
            return Response({'error': f'No Stripe price configured for {tier.name} {billing_period}'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get or create Stripe customer
        customer_id = None
        try:
            user_subscription = UserSubscription.objects.get(user=request.user)
            customer_id = user_subscription.stripe_customer_id
        except UserSubscription.DoesNotExist:
            pass
        
        if not customer_id:
            # Create new customer
            try:
                customer = stripe.Customer.create(
                    email=request.user.email,
                    name=f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
                    metadata={'user_id': str(request.user.id)}
                )
                customer_id = customer.id
            except stripe.StripeError as e:
                return Response({'error': f'Failed to create customer: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Create checkout session
        try:
            checkout_session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url or f"{settings.FRONTEND_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=cancel_url or f"{settings.FRONTEND_URL}/billing",
                metadata={
                    'user_id': str(request.user.id),
                    'tier_id': str(tier.id),
                    'billing_period': billing_period,
                }
            )
            
            return Response({
                'checkout_url': checkout_session.url,
                'session_id': checkout_session.id,
                'tier_name': tier.display_name,
                'price': float(tier.price_monthly if billing_period == 'monthly' else tier.price_yearly),
                'billing_period': billing_period
            })
            
        except stripe.StripeError as e:
            return Response({'error': f'Failed to create checkout session: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    except Exception as e:
        return Response({'error': f'Unexpected error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def convert_trial_to_paid(request: Request):
    """Convert trial subscription to paid subscription"""
    try:
        profile = request.user.profile
        
        # Check if user is on trial
        if not profile.is_trial_active:
            return Response({'error': 'No active trial found'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if trial expired
        if profile.is_trial_expired():
            return Response({'error': 'Trial has already expired'}, status=status.HTTP_400_BAD_REQUEST)
        
        tier_id = request.data.get('tier_id')
        billing_period = request.data.get('billing_period', 'monthly')
        
        if tier_id:
            try:
                tier = SubscriptionTier.objects.get(id=tier_id, is_active=True)
            except SubscriptionTier.DoesNotExist:
                return Response({'error': 'Invalid subscription tier'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Use current trial tier
            tier = profile.subscription_tier
        
        # Create checkout session for the trial tier
        success_url = request.data.get('success_url', f"{settings.FRONTEND_URL}/billing/success")
        cancel_url = request.data.get('cancel_url', f"{settings.FRONTEND_URL}/billing")
        
        # Call the checkout session creation
        checkout_request_data = {
            'tier_id': str(tier.id),
            'billing_period': billing_period,
            'success_url': success_url,
            'cancel_url': cancel_url
        }
        
        # Create a new request object for checkout session creation
        from django.http import HttpRequest
        checkout_request = HttpRequest()
        checkout_request.user = request.user
        checkout_request.data = checkout_request_data
        checkout_request.method = 'POST'
        
        # Get checkout session
        response = create_checkout_session(checkout_request)
        
        if response.status_code == 200:
            return Response({
                'message': 'Checkout session created for trial conversion',
                'checkout_url': response.data['checkout_url'],
                'session_id': response.data['session_id'],
                'trial_days_left': profile.days_left_in_trial()
            })
        else:
            return response
            
    except Exception as e:
        return Response({'error': f'Failed to convert trial: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def handle_payment_success(request):
    """Handle successful payment from Stripe webhook or frontend callback"""
    try:
        session_id = request.data.get('session_id')
        subscription_id = request.data.get('subscription_id')
        
        if not session_id and not subscription_id:
            return Response({
                'error': 'session_id or subscription_id required'
            }, status=400)
        
        user_profile = request.user.userprofile
        
        # If we have a session_id, retrieve the subscription from Stripe
        if session_id:
            session = stripe.checkout.Session.retrieve(session_id)
            subscription_id = session.subscription
        
        if subscription_id:
            # Get subscription details from Stripe
            stripe_subscription = stripe.Subscription.retrieve(subscription_id)
            price_id = stripe_subscription.items.data[0].price.id

            # Find tier by matching either monthly or yearly price id
            subscription_tier = SubscriptionTier.objects.filter(
                Q(stripe_price_id_monthly=price_id) | Q(stripe_price_id_yearly=price_id),
                is_active=True
            ).first()

            if not subscription_tier:
                return Response({'error': 'No matching tier for Stripe price ID'}, status=400)
            
            # Update user's subscription
            user_profile.subscription_tier = subscription_tier
            user_profile.is_trial = False
            user_profile.trial_end_date = None
            user_profile.save()
            
            # Create or update UserSubscription record
            user_subscription, created = UserSubscription.objects.get_or_create(
                user=request.user,
                defaults={
                    'tier': subscription_tier,
                    'stripe_subscription_id': subscription_id,
                    'status': stripe_subscription.status,
                    'current_period_start': timezone.datetime.fromtimestamp(
                        stripe_subscription.current_period_start, tz=timezone.utc
                    ),
                    'current_period_end': timezone.datetime.fromtimestamp(
                        stripe_subscription.current_period_end, tz=timezone.utc
                    )
                }
            )
            
            if not created:
                user_subscription.tier = subscription_tier
                user_subscription.stripe_subscription_id = subscription_id
                user_subscription.status = stripe_subscription.status
                user_subscription.current_period_start = timezone.datetime.fromtimestamp(
                    stripe_subscription.current_period_start, tz=timezone.utc
                )
                user_subscription.current_period_end = timezone.datetime.fromtimestamp(
                    stripe_subscription.current_period_end, tz=timezone.utc
                )
                user_subscription.save()
            
            # Send confirmation email (if task exists) using dynamic import to avoid static import errors
            try:
                from importlib import import_module
                tasks_module = import_module('apps.billing.tasks')
                if hasattr(tasks_module, 'send_subscription_confirmation_email'):
                    tasks_module.send_subscription_confirmation_email.delay(request.user.id, subscription_tier.name)
            except Exception:
                pass  # Task not implemented yet or import failed
            
            return Response({
                'success': True,
                'message': f'Successfully upgraded to {subscription_tier.name}',
                'subscription_tier': subscription_tier.name
            })
        
        return Response({
            'error': 'No valid subscription found'
        }, status=400)
        
    except Exception as e:
        logger.error(f"Payment success handling error: {str(e)}")
        return Response({
            'error': 'Internal server error'
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_subscription(request):
    """Cancel user's current subscription"""
    try:
        user_profile = request.user.userprofile
        
        # Get user's current subscription
        user_subscription = UserSubscription.objects.filter(
            user=request.user, 
            status='active'
        ).first()
        
        if not user_subscription or not user_subscription.stripe_subscription_id:
            return Response({
                'error': 'No active subscription found'
            }, status=400)
        
        # Cancel subscription in Stripe
        stripe.Subscription.modify(
            user_subscription.stripe_subscription_id,
            cancel_at_period_end=True
        )
        # Do not change local status here; webhook will update to 'canceled' when effective
        return Response({
            'success': True,
            'message': 'Subscription will be canceled at the end of the current period'
        })
        
    except Exception as e:
        logger.error(f"Subscription cancellation error: {str(e)}")
        return Response({
            'error': 'Failed to cancel subscription'
        }, status=500)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def stripe_webhook(request):
    """Handle Stripe webhooks"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        return Response(status=400)
    except stripe.error.SignatureVerificationError:
        return Response(status=400)

    # Handle different webhook events
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        # Handle successful checkout
        logger.info(f"Checkout session completed: {session['id']}")
        
    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        # Update subscription status
        try:
            user_subscription = UserSubscription.objects.get(
                stripe_subscription_id=subscription['id']
            )
            user_subscription.status = subscription['status']
            user_subscription.save()
            
            # If subscription was canceled, downgrade user
            if subscription['status'] == 'canceled':
                user_profile = user_subscription.user.userprofile
                free_tier = SubscriptionTier.objects.get(name='free')
                user_profile.subscription_tier = free_tier
                user_profile.save()
                
        except UserSubscription.DoesNotExist:
            logger.warning(f"UserSubscription not found for Stripe subscription: {subscription['id']}")
            
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        # Handle subscription deletion
        try:
            user_subscription = UserSubscription.objects.get(
                stripe_subscription_id=subscription['id']
            )
            user_subscription.status = 'canceled'
            user_subscription.save()
            
            # Downgrade user to free tier
            user_profile = user_subscription.user.userprofile
            free_tier = SubscriptionTier.objects.get(name='free')
            user_profile.subscription_tier = free_tier
            user_profile.save()
            
        except UserSubscription.DoesNotExist:
            logger.warning(f"UserSubscription not found for Stripe subscription: {subscription['id']}")

    return Response(status=200)


@api_view(['GET'])
@permission_classes([AllowAny])
def subscription_tiers_list(request):
    """List all available subscription tiers for frontend display"""
    try:
        tiers = SubscriptionTier.objects.filter(is_active=True).order_by('price_monthly')
        tiers_data = []
        
        for tier in tiers:
            tiers_data.append({
                'id': str(tier.id),
                'name': tier.name,
                'display_name': tier.display_name,
                'description': tier.description,
                'price_monthly': float(tier.price_monthly),
                'price_yearly': float(tier.price_yearly),
                'features': {
                    'max_social_accounts': tier.max_social_accounts,
                    'max_scheduled_posts': tier.max_scheduled_posts,
                    'max_team_members': tier.max_team_members,
                    'analytics_retention_days': tier.analytics_retention_days,
                    'advanced_analytics': tier.advanced_analytics,
                    'priority_support': tier.priority_support,
                    'white_label': tier.white_label,
                    'custom_branding': tier.custom_branding,
                    'bulk_upload_scheduling': tier.bulk_upload_scheduling,
                    'hashtag_suggestions': tier.hashtag_suggestions,
                    'best_time_insights': tier.best_time_insights,
                    'approval_workflows': tier.approval_workflows,
                    'phone_support': tier.phone_support,
                    'dedicated_account_manager': tier.dedicated_account_manager,
                }
            })
        
        return Response({
            'success': True,
            'tiers': tiers_data
        })
    except Exception as e:
        logger.error(f"Error fetching subscription tiers: {str(e)}")
        return Response({
            'error': 'Failed to fetch subscription tiers'
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_customer_portal_session(request):
    """Create Stripe customer portal session for subscription management"""
    try:
        # Get user's subscription
        user_subscription = UserSubscription.objects.filter(user=request.user).first()
        
        if not user_subscription or not user_subscription.stripe_customer_id:
            return Response({
                'error': 'No subscription found. Please subscribe first.'
            }, status=400)
        
        # Create portal session
        portal_session = stripe.billing_portal.Session.create(
            customer=user_subscription.stripe_customer_id,
            return_url=f"{settings.FRONTEND_URL}/billing"
        )
        
        return Response({
            'success': True,
            'portal_url': portal_session.url
        })
        
    except stripe.StripeError as e:
        logger.error(f"Stripe error creating portal session: {str(e)}")
        return Response({
            'error': 'Failed to create customer portal session'
        }, status=500)
    except Exception as e:
        logger.error(f"Error creating portal session: {str(e)}")
        return Response({
            'error': 'Internal server error'
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_subscription_status(request):
    """Get current user's subscription status"""
    try:
        user_subscription = UserSubscription.objects.filter(user=request.user).first()
        
        if not user_subscription:
            return Response({
                'success': True,
                'subscription': None,
                'message': 'No active subscription'
            })
        
        # Get subscription details from Stripe
        stripe_subscription = None
        if user_subscription.stripe_subscription_id:
            try:
                stripe_subscription = stripe.Subscription.retrieve(user_subscription.stripe_subscription_id)
            except stripe.StripeError as e:
                logger.warning(f"Failed to retrieve Stripe subscription: {str(e)}")
        
        subscription_data = {
            'id': str(user_subscription.id),
            'tier': {
                'id': str(user_subscription.tier.id),
                'name': user_subscription.tier.name,
                'display_name': user_subscription.tier.display_name,
                'price_monthly': float(user_subscription.tier.price_monthly),
                'price_yearly': float(user_subscription.tier.price_yearly),
            },
            'status': user_subscription.status,
            'billing_period': user_subscription.billing_period,
            'current_period_start': user_subscription.current_period_start,
            'current_period_end': user_subscription.current_period_end,
            'next_payment_date': user_subscription.next_payment_date,
            'stripe_status': stripe_subscription.status if stripe_subscription else None,
            'cancel_at_period_end': stripe_subscription.cancel_at_period_end if stripe_subscription else False,
        }
        
        return Response({
            'success': True,
            'subscription': subscription_data
        })
        
    except Exception as e:
        logger.error(f"Error getting subscription status: {str(e)}")
        return Response({
            'error': 'Failed to get subscription status'
        }, status=500)
