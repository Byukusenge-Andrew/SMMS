"""
Rate Limiting Algorithm for SMMS
Implements Token Bucket and Sliding Window algorithms for API rate limiting
"""

import json
import logging
import time
from typing import Dict, Optional, Tuple

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class TokenBucketRateLimiter:
    """
    Token Bucket Algorithm Implementation
    - Allows burst traffic up to bucket capacity
    - Refills tokens at a steady rate
    - Good for handling spiky traffic patterns
    """

    def __init__(self, capacity: int, refill_rate: float, cache_timeout: int = 3600):
        self.capacity = capacity  # Maximum tokens in bucket
        self.refill_rate = refill_rate  # Tokens per second
        self.cache_timeout = cache_timeout

    def _get_bucket_key(self, identifier: str) -> str:
        return f"token_bucket:{identifier}"

    def _get_bucket_state(self, identifier: str) -> Tuple[int, float]:
        """Get current bucket state (tokens, last_refill_time)"""
        key = self._get_bucket_key(identifier)
        bucket_data = cache.get(key)

        if bucket_data is None:
            # Initialize new bucket
            return self.capacity, time.time()

        try:
            data = json.loads(bucket_data)
            return data["tokens"], data["last_refill"]
        except (json.JSONDecodeError, KeyError):
            return self.capacity, time.time()

    def _save_bucket_state(self, identifier: str, tokens: int, last_refill: float):
        """Save bucket state to cache"""
        key = self._get_bucket_key(identifier)
        bucket_data = json.dumps({"tokens": tokens, "last_refill": last_refill})
        cache.set(key, bucket_data, self.cache_timeout)

    def _refill_bucket(self, current_tokens: int, last_refill: float) -> Tuple[int, float]:
        """Refill bucket based on elapsed time"""
        now = time.time()
        elapsed = now - last_refill

        # Calculate tokens to add
        tokens_to_add = int(elapsed * self.refill_rate)
        new_tokens = min(current_tokens + tokens_to_add, self.capacity)

        return new_tokens, now

    def is_allowed(self, identifier: str, tokens_requested: int = 1) -> Tuple[bool, Dict]:
        """
        Check if request is allowed and consume tokens
        Returns: (allowed, metadata)
        """
        current_tokens, last_refill = self._get_bucket_state(identifier)
        current_tokens, current_time = self._refill_bucket(current_tokens, last_refill)

        metadata = {
            "tokens_available": current_tokens,
            "tokens_requested": tokens_requested,
            "bucket_capacity": self.capacity,
            "refill_rate": self.refill_rate,
        }

        if current_tokens >= tokens_requested:
            # Allow request and consume tokens
            current_tokens -= tokens_requested
            self._save_bucket_state(identifier, current_tokens, current_time)
            metadata["tokens_remaining"] = current_tokens
            return True, metadata
        else:
            # Request denied
            self._save_bucket_state(identifier, current_tokens, current_time)
            time_to_wait = (tokens_requested - current_tokens) / self.refill_rate
            metadata["retry_after"] = int(time_to_wait)
            metadata["tokens_remaining"] = current_tokens
            return False, metadata


class SlidingWindowRateLimiter:
    """
    Sliding Window Algorithm Implementation
    - More accurate than fixed window
    - Prevents burst at window boundaries
    - Good for strict rate limiting
    """

    def __init__(self, max_requests: int, window_size: int, cache_timeout: int = 3600):
        self.max_requests = max_requests
        self.window_size = window_size  # in seconds
        self.cache_timeout = cache_timeout

    def _get_window_key(self, identifier: str) -> str:
        return f"sliding_window:{identifier}"

    def _cleanup_old_requests(self, requests: list, current_time: float) -> list:
        """Remove requests older than window_size"""
        cutoff_time = current_time - self.window_size
        return [req_time for req_time in requests if req_time > cutoff_time]

    def is_allowed(self, identifier: str) -> Tuple[bool, Dict]:
        """
        Check if request is allowed in sliding window
        Returns: (allowed, metadata)
        """
        key = self._get_window_key(identifier)
        current_time = time.time()

        # Get existing requests
        requests_data = cache.get(key, "[]")
        try:
            requests = json.loads(requests_data)
        except json.JSONDecodeError:
            requests = []

        # Cleanup old requests
        requests = self._cleanup_old_requests(requests, current_time)

        metadata = {
            "current_requests": len(requests),
            "max_requests": self.max_requests,
            "window_size": self.window_size,
            "requests_remaining": max(0, self.max_requests - len(requests)),
        }

        if len(requests) < self.max_requests:
            # Allow request and record it
            requests.append(current_time)
            cache.set(key, json.dumps(requests), self.cache_timeout)
            metadata["requests_remaining"] = self.max_requests - len(requests)
            return True, metadata
        else:
            # Request denied
            oldest_request = min(requests) if requests else current_time
            retry_after = int(oldest_request + self.window_size - current_time)
            metadata["retry_after"] = max(1, retry_after)
            return False, metadata


class RateLimitHeaderMiddleware:
    """
    Middleware to add rate limiting headers to responses
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Add rate limit headers if metadata is available
        if hasattr(request, "rate_limit_metadata"):
            metadata = request.rate_limit_metadata

            if "token_bucket" in metadata:
                tb = metadata["token_bucket"]
                response["X-RateLimit-Bucket-Capacity"] = str(tb.get("bucket_capacity", 0))
                response["X-RateLimit-Bucket-Remaining"] = str(tb.get("tokens_remaining", 0))
                response["X-RateLimit-Bucket-Refill-Rate"] = str(tb.get("refill_rate", 0))

            if "sliding_window" in metadata:
                sw = metadata["sliding_window"]
                response["X-RateLimit-Window-Limit"] = str(sw.get("max_requests", 0))
                response["X-RateLimit-Window-Remaining"] = str(sw.get("requests_remaining", 0))
                response["X-RateLimit-Window-Size"] = str(sw.get("window_size", 0))

            if not metadata.get("allowed", True):
                wait_time = max(
                    metadata["token_bucket"].get("retry_after", 0), metadata["sliding_window"].get("retry_after", 0)
                )
                response["Retry-After"] = str(wait_time)

        return response
