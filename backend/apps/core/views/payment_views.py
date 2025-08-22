"""
API views for payment and subscription management
"""
import logging
from decimal import Decimal
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from django.contrib.auth.models import User
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import HttpResponse
import stripe

from ..models.payment_models import SubscriptionTier, UserSubscription, PaymentHistory
from ..services.stripe_service import StripePaymentService
from ..serializers.payment_serializers import (
    SubscriptionTierSerializer,
    SubscriptionTierCreateUpdateSerializer,
    UserSubscriptionSerializer,
    PaymentHistorySerializer,
)

logger = logging.getLogger(__name__)


@extend_schema(
    operation_id="get_subscription_tiers",
    responses={
        200: OpenApiResponse(description="List of available subscription tiers"),
    },
    summary="Get subscription tiers",
    description="Get all available subscription tiers with features and pricing"
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_subscription_tiers(request):
    """Get all available subscription tiers"""
    try:
        tiers = SubscriptionTier.objects.filter(is_active=True).order_by('price_monthly')
        
        tier_data = []
        for tier in tiers:
            tier_data.append({
                'id': str(tier.id),
                'name': tier.name,
                'display_name': tier.display_name,
                'description': tier.description,
                'price_monthly': tier.price_monthly,
                'price_yearly': tier.price_yearly,
                'features': {
                    'max_social_accounts': tier.max_social_accounts,
                    'max_scheduled_posts': tier.max_scheduled_posts,
                    'max_team_members': tier.max_team_members,
                    'analytics_retention_days': tier.analytics_retention_days,
                    'api_rate_limit': tier.api_rate_limit,
                    'gohighlevel_integration': tier.gohighlevel_integration,
                    'advanced_analytics': tier.advanced_analytics,
                    'priority_support': tier.priority_support,
                    'white_label': tier.white_label,
                }
            })
        
        return Response({
            'success': True,
            'tiers': tier_data
        })
        
    except Exception as e:
        logger.error(f"Error fetching subscription tiers: {e}")
        return Response({
            'success': False,
            'error': 'Failed to fetch subscription tiers'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    operation_id="get_user_subscription",
    responses={
        200: OpenApiResponse(description="User subscription details"),
        404: OpenApiResponse(description="No subscription found"),
    },
    summary="Get user subscription",
    description="Get current user's subscription details and payment history"
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_user_subscription(request):
    """Get current user's subscription details"""
    try:
        stripe_service = StripePaymentService()
        subscription_details = stripe_service.get_subscription_details(request.user)
        
        return Response(subscription_details)
        
    except Exception as e:
        logger.error(f"Error fetching user subscription: {e}")
        return Response({
            'success': False,
            'error': 'Failed to fetch subscription details'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    operation_id="create_subscription",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'tier_id': {'type': 'string', 'description': 'Subscription tier ID'},
                'billing_period': {'type': 'string', 'enum': ['monthly', 'yearly'], 'description': 'Billing period'},
                'payment_method_id': {'type': 'string', 'description': 'Stripe payment method ID'},
                'trial_days': {'type': 'integer', 'description': 'Number of trial days (optional)'},
            },
            'required': ['tier_id', 'billing_period']
        }
    },
    responses={
        200: OpenApiResponse(description="Subscription created successfully"),
        400: OpenApiResponse(description="Invalid request data"),
        404: OpenApiResponse(description="Tier not found"),
    },
    summary="Create subscription",
    description="Create a new subscription for the user"
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_subscription(request):
    """Create a new subscription for the user"""
    try:
        data = request.data
        tier_id = data.get('tier_id')
        billing_period = data.get('billing_period', 'monthly')
        payment_method_id = data.get('payment_method_id')
        trial_days = data.get('trial_days')
        
        if not tier_id:
            return Response({
                'success': False,
                'error': 'tier_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if billing_period not in ['monthly', 'yearly']:
            return Response({
                'success': False,
                'error': 'billing_period must be monthly or yearly'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get subscription tier
        try:
            tier = SubscriptionTier.objects.get(id=tier_id, is_active=True)
        except SubscriptionTier.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Subscription tier not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Create subscription using Stripe service
        stripe_service = StripePaymentService()
        result = stripe_service.create_subscription(
            user=request.user,
            tier=tier,
            billing_period=billing_period,
            payment_method_id=payment_method_id,
            trial_days=trial_days
        )
        
        return Response(result)
        
    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        return Response({
            'success': False,
            'error': 'Failed to create subscription'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    operation_id="update_subscription",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'tier_id': {'type': 'string', 'description': 'New subscription tier ID'},
                'billing_period': {'type': 'string', 'enum': ['monthly', 'yearly'], 'description': 'Billing period'},
            },
            'required': ['tier_id']
        }
    },
    responses={
        200: OpenApiResponse(description="Subscription updated successfully"),
        400: OpenApiResponse(description="Invalid request data"),
        404: OpenApiResponse(description="Subscription or tier not found"),
    },
    summary="Update subscription",
    description="Update user's subscription tier"
)
@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def update_subscription(request):
    """Update user's subscription tier"""
    try:
        data = request.data
        tier_id = data.get('tier_id')
        billing_period = data.get('billing_period')
        
        if not tier_id:
            return Response({
                'success': False,
                'error': 'tier_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get new subscription tier
        try:
            new_tier = SubscriptionTier.objects.get(id=tier_id, is_active=True)
        except SubscriptionTier.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Subscription tier not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Update subscription using Stripe service
        stripe_service = StripePaymentService()
        result = stripe_service.update_subscription(
            user=request.user,
            new_tier=new_tier,
            billing_period=billing_period
        )
        
        return Response(result)
        
    except Exception as e:
        logger.error(f"Error updating subscription: {e}")
        return Response({
            'success': False,
            'error': 'Failed to update subscription'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    operation_id="cancel_subscription",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'immediately': {'type': 'boolean', 'description': 'Cancel immediately or at period end'},
            }
        }
    },
    responses={
        200: OpenApiResponse(description="Subscription canceled successfully"),
        404: OpenApiResponse(description="No subscription found"),
    },
    summary="Cancel subscription",
    description="Cancel user's subscription"
)
@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def cancel_subscription(request):
    """Cancel user's subscription"""
    try:
        immediately = request.data.get('immediately', False)
        
        # Cancel subscription using Stripe service
        stripe_service = StripePaymentService()
        result = stripe_service.cancel_subscription(
            user=request.user,
            immediately=immediately
        )
        
        return Response(result)
        
    except Exception as e:
        logger.error(f"Error canceling subscription: {e}")
        return Response({
            'success': False,
            'error': 'Failed to cancel subscription'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    operation_id="get_payment_history",
    parameters=[
        OpenApiParameter('limit', int, description='Number of payments to return'),
        OpenApiParameter('offset', int, description='Offset for pagination'),
    ],
    responses={
        200: OpenApiResponse(description="Payment history"),
    },
    summary="Get payment history",
    description="Get user's payment transaction history"
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_payment_history(request):
    """Get user's payment history"""
    try:
        limit = int(request.GET.get('limit', 20))
        offset = int(request.GET.get('offset', 0))
        
        payments = PaymentHistory.objects.filter(
            user=request.user
        ).order_by('-payment_date')[offset:offset + limit]
        
        payment_data = []
        for payment in payments:
            payment_data.append({
                'id': str(payment.id),
                'amount': payment.amount,
                'currency': payment.currency,
                'status': payment.status,
                'payment_date': payment.payment_date,
                'stripe_payment_intent_id': payment.stripe_payment_intent_id,
                'subscription_tier': payment.subscription.tier.display_name if payment.subscription else None,
            })
        
        total_count = PaymentHistory.objects.filter(user=request.user).count()
        
        return Response({
            'success': True,
            'payments': payment_data,
            'total_count': total_count,
            'has_more': offset + limit < total_count
        })
        
    except Exception as e:
        logger.error(f"Error fetching payment history: {e}")
        return Response({
            'success': False,
            'error': 'Failed to fetch payment history'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    operation_id="create_stripe_customer",
    responses={
        200: OpenApiResponse(description="Stripe customer created"),
        400: OpenApiResponse(description="Failed to create customer"),
    },
    summary="Create Stripe customer",
    description="Create a Stripe customer for the current user"
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_stripe_customer(request):
    """Create a Stripe customer for the user"""
    try:
        stripe_service = StripePaymentService()
        customer_id = stripe_service.get_or_create_customer(request.user)
        
        if customer_id:
            return Response({
                'success': True,
                'customer_id': customer_id
            })
        else:
            return Response({
                'success': False,
                'error': 'Failed to create Stripe customer'
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error creating Stripe customer: {e}")
        return Response({
            'success': False,
            'error': 'Failed to create customer'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def stripe_webhook(request):
    """Handle Stripe webhook events"""
    try:
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        
        if not sig_header:
            return HttpResponse(status=400)
        
        # Handle webhook using Stripe service
        stripe_service = StripePaymentService()
        result = stripe_service.handle_webhook(payload, sig_header)
        
        if result['success']:
            return HttpResponse(status=200)
        else:
            logger.error(f"Stripe webhook error: {result['error']}")
            return HttpResponse(status=400)
            
    except Exception as e:
        logger.error(f"Error handling Stripe webhook: {e}")
        return HttpResponse(status=400)


@extend_schema(
    operation_id="create_subscription_tier",
    request=SubscriptionTierCreateUpdateSerializer,
    responses={
        201: OpenApiResponse(description="Subscription tier created successfully"),
        400: OpenApiResponse(description="Invalid request data"),
        403: OpenApiResponse(description="Permission denied"),
    },
    summary="Create subscription tier",
    description="Create a new subscription tier (admin only)"
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_subscription_tier(request):
    """Create a new subscription tier (admin only)"""
    try:
        # Check if user is admin/staff
        if not request.user.is_staff:
            return Response({
                'success': False,
                'error': 'Only administrators can create subscription tiers'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = SubscriptionTierCreateUpdateSerializer(data=request.data)
        if serializer.is_valid():
            tier = serializer.save()
            response_serializer = SubscriptionTierSerializer(tier)
            
            return Response({
                'success': True,
                'tier': response_serializer.data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error creating subscription tier: {e}")
        return Response({
            'success': False,
            'error': 'Failed to create subscription tier'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    operation_id="update_subscription_tier",
    request=SubscriptionTierCreateUpdateSerializer,
    responses={
        200: OpenApiResponse(description="Subscription tier updated successfully"),
        400: OpenApiResponse(description="Invalid request data"),
        403: OpenApiResponse(description="Permission denied"),
        404: OpenApiResponse(description="Subscription tier not found"),
    },
    summary="Update subscription tier",
    description="Update an existing subscription tier (admin only)"
)
@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def update_subscription_tier(request, tier_id):
    """Update an existing subscription tier (admin only)"""
    try:
        # Check if user is admin/staff
        if not request.user.is_staff:
            return Response({
                'success': False,
                'error': 'Only administrators can update subscription tiers'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get subscription tier
        try:
            tier = SubscriptionTier.objects.get(id=tier_id)
        except SubscriptionTier.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Subscription tier not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = SubscriptionTierCreateUpdateSerializer(tier, data=request.data, partial=True)
        if serializer.is_valid():
            tier = serializer.save()
            response_serializer = SubscriptionTierSerializer(tier)
            
            return Response({
                'success': True,
                'tier': response_serializer.data
            })
        else:
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error updating subscription tier: {e}")
        return Response({
            'success': False,
            'error': 'Failed to update subscription tier'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    operation_id="delete_subscription_tier",
    responses={
        200: OpenApiResponse(description="Subscription tier deactivated successfully"),
        403: OpenApiResponse(description="Permission denied"),
        404: OpenApiResponse(description="Subscription tier not found"),
    },
    summary="Delete subscription tier",
    description="Deactivate a subscription tier (admin only)"
)
@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_subscription_tier(request, tier_id):
    """Deactivate a subscription tier (admin only)"""
    try:
        # Check if user is admin/staff
        if not request.user.is_staff:
            return Response({
                'success': False,
                'error': 'Only administrators can delete subscription tiers'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get subscription tier
        try:
            tier = SubscriptionTier.objects.get(id=tier_id)
        except SubscriptionTier.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Subscription tier not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Don't actually delete, just deactivate
        tier.is_active = False
        tier.save()
        
        return Response({
            'success': True,
            'message': 'Subscription tier deactivated successfully'
        })
        
    except Exception as e:
        logger.error(f"Error deleting subscription tier: {e}")
        return Response({
            'success': False,
            'error': 'Failed to delete subscription tier'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
