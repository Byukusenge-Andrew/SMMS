"""
Facebook OAuth Views
Handles Facebook Login integration for user authentication and page management.
"""

import json
import logging
from typing import Any, Dict, Optional

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from apps.integrations.services.facebook_service import FacebookService

User = get_user_model()
logger = logging.getLogger(__name__)

facebook_service = FacebookService()


@require_GET
def facebook_login(request: HttpRequest) -> HttpResponse:
    """
    Initiate Facebook OAuth flow.
    Redirects user to Facebook authorization page.
    """
    try:
        # Generate Facebook OAuth URL
        auth_url = facebook_service.get_authorization_url()
        
        logger.info(f"Generated Facebook OAuth URL: {auth_url}")
        
        # Redirect to Facebook OAuth
        return redirect(auth_url)
        
    except Exception as e:
        logger.error(f"Error initiating Facebook OAuth: {str(e)}")
        return JsonResponse({
            'error': 'Failed to initiate Facebook authentication',
            'message': str(e)
        }, status=500)


@require_GET
def facebook_callback(request: HttpRequest) -> HttpResponse:
    """
    Handle Facebook OAuth callback.
    Exchanges authorization code for access token and user info.
    """
    try:
        # Get authorization code from callback
        auth_code = request.GET.get('code')
        error = request.GET.get('error')
        error_description = request.GET.get('error_description')
        
        if error:
            logger.error(f"Facebook OAuth error: {error} - {error_description}")
            return JsonResponse({
                'error': f'Facebook OAuth error: {error}',
                'description': error_description
            }, status=400)
        
        if not auth_code:
            logger.error("No authorization code received from Facebook")
            return JsonResponse({
                'error': 'No authorization code received from Facebook'
            }, status=400)
        
        # Exchange code for access token
        token_data = facebook_service.exchange_code_for_token(auth_code)
        
        if not token_data:
            logger.error("Failed to exchange code for Facebook access token")
            return JsonResponse({
                'error': 'Failed to exchange code for access token'
            }, status=400)
        
        access_token = token_data.get('access_token')
        token_type = token_data.get('token_type', 'Bearer')
        expires_in = token_data.get('expires_in')
        
        # Get user info from Facebook
        user_info = facebook_service.get_user_info(access_token)
        
        if not user_info:
            logger.error("Failed to get user info from Facebook")
            return JsonResponse({
                'error': 'Failed to get user information from Facebook'
            }, status=400)
        
        facebook_id = user_info.get('id')
        name = user_info.get('name')
        email = user_info.get('email')
        
        logger.info(f"Facebook OAuth successful for user: {name} ({facebook_id})")
        
        # Get user's Facebook pages
        pages = facebook_service.get_user_pages(access_token)
        
        # Store Facebook integration data in session
        request.session['facebook_auth'] = {
            'access_token': access_token,
            'token_type': token_type,
            'expires_in': expires_in,
            'user_info': user_info,
            'pages': pages
        }
        
        # Create success response
        context = {
            'platform': 'Facebook',
            'success': True,
            'user_info': json.dumps(user_info),
            'pages': json.dumps(pages),
            'message': f'Successfully connected to Facebook as {name}'
        }
        
        return render(request, 'integrations/oauth_success.html', context)
        
    except Exception as e:
        logger.error(f"Error in Facebook OAuth callback: {str(e)}")
        return JsonResponse({
            'error': 'Facebook OAuth callback error',
            'message': str(e)
        }, status=500)


@require_GET
@login_required
def facebook_profile(request: HttpRequest) -> HttpResponse:
    """
    Display Facebook user profile and pages.
    """
    try:
        facebook_auth = request.session.get('facebook_auth')
        
        if not facebook_auth:
            return JsonResponse({
                'error': 'No Facebook authentication found. Please connect to Facebook first.'
            }, status=401)
        
        user_info = facebook_auth.get('user_info', {})
        pages = facebook_auth.get('pages', [])
        
        return JsonResponse({
            'user_info': user_info,
            'pages': pages,
            'connected': True
        })
        
    except Exception as e:
        logger.error(f"Error getting Facebook profile: {str(e)}")
        return JsonResponse({
            'error': 'Failed to get Facebook profile',
            'message': str(e)
        }, status=500)


@require_POST
@login_required
@csrf_exempt
def facebook_post(request: HttpRequest) -> HttpResponse:
    """
    Create a post on Facebook page.
    """
    try:
        facebook_auth = request.session.get('facebook_auth')
        
        if not facebook_auth:
            return JsonResponse({
                'error': 'No Facebook authentication found. Please connect to Facebook first.'
            }, status=401)
        
        access_token = facebook_auth.get('access_token')
        
        # Parse request data
        data = json.loads(request.body)
        page_id = data.get('page_id')
        message = data.get('message', '')
        link = data.get('link')
        
        if not page_id:
            return JsonResponse({
                'error': 'Page ID is required'
            }, status=400)
        
        if not message and not link:
            return JsonResponse({
                'error': 'Message or link is required'
            }, status=400)
        
        # Get page access token
        pages = facebook_auth.get('pages', [])
        page_access_token = None
        
        for page in pages:
            if page.get('id') == page_id:
                page_access_token = page.get('access_token')
                break
        
        if not page_access_token:
            return JsonResponse({
                'error': 'Page access token not found. Please reconnect to Facebook.'
            }, status=401)
        
        # Create the post
        post_result = facebook_service.post_to_page(
            page_id=page_id,
            page_access_token=page_access_token,
            message=message,
            link=link
        )
        
        if post_result:
            logger.info(f"Successfully posted to Facebook page {page_id}: {post_result.get('id')}")
            return JsonResponse({
                'success': True,
                'post_id': post_result.get('id'),
                'message': 'Post created successfully'
            })
        else:
            return JsonResponse({
                'error': 'Failed to create Facebook post'
            }, status=400)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error creating Facebook post: {str(e)}")
        return JsonResponse({
            'error': 'Failed to create Facebook post',
            'message': str(e)
        }, status=500)


@require_GET
@login_required
def facebook_disconnect(request: HttpRequest) -> HttpResponse:
    """
    Disconnect Facebook integration.
    """
    try:
        if 'facebook_auth' in request.session:
            del request.session['facebook_auth']
            logger.info("Facebook integration disconnected")
        
        return JsonResponse({
            'success': True,
            'message': 'Facebook integration disconnected successfully'
        })
        
    except Exception as e:
        logger.error(f"Error disconnecting Facebook: {str(e)}")
        return JsonResponse({
            'error': 'Failed to disconnect Facebook',
            'message': str(e)
        }, status=500)


@require_GET
def facebook_status(request: HttpRequest) -> HttpResponse:
    """
    Check Facebook integration status.
    """
    try:
        # Simple rate limiting: check last access time
        last_check = request.session.get('facebook_status_last_check', 0)
        current_time = timezone.now().timestamp()
        
        # Limit to once per 2 seconds to prevent spam
        if current_time - last_check < 2:
            # Return cached result if available
            cached_status = request.session.get('facebook_status_cache')
            if cached_status:
                return JsonResponse(cached_status)
        
        request.session['facebook_status_last_check'] = current_time
        
        facebook_auth = request.session.get('facebook_auth')
        
        if facebook_auth:
            user_info = facebook_auth.get('user_info', {})
            pages_count = len(facebook_auth.get('pages', []))
            
            status_data = {
                'connected': True,
                'user_name': user_info.get('name'),
                'user_id': user_info.get('id'),
                'pages_count': pages_count
            }
        else:
            status_data = {
                'connected': False
            }
        
        # Cache the result
        request.session['facebook_status_cache'] = status_data
        return JsonResponse(status_data)
        
    except Exception as e:
        logger.error(f"Error checking Facebook status: {str(e)}")
        return JsonResponse({
            'error': 'Failed to check Facebook status',
            'message': str(e)
        }, status=500)
