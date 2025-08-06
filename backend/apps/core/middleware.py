"""
Enhanced rate limiting middleware with logging and IP blocking
"""

import logging

from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

from .models import IPBlacklist, IPWhitelist, RateLimitLog
from .rate_limiter import SlidingWindowRateLimiter, TokenBucketRateLimiter

logger = logging.getLogger(__name__)


class RateLimitMiddleware(MiddlewareMixin):
    """
    Middleware to enforce rate limiting and IP blocking
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

    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_request(self, request):
        """Process incoming request for rate limiting"""

        # Get client IP
        ip_address = self._get_client_ip(request)

        # Check IP blacklist first
        if self._is_ip_blacklisted(ip_address):
            self._log_rate_limit_event(request, ip_address, "denied", metadata={"reason": "IP blacklisted"})
            return JsonResponse({"error": "Access denied", "message": "Your IP address has been blocked"}, status=403)

        # Check IP whitelist
        if self._is_ip_whitelisted(ip_address):
            return None  # Allow request to proceed

        # Apply rate limiting
        user_type = self._get_user_type(request)
        identifier = self._get_identifier(request)

        # Check if should skip throttling
        if self._should_skip_throttling(request):
            return None

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

        # Create metadata
        metadata = {"user_type": user_type, "token_bucket": tb_metadata, "sliding_window": sw_metadata, "allowed": allowed}

        if not allowed:
            wait_time = max(tb_metadata.get("retry_after", 0), sw_metadata.get("retry_after", 0))

            self._log_rate_limit_event(request, ip_address, "denied", metadata=metadata)

            response = JsonResponse(
                {
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": wait_time,
                },
                status=429,
            )

            if wait_time:
                response["Retry-After"] = str(wait_time)

            return response

        # Log successful request
        self._log_rate_limit_event(request, ip_address, "allowed", metadata=metadata)

        # Store metadata for response headers
        request.rate_limit_metadata = metadata

        return None

    def _get_user_type(self, request):
        """Determine user type for rate limiting"""
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return "anonymous"
        elif request.user.is_staff or request.user.is_superuser:
            return "admin"
        elif hasattr(request.user, "profile") and request.user.profile.is_premium:
            return "premium"
        else:
            return "authenticated"

    def _get_identifier(self, request):
        """Get unique identifier for rate limiting"""
        if hasattr(request, 'user') and request.user.is_authenticated:
            return f"user:{request.user.id}"
        else:
            return f"ip:{self._get_client_ip(request)}"

    def _should_skip_throttling(self, request):
        """Check if throttling should be skipped for this request"""
        # Skip for health checks
        if request.path in ["/health/", "/api/health/"]:
            return True

        # Skip for admin users on specific endpoints
        if hasattr(request, 'user') and request.user.is_authenticated and request.user.is_superuser and request.path.startswith("/admin/"):
            return True

        return False

        return None

    def process_response(self, request, response):
        """Add rate limiting headers to response"""

        if hasattr(request, "rate_limit_metadata"):
            metadata = request.rate_limit_metadata

            # Add rate limiting headers
            if "token_bucket" in metadata:
                tb = metadata["token_bucket"]
                response["X-RateLimit-Bucket-Remaining"] = str(tb.get("tokens_remaining", 0))
                response["X-RateLimit-Bucket-Capacity"] = str(tb.get("bucket_capacity", 0))
                response["X-RateLimit-Bucket-Refill-Rate"] = str(tb.get("refill_rate", 0))

            if "sliding_window" in metadata:
                sw = metadata["sliding_window"]
                response["X-RateLimit-Window-Remaining"] = str(sw.get("requests_remaining", 0))
                response["X-RateLimit-Window-Limit"] = str(sw.get("max_requests", 0))
                response["X-RateLimit-Window-Reset"] = str(sw.get("window_size", 0))

            response["X-RateLimit-User-Type"] = metadata.get("user_type", "unknown")

        return response

    def _get_client_ip(self, request):
        """Extract client IP address from request"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    def _is_ip_blacklisted(self, ip_address):
        """Check if IP is blacklisted"""
        cache_key = f"ip_blacklist:{ip_address}"
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            return cached_result

        # Check database
        blacklisted = IPBlacklist.objects.filter(ip_address=ip_address, is_active=True).exists()

        # Cache result for 5 minutes
        cache.set(cache_key, blacklisted, 300)
        return blacklisted

    def _is_ip_whitelisted(self, ip_address):
        """Check if IP is whitelisted"""
        cache_key = f"ip_whitelist:{ip_address}"
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            return cached_result

        # Check database
        whitelisted = IPWhitelist.objects.filter(ip_address=ip_address, is_active=True).exists()

        # Cache result for 5 minutes
        cache.set(cache_key, whitelisted, 300)
        return whitelisted

    def _log_rate_limit_event(self, request, ip_address, action, metadata=None):
        """Log rate limiting event"""
        try:
            user_type = "anonymous"
            user = None

            if hasattr(request, 'user') and request.user.is_authenticated:
                user = request.user
                if request.user.is_staff or request.user.is_superuser:
                    user_type = "admin"
                elif hasattr(request.user, "profile") and request.user.profile.is_premium:
                    user_type = "premium"
                else:
                    user_type = "authenticated"

            # Extract relevant metadata
            log_metadata = metadata or {}
            tokens_remaining = None
            requests_remaining = None
            retry_after = None

            if "token_bucket" in log_metadata:
                tokens_remaining = log_metadata["token_bucket"].get("tokens_remaining")
                retry_after = log_metadata["token_bucket"].get("retry_after")

            if "sliding_window" in log_metadata:
                requests_remaining = log_metadata["sliding_window"].get("requests_remaining")
                if not retry_after:
                    retry_after = log_metadata["sliding_window"].get("retry_after")

            RateLimitLog.objects.create(
                user=user,
                ip_address=ip_address,
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
                endpoint=request.path,
                method=request.method,
                user_type=user_type,
                action=action,
                algorithm_used=log_metadata.get("algorithm", "both"),
                tokens_remaining=tokens_remaining,
                requests_remaining=requests_remaining,
                retry_after=retry_after,
                metadata=log_metadata,
            )
        except Exception as e:
            logger.error(f"Failed to log rate limit event: {e}")


class BurstProtectionMiddleware(MiddlewareMixin):
    """
    Additional middleware for burst attack protection
    More aggressive short-term limits
    """

    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_request(self, request):
        """Apply burst protection"""

        # Skip for authenticated staff users (safely check if user exists)
        if hasattr(request, 'user') and request.user.is_authenticated and request.user.is_staff:
            return None

        ip_address = self._get_client_ip(request)

        # Check for rapid successive requests
        cache_key = f"burst_protection:{ip_address}"
        request_times = cache.get(cache_key, [])

        current_time = timezone.now().timestamp()

        # Remove requests older than 10 seconds
        request_times = [t for t in request_times if current_time - t < 10]

        # Check if too many requests in short time
        if len(request_times) >= 5:  # 5 requests in 10 seconds
            self._log_burst_protection(request, ip_address)

            return JsonResponse(
                {"error": "Too many requests", "message": "Burst protection triggered. Please slow down.", "retry_after": 10},
                status=429,
            )

        # Add current request time
        request_times.append(current_time)
        cache.set(cache_key, request_times, 10)

        return None

    def _get_client_ip(self, request):
        """Extract client IP address from request"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    def _log_burst_protection(self, request, ip_address):
        """Log burst protection trigger"""
        try:
            RateLimitLog.objects.create(
                user=request.user if hasattr(request, 'user') and request.user.is_authenticated else None,
                ip_address=ip_address,
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
                endpoint=request.path,
                method=request.method,
                user_type="authenticated" if hasattr(request, 'user') and request.user.is_authenticated else "anonymous",
                action="burst_protection",
                algorithm_used="burst_protection",
                metadata={"reason": "Too many requests in short time"},
            )
        except Exception as e:
            logger.error(f"Failed to log burst protection event: {e}")
