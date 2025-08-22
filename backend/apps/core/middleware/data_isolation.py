"""
Data Isolation Middleware for SMMS
Provides an additional layer of security to prevent data leakage between clients
"""

import logging
import json
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('data_isolation')


class DataIsolationMiddleware(MiddlewareMixin):
    """
    Middleware to enforce data isolation and log access patterns
    """
    
    # URLs that should be monitored for cross-user access
    MONITORED_PATTERNS = [
        '/api/posts/',
        '/api/media/',
        '/api/analytics/',
        '/api/social-accounts/',
        '/api/notifications/',
        '/api/messaging/',
        '/api/integrations/',
    ]
    
    # URLs that are safe to access without user filtering
    SAFE_PATTERNS = [
        '/api/auth/',
        '/api/health/',
        '/api/schema/',
        '/admin/',
        '/static/',
    ]
    
    def process_request(self, request):
        """Process incoming request for data isolation checks"""
        
        # Skip monitoring for safe URLs
        if any(request.path.startswith(pattern) for pattern in self.SAFE_PATTERNS):
            return None
        
        # Log access for monitored URLs
        if any(request.path.startswith(pattern) for pattern in self.MONITORED_PATTERNS):
            self._log_access(request)
        
        # Add isolation context to request
        if hasattr(request, 'user') and request.user.is_authenticated:
            request.isolation_user_id = request.user.id
        
        return None
    
    def process_response(self, request, response):
        """Process response to check for potential data leakage"""
        
        # Only monitor JSON responses for sensitive endpoints
        if (response.get('content-type', '').startswith('application/json') and
            any(request.path.startswith(pattern) for pattern in self.MONITORED_PATTERNS)):
            
            self._validate_response_data(request, response)
        
        return response
    
    def _log_access(self, request):
        """Log user access for audit purposes"""
        if hasattr(request, 'user') and request.user.is_authenticated:
            logger.info(
                f"User access - ID: {request.user.id}, "
                f"Username: {request.user.username}, "
                f"Path: {request.path}, "
                f"Method: {request.method}, "
                f"IP: {self._get_client_ip(request)}"
            )
    
    def _validate_response_data(self, request, response):
        """Validate that response doesn't contain other users' data"""
        
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return
        
        try:
            # Only check successful JSON responses
            if (response.status_code == 200 and 
                response.get('content-type', '').startswith('application/json')):
                
                content = response.content.decode('utf-8')
                data = json.loads(content)
                
                # Check for potential cross-user data in common response patterns
                self._check_user_data_in_response(request.user, data, request.path)
                
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Skip validation for non-JSON or malformed responses
            pass
        except Exception as e:
            logger.warning(f"Error validating response data: {str(e)}")
    
    def _check_user_data_in_response(self, user, data, path):
        """Check response data for potential cross-user data leakage"""
        
        def check_object(obj, path_context):
            if isinstance(obj, dict):
                # Check for user_id fields
                if 'user_id' in obj or 'user' in obj:
                    user_id = obj.get('user_id') or (obj.get('user', {}).get('id') if isinstance(obj.get('user'), dict) else obj.get('user'))
                    if user_id and str(user_id) != str(user.id):
                        logger.warning(
                            f"Potential data leakage detected - User {user.id} accessing data for user {user_id} "
                            f"at path {path} (context: {path_context})"
                        )
                
                # Recursively check nested objects
                for key, value in obj.items():
                    if isinstance(value, (dict, list)):
                        check_object(value, f"{path_context}.{key}")
            
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    if isinstance(item, (dict, list)):
                        check_object(item, f"{path_context}[{i}]")
        
        # Start validation
        if isinstance(data, (dict, list)):
            check_object(data, 'root')
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class CrossUserAccessDetectionMiddleware(MiddlewareMixin):
    """
    Middleware specifically designed to detect and prevent cross-user data access
    """
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        """Process view to detect potential cross-user access"""
        
        # Skip if user is not authenticated
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None
        
        # Check for user ID in URL parameters
        user_id_params = ['user_id', 'userId', 'user']
        url_user_id = None
        
        for param in user_id_params:
            if param in view_kwargs:
                url_user_id = view_kwargs[param]
                break
        
        # If URL contains user ID, verify it matches the authenticated user
        if url_user_id:
            try:
                url_user_id = int(url_user_id)
                if url_user_id != request.user.id and not request.user.is_staff:
                    logger.error(
                        f"Cross-user access attempt detected - User {request.user.id} "
                        f"trying to access user {url_user_id} data at {request.path}"
                    )
                    return JsonResponse({
                        'error': 'Access denied',
                        'message': 'You can only access your own data'
                    }, status=403)
            except (ValueError, TypeError):
                # URL user ID is not a valid integer, skip check
                pass
        
        return None


class SecurityAuditMiddleware(MiddlewareMixin):
    """
    Middleware for security auditing and suspicious activity detection
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.suspicious_patterns = {
            'rapid_requests': {},  # Track rapid requests per user
            'unusual_access': {},  # Track unusual access patterns
        }
    
    def __call__(self, request):
        # Pre-process
        self._track_request_patterns(request)
        
        response = self.get_response(request)
        
        # Post-process
        self._analyze_response_patterns(request, response)
        
        return response
    
    def _track_request_patterns(self, request):
        """Track request patterns for anomaly detection"""
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return
        
        user_id = request.user.id
        current_time = __import__('time').time()
        
        # Track rapid requests
        if user_id not in self.suspicious_patterns['rapid_requests']:
            self.suspicious_patterns['rapid_requests'][user_id] = []
        
        # Clean old requests (keep only last 60 seconds)
        self.suspicious_patterns['rapid_requests'][user_id] = [
            t for t in self.suspicious_patterns['rapid_requests'][user_id]
            if current_time - t < 60
        ]
        
        # Add current request
        self.suspicious_patterns['rapid_requests'][user_id].append(current_time)
        
        # Check for suspicious rapid requests (more than 100 requests per minute)
        if len(self.suspicious_patterns['rapid_requests'][user_id]) > 100:
            logger.warning(
                f"Suspicious rapid requests detected - User {user_id} made "
                f"{len(self.suspicious_patterns['rapid_requests'][user_id])} requests in last minute"
            )
    
    def _analyze_response_patterns(self, request, response):
        """Analyze response patterns for security issues"""
        # Log failed authentication attempts
        if request.path.startswith('/api/auth/') and response.status_code == 401:
            logger.warning(
                f"Failed authentication attempt from {self._get_client_ip(request)} "
                f"for path {request.path}"
            )
        
        # Log access to sensitive endpoints
        sensitive_endpoints = ['/api/admin/', '/api/users/', '/api/system/']
        if any(request.path.startswith(endpoint) for endpoint in sensitive_endpoints):
            user = getattr(request, 'user', None)
            if user and user.is_authenticated:
                logger.info(
                    f"Sensitive endpoint access - User {user.id} accessed {request.path}"
                )
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
