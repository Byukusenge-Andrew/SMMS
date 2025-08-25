"""
Complete billing views with dashboard endpoint
"""

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
        user_subscription.status = 'cancelled'
        user_subscription.end_date = timezone.now()
        user_subscription.save()
    except UserSubscription.DoesNotExist:
        pass
