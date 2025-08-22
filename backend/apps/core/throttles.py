"""
Django REST Framework throttle classes for SMMS
Separate file to avoid circular imports
"""

import logging
from typing import Optional

from django.conf import settings

from rest_framework.request import Request
from rest_framework.throttling import BaseThrottle
from rest_framework.views import APIView

from .rate_limiter import SlidingWindowRateLimiter, TokenBucketRateLimiter

logger = logging.getLogger(__name__)


class SMMSCustomThrottle(BaseThrottle):
    """
    Custom Django REST Framework Throttle
    Integrates Token Bucket and Sliding Window algorithms
    """

    # Rate limits for different user types
    RATE_LIMITS = {
        "anonymous": {
            "token_bucket": {"capacity": 10, "refill_rate": 0.1},  # 10 requests, refill 1 per 10 seconds
            "sliding_window": {"max_requests": 20, "window_size": 3600},  # 20 requests per hour
        },
        "authenticated": {
            "token_bucket": {"capacity": 100, "refill_rate": 1.0},  # 100 requests, refill 1 per second
            "sliding_window": {"max_requests": 1000, "window_size": 3600},  # 1000 requests per hour
        },
        "premium": {
            "token_bucket": {"capacity": 500, "refill_rate": 5.0},  # 500 requests, refill 5 per second
            "sliding_window": {"max_requests": 10000, "window_size": 3600},  # 10000 requests per hour
        },
        "admin": {
            "token_bucket": {"capacity": 1000, "refill_rate": 10.0},  # 1000 requests, refill 10 per second
            "sliding_window": {"max_requests": 50000, "window_size": 3600},  # 50000 requests per hour
        },
    }

    def get_user_type(self, request: Request) -> str:
        """Determine user type for rate limiting based on subscription tier"""
        if not request.user.is_authenticated:
            return "anonymous"
        elif request.user.is_staff or request.user.is_superuser:
            return "admin"
        else:
            # Check subscription tier for premium users
            try:
                from .models import UserSubscription
                subscription = UserSubscription.objects.get(user=request.user)
                
                if subscription.is_active:
                    # Map subscription tiers to rate limit types
                    tier_mapping = {
                        'enterprise': 'admin',
                        'professional': 'premium', 
                        'basic': 'authenticated',
                        'free': 'authenticated'
                    }
                    return tier_mapping.get(subscription.tier.name, 'authenticated')
                    
            except UserSubscription.DoesNotExist:
                pass
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Error checking subscription for user {request.user.username}: {e}")
            
            # Fallback to checking legacy profile attribute
            if hasattr(request.user, "profile") and request.user.profile.subscription_type == "premium":
                return "premium"
            
            return "authenticated"

    def get_ident(self, request: Request) -> str:
        """Get unique identifier for rate limiting"""
        if request.user.is_authenticated:
            return f"user:{request.user.id}"
        else:
            # Use IP address for anonymous users
            xff = request.META.get("HTTP_X_FORWARDED_FOR")
            remote_addr = request.META.get("REMOTE_ADDR")
            numProxies = getattr(settings, "NUM_PROXIES", None)

            if numProxies is not None:
                if xff:
                    addrs = xff.split(",")
                    client_addr = addrs[-min(numProxies, len(addrs))]
                    return client_addr.strip()

            return xff.split(",")[0].strip() if xff else remote_addr

    def allow_request(self, request: Request, view: APIView) -> bool:
        """Main throttling logic"""
        user_type = self.get_user_type(request)
        identifier = self.get_ident(request)

        # Skip throttling for certain endpoints
        if self._should_skip_throttling(request, view):
            return True

        # Get rate limits for user type
        limits = self.RATE_LIMITS.get(user_type, self.RATE_LIMITS["anonymous"])

        # Check Token Bucket
        tb_config = limits["token_bucket"]
        token_bucket = TokenBucketRateLimiter(capacity=tb_config["capacity"], refill_rate=tb_config["refill_rate"])

        tb_allowed, tb_metadata = token_bucket.is_allowed(f"tb:{identifier}")

        # Check Sliding Window
        sw_config = limits["sliding_window"]
        sliding_window = SlidingWindowRateLimiter(max_requests=sw_config["max_requests"], window_size=sw_config["window_size"])

        sw_allowed, sw_metadata = sliding_window.is_allowed(f"sw:{identifier}")

        # Request is allowed only if both algorithms allow it
        allowed = tb_allowed and sw_allowed

        # Store metadata for headers
        self.metadata = {
            "user_type": user_type,
            "token_bucket": tb_metadata,
            "sliding_window": sw_metadata,
            "allowed": allowed,
        }

        if not allowed:
            logger.warning(f"Rate limit exceeded for {user_type} user {identifier}. " f"TB: {tb_allowed}, SW: {sw_allowed}")

        return allowed

    def _should_skip_throttling(self, request: Request, view: APIView) -> bool:
        """Check if throttling should be skipped for this request"""
        # Skip for health checks
        if request.path in ["/health/", "/api/health/"]:
            return True

        # Skip for admin users on specific endpoints
        if request.user.is_superuser and request.path.startswith("/admin/"):
            return True

        return False

    def wait(self) -> Optional[int]:
        """Return wait time in seconds"""
        if not hasattr(self, "metadata"):
            return None

        tb_retry = self.metadata["token_bucket"].get("retry_after", 0)
        sw_retry = self.metadata["sliding_window"].get("retry_after", 0)

        return max(tb_retry, sw_retry) if tb_retry or sw_retry else None


class AnonymousUserThrottle(SMMSCustomThrottle):
    """Rate limiter for anonymous users"""

    def get_user_type(self, request):
        return "anonymous"


class AuthenticatedUserThrottle(SMMSCustomThrottle):
    """Rate limiter for authenticated users"""

    def allow_request(self, request, view):
        if not request.user.is_authenticated:
            return True
        return super().allow_request(request, view)


class PremiumUserThrottle(SMMSCustomThrottle):
    """Rate limiter for premium users"""

    def allow_request(self, request, view):
        if not request.user.is_authenticated:
            return True
        return super().allow_request(request, view)


class BurstProtectionThrottle(BaseThrottle):
    """
    Additional protection against burst attacks
    Very strict short-term limits
    """

    def __init__(self):
        self.limiter = SlidingWindowRateLimiter(max_requests=5, window_size=10)  # 5 requests  # per 10 seconds

    def allow_request(self, request, view):
        if request.user.is_authenticated and request.user.is_staff:
            return True

        identifier = self.get_ident(request)
        allowed, metadata = self.limiter.is_allowed(f"burst:{identifier}")

        if not allowed:
            logger.warning(f"Burst protection triggered for {identifier}")

        return allowed

    def get_ident(self, request):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        remote_addr = request.META.get("REMOTE_ADDR")
        return xff.split(",")[0].strip() if xff else remote_addr

    def wait(self):
        return 10  # Wait 10 seconds for burst protection
