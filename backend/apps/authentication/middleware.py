"""
Post-authentication middleware to handle first-time user setup
"""
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth.models import User
from apps.core.models.payment_models import SubscriptionTier, UserSubscription


class FirstLoginSetupMiddleware:
    """
    Middleware to redirect first-time users to plan selection after login
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process the request
        response = self.process_request(request)
        if response:
            return response
            
        response = self.get_response(request)
        return response

    def process_request(self, request):
        """
        Check if authenticated user needs first-time setup
        """
        # Skip middleware for certain paths
        skip_paths = [
            '/api/',
            '/admin/',
            '/static/',
            '/media/',
            '/auth/',
            '/logout/',
            '/health/',
            '/plan-selection/',
        ]
        
        if any(request.path.startswith(path) for path in skip_paths):
            return None
            
        # Only process authenticated users
        if not request.user.is_authenticated:
            return None
            
        # Skip for superusers
        if request.user.is_superuser:
            return None
            
        # Skip if already completed setup
        if request.session.get('setup_completed', False):
            return None
            
        # Check if user has a subscription
        try:
            user_subscription = UserSubscription.objects.get(user=request.user)
            # Mark setup as completed if they have a subscription
            request.session['setup_completed'] = True
            if hasattr(request.user, 'profile'):
                request.user.profile.setup_completed = True
                request.user.profile.save()
            return None
        except UserSubscription.DoesNotExist:
            # User doesn't have a subscription, assign free tier and redirect
            return self.setup_free_tier(request)
                
        return None
    
    def setup_free_tier(self, request):
        """
        Assign free tier to user and redirect to plan selection
        """
        try:
            # Get free tier
            free_tier = SubscriptionTier.objects.get(name='free')
            
            # Create user subscription with free tier
            UserSubscription.objects.get_or_create(
                user=request.user,
                defaults={
                    'tier': free_tier,
                    'status': 'active',
                    'billing_period': 'monthly',
                    'is_trial': False
                }
            )
            
            # Redirect to plan selection page
            return redirect('/plan-selection')
            
        except SubscriptionTier.DoesNotExist:
            # Free tier doesn't exist, redirect to dashboard
            return redirect('dashboard')
        except Exception as e:
            # Log error and continue to dashboard
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in FirstLoginSetupMiddleware: {e}")
            return redirect('dashboard')
