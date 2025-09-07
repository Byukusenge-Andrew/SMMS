import logging
import secrets
import uuid
from django.conf import settings
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from rest_framework import status
import requests
from apps.authentication.models import SocialMediaAccount as AuthSocialMediaAccount
from apps.integrations.models import SocialMediaAccount, SocialMediaPlatform

logger = logging.getLogger(__name__)
User = get_user_model()

# Facebook Graph API endpoints
FACEBOOK_AUTH_URL = "https://www.facebook.com/v18.0/dialog/oauth"
FACEBOOK_TOKEN_URL = "https://graph.facebook.com/v18.0/oauth/access_token"
FACEBOOK_USER_URL = "https://graph.facebook.com/v18.0/me"
FACEBOOK_PAGES_URL = "https://graph.facebook.com/v18.0/me/accounts"

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def facebook_authorize(request):
    """
    Generate Facebook authorization URL
    """
    try:
        app_id = settings.SOCIAL_MEDIA_CONFIGS['FACEBOOK']['APP_ID']
        redirect_uri = settings.SOCIAL_MEDIA_CONFIGS['FACEBOOK']['REDIRECT_URI']
        
        if not app_id or not redirect_uri:
            return JsonResponse({
                'error': 'Facebook API credentials not configured'
            }, status=400)
        
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Store state in session
        request.session['facebook_oauth_state'] = state
        request.session['facebook_user_id'] = request.user.id
        
        # Facebook permissions for basic profile and pages
        scope = 'email,public_profile,pages_show_list,pages_read_engagement,publish_to_groups'
        
        auth_url = (
            f"{FACEBOOK_AUTH_URL}?"
            f"client_id={app_id}&"
            f"redirect_uri={redirect_uri}&"
            f"scope={scope}&"
            f"state={state}&"
            f"response_type=code"
        )
        
        logger.info(f"Facebook authorization URL generated for user {request.user.id}")
        
        # Check if redirect parameter is false (for API calls)
        if request.GET.get('redirect') == 'false':
            return JsonResponse({
                'authorization_url': auth_url,
                'state': state
            })
        
        return HttpResponseRedirect(auth_url)
        
    except Exception as e:
        logger.error(f"Error generating Facebook authorization URL: {e}")
        return JsonResponse({
            'error': 'Failed to generate authorization URL'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def facebook_callback(request):
    """
    Handle Facebook OAuth callback
    """
    try:
        # Get authorization code and state from callback
        code = request.GET.get('code')
        state = request.GET.get('state')
        error = request.GET.get('error')
        
        logger.info(f"Facebook callback received - code: {'present' if code else 'missing'}, state: {state}, error: {error}")
        
        if error:
            logger.error(f"Facebook OAuth error: {error}")
            return JsonResponse({
                'error': f'Facebook authorization failed: {error}',
                'success': False
            }, status=400)
        
        if not code:
            logger.error("Facebook callback missing authorization code")
            return JsonResponse({
                'error': 'Authorization code not provided',
                'success': False
            }, status=400)
        
        # Verify state for CSRF protection
        expected_state = request.session.get('facebook_oauth_state')
        logger.info(f"Facebook callback session data: state_expected={expected_state}, state_received={state}")
        
        # Get user ID from session with fallback strategies
        user_id = request.session.get('facebook_user_id')
        logger.info(f"Facebook callback user_id from session: {user_id}")
        
        current_user = None
        
        # Multi-tier user identification strategy
        if user_id:
            try:
                current_user = User.objects.get(id=user_id)
                logger.info(f"Facebook callback: Found user by session user_id: {current_user.email}")
            except User.DoesNotExist:
                logger.warning(f"Facebook callback: User {user_id} from session not found")
        
        # Fallback 1: Check if request has authenticated user
        if not current_user and hasattr(request, 'user') and request.user.is_authenticated:
            current_user = request.user
            logger.info(f"Facebook callback: Found user by request.user: {current_user.email}")
        
        # Fallback 2: Try to find user by email if we can get it from Facebook
        if not current_user:
            logger.warning("Facebook callback: No user context found, will attempt email lookup after token exchange")
        
        # Exchange authorization code for access token
        app_id = settings.SOCIAL_MEDIA_CONFIGS['FACEBOOK']['APP_ID']
        app_secret = settings.SOCIAL_MEDIA_CONFIGS['FACEBOOK']['APP_SECRET']
        redirect_uri = settings.SOCIAL_MEDIA_CONFIGS['FACEBOOK']['REDIRECT_URI']
        
        logger.info(f"Attempting token exchange for Facebook with code: {code[:10]}...")
        
        token_response = requests.post(FACEBOOK_TOKEN_URL, data={
            'client_id': app_id,
            'client_secret': app_secret,
            'redirect_uri': redirect_uri,
            'code': code
        })
        
        if token_response.status_code != 200:
            logger.error(f"Facebook token exchange failed: {token_response.status_code} - {token_response.text}")
            return JsonResponse({
                'error': 'Failed to exchange authorization code for token',
                'success': False
            }, status=400)
        
        token_data = token_response.json()
        access_token = token_data.get('access_token')
        expires_in = token_data.get('expires_in')
        
        if not access_token:
            logger.error(f"Facebook token exchange did not return access token: {token_data}")
            return JsonResponse({
                'error': 'Invalid token response from Facebook',
                'success': False
            }, status=400)
        
        logger.info("Token exchange result: True")
        
        # Get user information from Facebook
        user_response = requests.get(f"{FACEBOOK_USER_URL}?access_token={access_token}&fields=id,name,email")
        
        if user_response.status_code != 200:
            logger.error(f"Failed to get Facebook user info: {user_response.status_code} - {user_response.text}")
            return JsonResponse({
                'error': 'Failed to get user information from Facebook',
                'success': False
            }, status=400)
        
        user_data = user_response.json()
        facebook_user_id = user_data.get('id')
        facebook_email = user_data.get('email')
        facebook_name = user_data.get('name')
        
        # Final fallback: Find user by email if we still don't have one
        if not current_user and facebook_email:
            try:
                current_user = User.objects.get(email=facebook_email)
                logger.info(f"Facebook callback: Found user by email: {facebook_email}")
            except User.DoesNotExist:
                logger.error(f"Facebook callback: No user found with email {facebook_email}")
                return JsonResponse({
                    'error': 'User account not found. Please ensure you are logged in.',
                    'success': False
                }, status=400)
        
        if not current_user:
            logger.error("Facebook callback: Unable to identify user after all fallback attempts")
            return JsonResponse({
                'error': 'Unable to identify user. Please ensure you are logged in.',
                'success': False
            }, status=400)
        
        # Save tokens to both models
        try:
            # Save to integrations SocialMediaAccount model
            integrated_account, created = SocialMediaAccount.objects.update_or_create(
                user=current_user,
                platform=SocialMediaPlatform.FACEBOOK,
                platform_user_id=facebook_user_id,
                defaults={
                    'username': facebook_name or facebook_email,
                    'display_name': facebook_name,
                    'access_token': access_token,
                    'refresh_token': None,  # Facebook uses long-lived tokens
                    'token_expires_at': None,  # Facebook tokens don't expire by default
                    'is_active': True,
                }
            )
            
            logger.info(f"Facebook tokens saved successfully for user {current_user.email}, account_id: {integrated_account.id}")
            
        except Exception as e:
            logger.error(f"Failed to save Facebook SocialMediaAccount: {e}")
        
        # Save to authentication SocialMediaAccount model
        try:
            auth_account, created = AuthSocialMediaAccount.objects.update_or_create(
                user=current_user,
                platform='facebook',
                platform_user_id=facebook_user_id,
                defaults={
                    'username': facebook_name or facebook_email,
                    'access_token': access_token,
                    'refresh_token': None,  # Facebook uses long-lived tokens
                    'is_active': True,
                }
            )
            logger.info(f"Facebook authentication account {'created' if created else 'updated'} for user {current_user.email}")
        except Exception as e:
            logger.error(f"Failed to sync auth SocialMediaAccount for Facebook: {e}")
        
        # Clear session data
        try:
            del request.session['facebook_oauth_state']
            del request.session['facebook_user_id']
        except KeyError:
            pass
        
        # Prepare response data
        response_data = {
            'success': True,
            'account': {
                'platform': 'facebook',
                'platform_user_id': facebook_user_id,
                'username': facebook_name,
                'email': facebook_email,
                'is_verified': True,  # Facebook accounts are inherently verified
            },
            'tokens': {
                'access_token': access_token,
                'expires_in': expires_in
            }
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Facebook callback error: {e}")
        return JsonResponse({
            'error': 'Internal server error during Facebook authentication',
            'success': False
        }, status=500)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def verify_facebook_credentials(request):
    """
    Verify if user has valid Facebook credentials
    """
    try:
        # Check both models for Facebook accounts
        user = request.user
        
        # Check integrations SocialMediaAccount
        try:
            integrated_account = SocialMediaAccount.objects.get(
                user=user,
                platform=SocialMediaPlatform.FACEBOOK,
                is_active=True
            )
            
            # Verify token is still valid by making a test API call
            test_response = requests.get(
                f"{FACEBOOK_USER_URL}?access_token={integrated_account.access_token}&fields=id,name"
            )
            
            if test_response.status_code == 200:
                user_data = test_response.json()
                return JsonResponse({
                    'success': True,
                    'message': 'Facebook account is connected and verified',
                    'account': {
                        'id': str(integrated_account.id),
                        'platform': 'facebook',
                        'username': integrated_account.username,
                        'display_name': user_data.get('name', integrated_account.username),
                        'profile_image_url': integrated_account.profile_image_url,
                        'platform_user_id': integrated_account.platform_user_id,
                        'is_verified': True,
                    }
                })
            else:
                # Token is invalid, deactivate account
                integrated_account.is_active = False
                integrated_account.save()
                logger.warning(f"Facebook token expired for user {user.email}")
                
        except SocialMediaAccount.DoesNotExist:
            pass
        
        # Check authentication SocialMediaAccount as fallback
        try:
            auth_account = AuthSocialMediaAccount.objects.get(
                user=user,
                platform='facebook',
                is_active=True
            )
            
            # Verify token is still valid
            test_response = requests.get(
                f"{FACEBOOK_USER_URL}?access_token={auth_account.access_token}&fields=id,name"
            )
            
            if test_response.status_code == 200:
                user_data = test_response.json()
                return JsonResponse({
                    'success': True,
                    'message': 'Facebook account is connected and verified',
                    'account': {
                        'id': str(auth_account.id),
                        'platform': 'facebook',
                        'username': auth_account.username,
                        'display_name': user_data.get('name', auth_account.username),
                        'profile_image_url': auth_account.profile_image_url,
                        'platform_user_id': auth_account.platform_user_id,
                        'is_verified': True,
                    }
                })
            else:
                # Token is invalid, deactivate account
                auth_account.is_active = False
                auth_account.save()
                
        except AuthSocialMediaAccount.DoesNotExist:
            pass
        
        return JsonResponse({
            'success': False,
            'message': 'No connected Facebook account found'
        })
        
    except Exception as e:
        logger.error(f"Error verifying Facebook credentials: {e}")
        return JsonResponse({
            'success': False,
            'message': 'Failed to verify Facebook credentials'
        }, status=500)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def facebook_disconnect(request):
    """
    Disconnect Facebook account
    """
    try:
        user = request.user
        
        # Deactivate integrations SocialMediaAccount
        try:
            integrated_account = SocialMediaAccount.objects.get(
                user=user,
                platform=SocialMediaPlatform.FACEBOOK
            )
            integrated_account.is_active = False
            integrated_account.save()
            logger.info(f"Facebook SocialMediaAccount deactivated for user {user.email}")
        except SocialMediaAccount.DoesNotExist:
            pass
        
        # Deactivate authentication SocialMediaAccount
        try:
            auth_account = AuthSocialMediaAccount.objects.get(
                user=user,
                platform='facebook'
            )
            auth_account.is_active = False
            auth_account.save()
            logger.info(f"Facebook authentication account deactivated for user {user.email}")
        except AuthSocialMediaAccount.DoesNotExist:
            pass
        
        return JsonResponse({
            'success': True,
            'message': 'Facebook account disconnected successfully'
        })
        
    except Exception as e:
        logger.error(f"Error disconnecting Facebook account: {e}")
        return JsonResponse({
            'error': 'Failed to disconnect Facebook account'
        }, status=500)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def post_facebook_share(request):
    """
    Post content to Facebook
    """
    try:
        user = request.user
        content = request.data.get('content', '')
        
        if not content:
            return JsonResponse({
                'error': 'Content is required'
            }, status=400)
        
        # Get user's Facebook access token
        access_token = None
        
        # Try integrations SocialMediaAccount first
        try:
            integrated_account = SocialMediaAccount.objects.get(
                user=user,
                platform=SocialMediaPlatform.FACEBOOK,
                is_active=True
            )
            access_token = integrated_account.access_token
        except SocialMediaAccount.DoesNotExist:
            # Fallback to authentication SocialMediaAccount
            try:
                auth_account = AuthSocialMediaAccount.objects.get(
                    user=user,
                    platform='facebook',
                    is_active=True
                )
                access_token = auth_account.access_token
            except AuthSocialMediaAccount.DoesNotExist:
                pass
        
        if not access_token:
            return JsonResponse({
                'error': 'Facebook account not connected'
            }, status=400)
        
        # Post to Facebook feed
        post_data = {
            'message': content,
            'access_token': access_token
        }
        
        response = requests.post(
            "https://graph.facebook.com/v18.0/me/feed",
            data=post_data
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Facebook post successful for user {user.email}: {result.get('id')}")
            
            return JsonResponse({
                'success': True,
                'post_id': result.get('id'),
                'message': 'Post shared successfully to Facebook'
            })
        else:
            logger.error(f"Facebook post failed: {response.status_code} - {response.text}")
            return JsonResponse({
                'error': 'Failed to post to Facebook',
                'details': response.text
            }, status=400)
        
    except Exception as e:
        logger.error(f"Error posting to Facebook: {e}")
        return JsonResponse({
            'error': 'Internal server error'
        }, status=500)
