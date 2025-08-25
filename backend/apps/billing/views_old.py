import stripe
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
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
        # Create free tier subscription if none exists
        free_tier = SubscriptionTier.objects.get(name='free')
        subscription = UserSubscription.objects.create(
            user=request.user,
            tier=free_tier,
            status='active'
        )
        serializer = UserSubscriptionSerializer(subscription)
        return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_subscription(request: Request):
    """Create a new subscription"""
    tier_id = request.data.get('tier_id')
    billing_period = request.data.get('billing_period', 'monthly')
    payment_method_id = request.data.get('payment_method_id')
    
    try:
        tier = SubscriptionTier.objects.get(id=tier_id)
        
        # Get or create Stripe customer
        customer = get_or_create_stripe_customer(request.user)
        
        # Attach payment method if provided
        if payment_method_id:
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer.id,
            )
        
        # Create Stripe subscription
        price_id = tier.stripe_price_id_yearly if billing_period == 'yearly' else tier.stripe_price_id_monthly
        
        stripe_subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[{'price': price_id}],
            default_payment_method=payment_method_id,
            expand=['latest_invoice.payment_intent'],
        )
        
        # Update or create user subscription
        subscription, created = UserSubscription.objects.update_or_create(
            user=request.user,
            defaults={
                'tier': tier,
                'status': 'active' if stripe_subscription.status == 'active' else 'inactive',
                'billing_period': billing_period,
                'stripe_customer_id': customer.id,
                'stripe_subscription_id': stripe_subscription.id,
                'start_date': timezone.now(),
                'next_payment_date': timezone.now() + timedelta(days=30 if billing_period == 'monthly' else 365)
            }
        )
        
        return Response({
            'subscription_id': str(subscription.id),
            'client_secret': stripe_subscription.latest_invoice.payment_intent.client_secret,
            'status': stripe_subscription.status
        })
        
    except SubscriptionTier.DoesNotExist:
        return Response({'error': 'Invalid tier'}, status=status.HTTP_400_BAD_REQUEST)
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
        
        subscription.status = 'canceled'
        subscription.save()
        
        return Response({'message': 'Subscription canceled successfully'})
        
    except UserSubscription.DoesNotExist:
        return Response({'error': 'No active subscription'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def payment_history(request: Request):
    """Get user payment history"""
    payments = PaymentHistory.objects.filter(user=request.user).order_by('-payment_date')
    serializer = PaymentHistorySerializer(payments, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def invoices(request: Request):
    """Get user invoices"""
    invoices = Invoice.objects.filter(user=request.user).order_by('-issue_date')
    serializer = InvoiceSerializer(invoices, many=True)
    return Response(serializer.data)


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def payment_methods(request: Request):
    """Get or add payment methods"""
    if request.method == 'GET':
        methods = PaymentMethod.objects.filter(user=request.user, is_active=True)
        serializer = PaymentMethodSerializer(methods, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        payment_method_id = request.data.get('payment_method_id')
        
        try:
            # Get Stripe payment method details
            stripe_pm = stripe.PaymentMethod.retrieve(payment_method_id)
            
            # Create payment method record
            payment_method = PaymentMethod.objects.create(
                user=request.user,
                type='card',
                last_four=stripe_pm.card.last4,
                brand=stripe_pm.card.brand,
                exp_month=stripe_pm.card.exp_month,
                exp_year=stripe_pm.card.exp_year,
                stripe_payment_method_id=payment_method_id,
                is_default=not PaymentMethod.objects.filter(user=request.user, is_active=True).exists()
            )
            
            serializer = PaymentMethodSerializer(payment_method)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_payment_method(request: Request, method_id):
    """Delete a payment method"""
    try:
        payment_method = PaymentMethod.objects.get(id=method_id, user=request.user)
        
        # Detach from Stripe
        if payment_method.stripe_payment_method_id:
            stripe.PaymentMethod.detach(payment_method.stripe_payment_method_id)
        
        payment_method.is_active = False
        payment_method.save()
        
        return Response({'message': 'Payment method deleted'})
        
    except PaymentMethod.DoesNotExist:
        return Response({'error': 'Payment method not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_stripe_customer(request: Request):
    """Create Stripe customer"""
    try:
        customer = get_or_create_stripe_customer(request.user)
        return Response({
            'customer_id': customer.id,
            'client_secret': create_setup_intent(customer.id)
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Helper functions
def get_or_create_stripe_customer(user: User):
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
    
    # Update or create subscription record
    subscription, created = UserSubscription.objects.get_or_create(
        user=user,
        defaults={'tier': SubscriptionTier.objects.get(name='free')}
    )
    subscription.stripe_customer_id = customer.id
    subscription.save()
    
    return customer


def create_setup_intent(customer_id: str):
    """Create setup intent for saving payment method"""
    setup_intent = stripe.SetupIntent.create(
        customer=customer_id,
        payment_method_types=['card'],
    )
    return setup_intent.client_secret


def get_posts_count(user: User, month_start):
    """Get posts count for current month"""
    from apps.posts.models import Post
    try:
        return Post.objects.filter(
            user=user,
            created_at__gte=month_start,
            created_at__lt=month_start + timedelta(days=32)
        ).count()
    except:
        return 0


def get_connected_accounts_count(user: User):
    """Get connected social accounts count"""
    from apps.authentication.models import SocialMediaAccount
    try:
        return SocialMediaAccount.objects.filter(user=user, is_active=True).count()
    except:
        return 0


def get_team_members_count(user: User):
    """Get team members count"""
    from apps.collaborators.models import Collaborator
    try:
        return Collaborator.objects.filter(creator=user, is_active=True).count()
    except:
        return 0


# Webhook handler for Stripe events
@api_view(['POST'])
@permission_classes([])  # Public endpoint
def stripe_webhook(request: Request):
    """Handle Stripe webhook events"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return Response({'error': 'Invalid payload'}, status=status.HTTP_400_BAD_REQUEST)
    except stripe.error.SignatureVerificationError:
        return Response({'error': 'Invalid signature'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Handle the event
    if event['type'] == 'payment_intent.succeeded':
        handle_payment_succeeded(event['data']['object'])
    elif event['type'] == 'invoice.payment_succeeded':
        handle_invoice_payment_succeeded(event['data']['object'])
    elif event['type'] == 'customer.subscription.updated':
        handle_subscription_updated(event['data']['object'])
    elif event['type'] == 'customer.subscription.deleted':
        handle_subscription_deleted(event['data']['object'])
    
    return Response({'status': 'success'})


def handle_payment_succeeded(payment_intent):
    """Handle successful payment"""
    customer_id = payment_intent['customer']
    amount = Decimal(str(payment_intent['amount'])) / 100  # Convert from cents
    
    try:
        subscription = UserSubscription.objects.get(stripe_customer_id=customer_id)
        
        PaymentHistory.objects.create(
            user=subscription.user,
            subscription=subscription,
            amount=amount,
            currency=payment_intent['currency'].upper(),
            status='succeeded',
            stripe_payment_intent_id=payment_intent['id'],
            description=f"Payment for {subscription.tier.display_name} subscription"
        )
        
        subscription.last_payment_date = timezone.now()
        subscription.save()
        
    except UserSubscription.DoesNotExist:
        pass


def handle_invoice_payment_succeeded(invoice):
    """Handle successful invoice payment"""
    customer_id = invoice['customer']
    
    try:
        subscription = UserSubscription.objects.get(stripe_customer_id=customer_id)
        subscription.status = 'active'
        subscription.save()
    except UserSubscription.DoesNotExist:
        pass


def handle_subscription_updated(subscription_obj):
    """Handle subscription updates"""
    customer_id = subscription_obj['customer']
    
    try:
        subscription = UserSubscription.objects.get(stripe_customer_id=customer_id)
        subscription.status = subscription_obj['status']
        subscription.save()
    except UserSubscription.DoesNotExist:
        pass


def handle_subscription_deleted(subscription_obj):
    """Handle subscription deletion"""
    customer_id = subscription_obj['customer']
    
    try:
        subscription = UserSubscription.objects.get(stripe_customer_id=customer_id)
        subscription.status = 'canceled'
        subscription.save()
    except UserSubscription.DoesNotExist:
        pass
