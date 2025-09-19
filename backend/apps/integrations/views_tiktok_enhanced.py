"""
TikTok OAuth Views - Enhanced Version
Similar implementation to Twitter with proper session management and PKCE
"""
import json
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from django.shortcuts import redirect
from urllib.parse import urlencode
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication

from apps.authentication.models import SocialMediaAccount
from .services.tiktok_service import TikTokService
from .models import SocialMediaAccount as IntegratedAccount, SocialMediaPlatform

logger = logging.getLogger(__name__)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([permissions.IsAuthenticated])
def tiktok_authorize(request):
    """Initiate TikTok OAuth 2.0 flow with PKCE."""
    client_key = getattr(settings, 'TIKTOK_CLIENT_KEY', None) or ''
    redirect_uri = getattr(settings, 'TIKTOK_REDIRECT_URI', None) or request.build_absolute_uri('/api/integrations/tiktok/callback/')
    scopes = getattr(settings, 'TIKTOK_SCOPES', 'user.info.basic,user.info.profile,user.info.stats,video.list,video.upload')

    if not client_key:
        return Response({'success': False, 'error': 'TIKTOK_CLIENT_KEY not configured'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Generate PKCE parameters and state
    import secrets
    import json
    import base64
    import time
    import hashlib
    
    # Generate code verifier and challenge for PKCE
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('utf-8')).digest()
    ).decode('utf-8').rstrip('=')
    
    # Generate state parameter
    state_data = {
        'csrf_token': secrets.token_urlsafe(16),
        'user_id': request.user.id,
        'timestamp': int(time.time())
    }
    state_val = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
    
    # Force session creation and save
    if not request.session.session_key:
        request.session.create()
    
    request.session['tiktok_oauth'] = {
        'state': state_val,
        'redirect_uri': redirect_uri,
        'popup_mode': True,
        'user_id': request.user.id,
        'code_verifier': code_verifier,
    }
    request.session.modified = True
    request.session.save()
    
    # Debug logging
    logger.info(f"TikTok authorize: Saving to session: user_id={request.user.id}, state={state_val[:50]}...")
    logger.info(f"TikTok authorize: Session key={request.session.session_key}")
    logger.info(f"TikTok authorize: Session data saved: {request.session.get('tiktok_oauth')}")

    # Build authorization URL
    params = {
        'client_key': client_key,
        'response_type': 'code',
        'redirect_uri': redirect_uri,
        'scope': scopes,
        'state': state_val,
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256'
    }
    
    url = f"https://www.tiktok.com/v2/auth/authorize/?{urlencode(params)}"
    
    # Debug logging
    logger.info(f"TikTok OAuth URL generated: {url}")
    logger.info(f"TikTok OAuth params: {params}")
    logger.info(f"Redirect URI being used: {redirect_uri}")
    
    return Response({'authorize_url': url})


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def tiktok_callback(request):
    """Handle TikTok OAuth 2.0 callback with proper state validation and token exchange."""
    from requests import post
    
    code = request.GET.get('code')
    state = request.GET.get('state')
    error = request.GET.get('error')
    error_description = request.GET.get('error_description')
    
    if error:
        logger.error(f"TikTok OAuth error: {error} - {error_description}")
        return Response({'success': False, 'error': f'TikTok OAuth error: {error}'}, status=status.HTTP_400_BAD_REQUEST)
    
    if not code:
        return Response({'success': False, 'error': 'Missing authorization code'}, status=status.HTTP_400_BAD_REQUEST)

    # Get session data
    session_data = request.session.get('tiktok_oauth') or {}
    popup_mode = session_data.get('popup_mode', False)
    
    # Debug session data
    logger.info(f"TikTok callback session data: state_expected={session_data.get('state')}, state_received={state}")
    logger.info(f"TikTok callback session data: popup_mode={popup_mode}")
    logger.info(f"TikTok callback session data: user_id={session_data.get('user_id')}")
    
    # Validate state
    expected_state = session_data.get('state')
    state_ok = (not expected_state) or (expected_state == state)
    
    if not state_ok:
        logger.warning(f"TikTok callback: State mismatch - expected: {expected_state}, received: {state}")
        if popup_mode:
            error_data = {'success': False, 'error': 'Invalid OAuth state. Please retry connection.'}
            return HttpResponse(f"""
            <script>
                window.opener.postMessage({{
                    source: 'tiktok-oauth',
                    data: '{json.dumps(error_data)}'
                }}, '*');
                window.close();
            </script>
            """, content_type='text/html')
        return Response({'success': False, 'error': 'Invalid OAuth state. Please retry connection.'}, status=status.HTTP_400_BAD_REQUEST)

    # Get credentials and session data
    client_key = getattr(settings, 'TIKTOK_CLIENT_KEY', None)
    client_secret = getattr(settings, 'TIKTOK_CLIENT_SECRET', None)
    redirect_uri = getattr(settings, 'TIKTOK_REDIRECT_URI', None) or request.build_absolute_uri('/api/integrations/tiktok/callback/')
    code_verifier = session_data.get('code_verifier', '')
    
    if not client_key or not client_secret:
        return Response({'success': False, 'error': 'TikTok client credentials not configured'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Exchange code for tokens
    token_data = {
        'client_key': client_key,
        'client_secret': client_secret,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': redirect_uri,
    }
    
    if code_verifier:
        token_data['code_verifier'] = code_verifier
        logger.info(f"TikTok callback: Using PKCE code verifier")
    else:
        logger.warning(f"TikTok callback: No PKCE code verifier found in session")

    try:
        token_resp = post(
            'https://open.tiktokapis.com/v2/oauth/token/',
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data=token_data,
            timeout=15
        )
        logger.info(f"TikTok token exchange response status: {token_resp.status_code}")
        
        if token_resp.status_code >= 400:
            logger.error(f"TikTok token exchange failed: {token_resp.status_code} - {token_resp.text}")
            error_msg = 'Token exchange failed'
            try:
                error_detail = token_resp.json()
                error_msg = f"Token exchange failed: {error_detail}"
                logger.error(f"TikTok token exchange error details: {error_detail}")
            except Exception:
                logger.error(f"TikTok token exchange error (raw): {token_resp.text}")
            
            if popup_mode:
                error_data = {'success': False, 'error': error_msg}
                return HttpResponse(f"""
                <script>
                    window.opener.postMessage({{
                        source: 'tiktok-oauth',
                        data: '{json.dumps(error_data)}'
                    }}, '*');
                    window.close();
                </script>
                """, content_type='text/html')
            return Response({'success': False, 'error': error_msg}, status=token_resp.status_code)
    except Exception as e:
        logger.error(f"TikTok token exchange request failed: {e}")
        error_msg = f'Token exchange request failed: {str(e)}'
        if popup_mode:
            error_data = {'success': False, 'error': error_msg}
            return HttpResponse(f"""
            <script>
                window.opener.postMessage({{
                    source: 'tiktok-oauth',
                    data: '{json.dumps(error_data)}'
                }}, '*');
                window.close();
            </script>
            """, content_type='text/html')
        return Response({'success': False, 'error': error_msg}, status=status.HTTP_502_BAD_GATEWAY)

    token_json = token_resp.json()
    access_token = token_json.get('access_token')
    refresh_token = token_json.get('refresh_token')
    expires_in = token_json.get('expires_in')
    open_id = token_json.get('open_id')

    # Fetch user identity using the new token
    try:
        import requests as _r
        user_resp = _r.post(
            'https://open.tiktokapis.com/v2/user/info/',
            headers={'Authorization': f'Bearer {access_token}'},
            data={'fields': 'open_id,union_id,avatar_url,display_name,username,follower_count,following_count,likes_count,video_count'},
            timeout=15
        )
        user_resp.raise_for_status()
        user_json = user_resp.json().get('data', {}).get('user', {})
    except Exception as e:
        logger.error(f"TikTok /user/info failed: {e}")
        if popup_mode:
            error_data = {'success': False, 'error': 'Failed to fetch user profile'}
            return HttpResponse(f"""
            <script>
                window.opener.postMessage({{
                    source: 'tiktok-oauth',
                    data: '{json.dumps(error_data)}'
                }}, '*');
                window.close();
            </script>
            """, content_type='text/html')
        return Response({'success': False, 'error': 'Failed to fetch user profile'}, status=status.HTTP_502_BAD_GATEWAY)

    # Get user from session or state
    user_id = session_data.get('user_id')
    current_user = None
    
    # Try to decode user ID from state parameter
    if state and not current_user:
        try:
            import json
            import base64
            state_data = json.loads(base64.urlsafe_b64decode(state.encode()).decode())
            state_user_id = state_data.get('user_id')
            if state_user_id:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                current_user = User.objects.get(id=state_user_id)
                logger.info(f"TikTok callback: Found user from state parameter: {current_user.username} (ID: {state_user_id})")
        except Exception as e:
            logger.warning(f"TikTok callback: Could not decode user from state parameter: {e}")
    
    # Fallback to session user ID
    if user_id and not current_user:
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            current_user = User.objects.get(id=user_id)
            logger.info(f"TikTok callback: Found user from session: {current_user.username} (ID: {user_id})")
        except Exception as e:
            logger.error(f"TikTok callback: Could not get user from session user_id {user_id}: {e}")
    
    if current_user:
        try:
            platform_user_id = user_json.get('open_id') or open_id
            
            # Create/update IntegratedAccount
            integrated_account, created = IntegratedAccount.objects.update_or_create(
                user=current_user,
                platform='tiktok',
                platform_user_id=platform_user_id,
                defaults={
                    'username': user_json.get('username', ''),
                    'display_name': user_json.get('display_name', ''),
                    'email': '',  # TikTok doesn't provide email
                    'profile_image_url': user_json.get('avatar_url', ''),
                    'followers_count': user_json.get('follower_count', 0),
                    'following_count': user_json.get('following_count', 0),
                    'posts_count': user_json.get('video_count', 0),
                    'is_verified': False,  # TikTok doesn't provide this in basic scope
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'token_expires_at': timezone.now() + timezone.timedelta(seconds=expires_in) if expires_in else None,
                    'is_active': True,
                }
            )
            
            logger.info(f"TikTok tokens bound successfully for user {current_user.id}, platform_user_id: {platform_user_id}")
                
        except Exception as e:
            logger.error(f"Failed to bind TikTok tokens for user {current_user.id}: {e}")
    else:
        logger.warning("TikTok callback: No user context found - tokens cannot be saved")

    # Prepare response data
    response_data = {
        'success': True,
        'account': {
            'platform': 'tiktok',
            'platform_user_id': user_json.get('open_id') or open_id,
            'username': user_json.get('username'),
            'display_name': user_json.get('display_name'),
            'profile_image_url': user_json.get('avatar_url'),
            'followers_count': user_json.get('follower_count', 0),
            'following_count': user_json.get('following_count', 0),
            'posts_count': user_json.get('video_count', 0),
        },
        'tokens': {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_in': expires_in
        }
    }

    # Clear used state
    try:
        del request.session['tiktok_oauth']
    except Exception:
        pass

    # Handle popup mode
    if popup_mode:
        return HttpResponse(f"""
        <script>
            window.opener.postMessage({{
                source: 'tiktok-oauth',
                data: {json.dumps(response_data)}
            }}, '*');
            window.close();
        </script>
        """, content_type='text/html')

    # Return JSON response for non-popup mode
    return Response(response_data)