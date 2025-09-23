"""
LinkedIn Integration Views
"""
import logging
from django.conf import settings
from django.shortcuts import redirect
from django.http import HttpResponse
from rest_framework import permissions, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse
from .models import SocialMediaAccount as IntegratedAccount, SocialMediaPlatform
from .social_media_integrator import LinkedInIntegrator

logger = logging.getLogger(__name__)


@extend_schema(
    operation_id="linkedin_authorize",
    responses={
        200: OpenApiResponse(description="LinkedIn authorization URL generated"),
        500: OpenApiResponse(description="Configuration error"),
    },
    summary="Get LinkedIn OAuth authorization URL",
    description="Generate LinkedIn OAuth authorization URL for user authentication"
)
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([permissions.IsAuthenticated])
def linkedin_authorize(request):
    """Get LinkedIn OAuth authorization URL"""
    try:
        linkedin_integrator = LinkedInIntegrator()
        # Use the exact redirect URI that's configured in LinkedIn app and .env
        callback_url = linkedin_integrator.redirect_uri
        
        # Generate state for CSRF protection without PKCE
        import secrets
        import json
        import base64
        import time
        
        # Encode user ID in state parameter for session-independent user identification
        state_data = {
            'csrf_token': secrets.token_urlsafe(16),
            'user_id': request.user.id,
            'timestamp': int(time.time())
        }
        state_val = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()

        # Optional redirect instruction from frontend (e.g., ?redirect=1&next=/dashboard/integrations)
        redirect_flag = str(request.GET.get('redirect', '')).lower() in {"1", "true", "yes"}
        next_path = request.GET.get('next') or "/dashboard/integrations"

        # Persist values in session for callback validation without PKCE
        request.session['linkedin_oauth'] = {
            'state': state_val,
            'redirect_uri': callback_url,
            'redirect': redirect_flag,
            'next': next_path,
            'user_id': request.user.id,  # Store user ID for callback
        }
        request.session.modified = True
        
        # Debug: Log what we're saving to session
        logger.info(f"LinkedIn authorize: Saving to session: user_id={request.user.id}, state={state_val}, redirect={redirect_flag}")
        logger.info(f"LinkedIn authorize: Session key={request.session.session_key}")
        logger.info(f"LinkedIn authorize: Session data saved: {request.session.get('linkedin_oauth')}")

        # Start OAuth without PKCE
        result = linkedin_integrator.start_oauth(callback_url, state=state_val, code_challenge=None)
        
        if 'error' in result:
            return Response({
                'success': False,
                'error': result['error']
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'success': True,
            'authorize_url': result['auth_url']
        })
        
    except Exception as e:
        logger.error(f"Error generating LinkedIn auth URL: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    operation_id="linkedin_callback",
    responses={
        200: OpenApiResponse(description="LinkedIn OAuth callback processed"),
        400: OpenApiResponse(description="Missing or invalid parameters"),
        500: OpenApiResponse(description="OAuth processing error"),
    },
    summary="Handle LinkedIn OAuth callback",
    description="Process LinkedIn OAuth callback and exchange code for tokens"
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def linkedin_callback(request):
    """Handle LinkedIn OAuth 2.0 callback.

    Modes:
      1. Redirect Mode (default when session oauth['redirect'] == True):
         Redirect the browser to the SPA frontend route.
      2. Headless/Test Harness Mode (oauth['redirect'] == False):
         Complete token exchange; if not JSON Accept header, return a tiny HTML page that posts
         the payload to window.opener then closes (for static harness usage).
    """
    try:
        code = request.GET.get('code')
        state = request.GET.get('state')
        error = request.GET.get('error')
        accept = request.META.get('HTTP_ACCEPT', '') or ''

        # Session values decide behavior
        sess = request.session.get('linkedin_oauth') or {}
        # If session missing, default to headless (False) so we can still try to exchange and postMessage
        redirect_pref = bool(sess.get('redirect')) if 'redirect' in sess else False
        
        # Debug session data
        logger.info(f"LinkedIn callback session data: state_expected={sess.get('state')}, state_received={state}")
        logger.info(f"LinkedIn callback session data: code_verifier disabled (PKCE not used)")
        logger.info(f"LinkedIn callback session data: callback_url={sess.get('callback_url')}")
        logger.info(f"LinkedIn callback session data: user_id={sess.get('user_id')}")
        logger.info(f"LinkedIn callback session data: redirect={sess.get('redirect')}")
        logger.info(f"LinkedIn callback session data: all_keys={list(sess.keys())}")
        logger.info(f"LinkedIn callback: session.session_key={request.session.session_key}")
        logger.info(f"LinkedIn callback: session keys={list(request.session.keys())}")

        # If browser navigation and redirect preference is True, bounce to frontend
        if 'application/json' not in accept and redirect_pref:
            from urllib.parse import quote
            target = f"{settings.FRONTEND_URL}/dashboard/integrations/linkedin/callback"
            sep = '?' if ('?' not in target) else '&'
            if error:
                return redirect(f"{target}{sep}error={quote(str(error))}&state={state or ''}")
            if code:
                return redirect(f"{target}{sep}code={code}&state={state or ''}")
            return redirect(f"{settings.FRONTEND_URL}/dashboard/integrations")
        # Error from provider
        if error:
            if sess.get('redirect'):
                target = sess.get('next') or "/dashboard/integrations"
                url = f"{settings.FRONTEND_URL}{target}"
                sep = '&' if ('?' in url) else '?'
                url = f"{url}{sep}linkedin=error&reason={error}"
                try:
                    del request.session['linkedin_oauth']
                except Exception:
                    pass
                return redirect(url)
            return Response({'success': False, 'error': f'LinkedIn OAuth error: {error}'}, status=status.HTTP_400_BAD_REQUEST)

        if not code:
            return Response({'success': False, 'error': 'Missing authorization code'}, status=status.HTTP_400_BAD_REQUEST)

        linkedin_integrator = LinkedInIntegrator()
        expected_state = sess.get('state')
        callback_url = sess.get('redirect_uri') or linkedin_integrator.redirect_uri

        logger.info(f"LinkedIn callback session data: state_expected={expected_state}, state_received={state}")
        logger.info(f"LinkedIn callback session data: PKCE disabled - no code verifier used")
        logger.info(f"LinkedIn callback session data: callback_url={callback_url}")

        if expected_state and state and expected_state != state:
            logger.error("LinkedIn state mismatch during callback")
            if sess.get('redirect'):
                target = sess.get('next') or "/dashboard/integrations"
                url = f"{settings.FRONTEND_URL}{target}"
                sep = '&' if ('?' in url) else '?'
                url = f"{url}{sep}linkedin=error&reason=state_mismatch"
                try:
                    del request.session['linkedin_oauth']
                except Exception:
                    pass
                return redirect(url)
            return Response({'success': False, 'error': 'Invalid OAuth state. Please try connecting again.'}, status=status.HTTP_400_BAD_REQUEST)

        # Exchange code for tokens without PKCE
        logger.info(f"Attempting token exchange for LinkedIn with code: {code[:10]}...")
        token_result = linkedin_integrator.exchange_code_for_tokens(code, callback_url, code_verifier=None)
        logger.info(f"Token exchange result: {token_result.get('success', False)}")

        if not token_result.get('success'):
            error_msg = token_result.get('error', 'Failed to exchange code for tokens')
            logger.error(f"LinkedIn token exchange failed: {error_msg}")
            if sess.get('redirect'):
                target = sess.get('next') or "/dashboard/integrations"
                url = f"{settings.FRONTEND_URL}{target}"
                sep = '&' if ('?' in url) else '?'
                from urllib.parse import quote
                url = f"{url}{sep}linkedin=error&reason={quote(str(error_msg))}"
                try:
                    del request.session['linkedin_oauth']
                except Exception:
                    pass
                return redirect(url)
            return Response({'success': False, 'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)

        access_token = token_result.get('access_token')
        profile_result = linkedin_integrator.get_profile(access_token)
        if not profile_result.get('success'):
            if sess.get('redirect'):
                target = sess.get('next') or "/dashboard/integrations"
                url = f"{settings.FRONTEND_URL}{target}"
                sep = '&' if ('?' in url) else '?'
                from urllib.parse import quote
                url = f"{url}{sep}linkedin=error&reason={quote(str(profile_result.get('error', 'profile_failed')))}"
                try:
                    del request.session['linkedin_oauth']
                except Exception:
                    pass
                return redirect(url)
            return Response({'success': False, 'error': profile_result.get('error', 'Failed to get user profile')}, status=status.HTTP_400_BAD_REQUEST)

        profile = profile_result.get('profile', {})

        # Save tokens directly to database if we have user context
        user_id = sess.get('user_id')
        current_user = None
        
        # Primary method: Try to decode user ID from state parameter
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
                    logger.info(f"LinkedIn callback: Found user from state parameter: {current_user.username} (ID: {state_user_id})")
            except Exception as e:
                logger.warning(f"LinkedIn callback: Could not decode user from state parameter: {e}")
        
        # Fallback: Try to get user from session (should work for OAuth redirects)
        if user_id and not current_user:
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                current_user = User.objects.get(id=user_id)
                logger.info(f"LinkedIn callback: Found user from session: {current_user.username} (ID: {user_id})")
            except Exception as e:
                logger.error(f"LinkedIn callback: Could not get user from session user_id {user_id}: {e}")
        
        # Last resort: try to get authenticated user from request (for API calls)
        if not current_user and hasattr(request, 'user') and request.user.is_authenticated:
            current_user = request.user
            logger.info(f"LinkedIn callback: Using authenticated user from request: {current_user.username} (ID: {current_user.id})")
        
        if not current_user:
            logger.warning("LinkedIn callback: No user context found - tokens cannot be saved")
            # For OAuth redirects, redirect to frontend with error
            if sess.get('redirect'):
                target = sess.get('next') or "/dashboard/integrations"
                url = f"{settings.FRONTEND_URL}{target}"
                sep = '&' if ('?' in url) else '?'
                url = f"{url}{sep}linkedin=error&reason=authentication_required"
                try:
                    del request.session['linkedin_oauth']
                except Exception:
                    pass
                return redirect(url)
            # For API calls, return 401 error
            return Response({
                'success': False, 
                'error': 'Authentication required. Please log in and try connecting LinkedIn again.'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        integration_saved = False
        if current_user:
            try:
                from .models import SocialMediaAccount as IntegratedAccount, SocialMediaPlatform
                from apps.authentication.models import SocialMediaAccount
                
                platform_user_id = profile.get('id')
                first_name = profile.get('first_name', '')
                last_name = profile.get('last_name', '')
                email = profile.get('email', '')
                profile_image_url = profile.get('profile_picture', '')
                
                access_token = token_result.get('access_token', '')
                refresh_token = token_result.get('refresh_token', '')
                expires_in = token_result.get('expires_in')
                
                if platform_user_id and access_token:
                    # Create display name and username
                    display_name = f"{first_name} {last_name}".strip()
                    if not display_name:
                        display_name = f"LinkedIn User {platform_user_id}"
                    # Use email as username if available, otherwise use platform_user_id
                    username = email if email else f"linkedin_{platform_user_id}"
                    
                    # Store in IntegratedAccount
                    account, created = IntegratedAccount.objects.update_or_create(
                        user=current_user,
                        platform=SocialMediaPlatform.LINKEDIN,
                        platform_user_id=platform_user_id,
                        defaults={
                            'username': username,
                            'display_name': display_name,
                            'profile_image_url': profile_image_url,
                            'is_active': True,
                            'access_token': access_token,
                            'refresh_token': refresh_token,
                        }
                    )
                    
                    if expires_in:
                        try:
                            from django.utils import timezone
                            account.token_expires_at = timezone.now() + timezone.timedelta(seconds=int(expires_in))
                            account.save(update_fields=['token_expires_at'])
                        except Exception:
                            pass
                    
                    # Mirror into auth app's SocialMediaAccount
                    try:
                        auth_defaults = {
                            'access_token': access_token,
                            'refresh_token': refresh_token,
                            'is_active': True,
                            'platform_user_id': platform_user_id,
                        }
                        
                        if expires_in:
                            try:
                                from django.utils import timezone as _tz
                                auth_defaults['token_expires_at'] = _tz.now() + _tz.timedelta(seconds=int(expires_in))
                            except Exception:
                                pass
                        
                        SocialMediaAccount.objects.update_or_create(
                            user=current_user,
                            platform='linkedin',
                            username=username,
                            defaults=auth_defaults,
                        )
                    except Exception as e:
                        logger.error(f"Failed to sync auth SocialMediaAccount for LinkedIn: {e}")
                    
                    integration_saved = True
                    logger.info(f"LinkedIn tokens saved successfully for user {current_user.username}, account_id: {account.id}")
                    
            except Exception as e:
                logger.error(f"Error saving LinkedIn integration: {e}")

        if sess.get('redirect'):
            target = sess.get('next') or "/dashboard/integrations"
            url = f"{settings.FRONTEND_URL}{target}"
            sep = '&' if ('?' in url) else '?'
            url = f"{url}{sep}linkedin=success"
            try:
                del request.session['linkedin_oauth']
            except Exception:
                pass
            return redirect(url)

        resp = {
            'success': True,
            'account': {
                'platform': 'linkedin',
                'platform_user_id': profile.get('id'),
                'first_name': profile.get('first_name'),
                'last_name': profile.get('last_name'),
                'email': profile.get('email'),
                'profile_image_url': profile.get('profile_picture'),
            },
            'tokens': {
                'access_token': access_token,
                'refresh_token': token_result.get('refresh_token'),
                'expires_in': token_result.get('expires_in'),
                'scope': token_result.get('scope'),
            }
        }
        try:
            del request.session['linkedin_oauth']
        except Exception:
            pass

        if 'application/json' in accept:
            return Response(resp)

        html = f"""<!DOCTYPE html><html><head><title>LinkedIn Connected</title></head>
<body style='font-family:system-ui; padding:20px;'>
<h3>LinkedIn Authorization Successful</h3>
<p>You can close this window.</p>
<script>
(function() {{
  try {{
    var payload = {resp};
    if (window.opener && window.opener.postMessage) {{
      window.opener.postMessage({{ source: 'linkedin-oauth', data: JSON.stringify(payload) }}, '*');
      setTimeout(function() {{ window.close(); }}, 400);
    }}
  }} catch(e) {{ console.error('postMessage failed', e); }}
}})();
</script>
</body></html>"""
        return HttpResponse(html)
    except Exception as e:
        logger.error(f"LinkedIn callback error: {e}")
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    operation_id="linkedin_bind_tokens",
    responses={
        200: OpenApiResponse(description="LinkedIn tokens bound successfully"),
        400: OpenApiResponse(description="Missing or invalid data"),
        500: OpenApiResponse(description="Server error"),
    },
    summary="Bind LinkedIn tokens to user account",
    description="Store LinkedIn OAuth tokens and profile info for authenticated user"
)
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([permissions.IsAuthenticated])
def linkedin_bind_tokens(request):
    """Bind LinkedIn tokens and profile to authenticated user"""
    logger.info(f"LinkedIn bind tokens called for user: {request.user}")
    try:
        data = request.data or {}
        logger.info(f"LinkedIn bind tokens data: {data}")
        account_data = data.get('account') or {}
        tokens = data.get('tokens') or {}
        
        platform_user_id = account_data.get('platform_user_id')
        first_name = account_data.get('first_name', '')
        last_name = account_data.get('last_name', '')
        email = account_data.get('email', '')
        profile_image_url = account_data.get('profile_image_url', '')
        
        access_token = tokens.get('access_token', '')
        refresh_token = tokens.get('refresh_token', '')
        expires_in = tokens.get('expires_in')
        
        if not platform_user_id or not access_token:
            return Response({
                'success': False,
                'error': 'Missing required account/token fields'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create display name and username
        display_name = f"{first_name} {last_name}".strip()
        if not display_name:
            display_name = f"LinkedIn User {platform_user_id}"
        # Use email as username if available, otherwise use platform_user_id
        username = email if email else f"linkedin_{platform_user_id}"
        
        # Store in IntegratedAccount
        account, created = IntegratedAccount.objects.update_or_create(
            user=request.user,
            platform=SocialMediaPlatform.LINKEDIN,
            platform_user_id=platform_user_id,
            defaults={
                'username': username,
                'display_name': display_name,
                'profile_image_url': profile_image_url,
                'is_active': True,
                'access_token': access_token,
                'refresh_token': refresh_token,
            }
        )
        
        if expires_in:
            try:
                from django.utils import timezone
                account.token_expires_at = timezone.now() + timezone.timedelta(seconds=int(expires_in))
                account.save(update_fields=['token_expires_at'])
            except Exception:
                pass
        
        # Mirror into auth app's SocialMediaAccount
        try:
            from apps.authentication.models import SocialMediaAccount
            from django.utils import timezone as _tz
            
            auth_defaults = {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'is_active': True,
                'platform_user_id': platform_user_id,
            }
            
            if expires_in:
                try:
                    auth_defaults['token_expires_at'] = _tz.now() + _tz.timedelta(seconds=int(expires_in))
                except Exception:
                    pass
            
            SocialMediaAccount.objects.update_or_create(
                user=request.user,
                platform='linkedin',
                username=username,
                defaults=auth_defaults,
            )
        except Exception as e:
            logger.error(f"Failed to sync auth SocialMediaAccount for LinkedIn: {e}")
        
        logger.info(f"LinkedIn tokens bound successfully for user {request.user}, account_id: {account.id}")
        return Response({'success': True, 'account_id': str(account.id)})
        
    except Exception as e:
        logger.error(f"Error binding LinkedIn tokens: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([permissions.IsAuthenticated])
def linkedin_disconnect(request):
    """Deactivate LinkedIn integration and clear tokens."""
    try:
        acct = IntegratedAccount.objects.filter(user=request.user, platform=SocialMediaPlatform.LINKEDIN, is_active=True).first()
        if not acct:
            return Response({'success': False, 'error': 'No active LinkedIn account'}, status=status.HTTP_400_BAD_REQUEST)
        acct.is_active = False
        acct.access_token = ''
        acct.refresh_token = ''
        acct.save(update_fields=['is_active', 'access_token', 'refresh_token'])
        try:
            from apps.authentication.models import SocialMediaAccount as AuthSMA
            AuthSMA.objects.filter(user=request.user, platform='linkedin', username=acct.username).update(is_active=False, access_token='')
        except Exception:
            pass
        return Response({'success': True, 'message': 'LinkedIn disconnected'})
    except Exception as e:
        logger.error(f"Error disconnecting LinkedIn: {e}")
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    operation_id="verify_linkedin_credentials",
    responses={
        200: OpenApiResponse(description="LinkedIn credentials verified successfully"),
        400: OpenApiResponse(description="Invalid credentials or API error"),
        401: OpenApiResponse(description="Authentication required")
    },
    summary="Verify LinkedIn API credentials",
    description="Verify the LinkedIn API credentials and return authenticated user information"
)
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([permissions.IsAuthenticated])
def verify_linkedin_credentials(request):
    """Verify LinkedIn API credentials"""
    try:
        account = IntegratedAccount.objects.filter(
            user=request.user, 
            platform=SocialMediaPlatform.LINKEDIN, 
            is_active=True
        ).first()
        
        if not account:
            # Not connected - return 400 so frontend knows it's not connected
            logger.warning(f"No active LinkedIn account found for user {request.user.email}")
            return Response({
                'success': False,
                'error': 'No connected LinkedIn account found'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        linkedin_integrator = LinkedInIntegrator()
        result = {}
        profile_fetched = False
        try:
            result = linkedin_integrator.get_profile(account.access_token)
            profile_fetched = bool(result.get('success'))
        except Exception as e:
            logger.warning(f"LinkedIn profile fetch failed: {e}")
            profile_fetched = False

        # If profile fetch failed, the token is likely invalid/revoked
        if not profile_fetched:
            logger.error(f"LinkedIn token verification failed for user {request.user.email}")
            return Response({
                'success': False,
                'error': 'LinkedIn token is invalid or expired. Please reconnect your account.',
                'error_code': 'INVALID_TOKEN'
            }, status=status.HTTP_400_BAD_REQUEST)

        if profile_fetched:
            # If we get here, profile was fetched successfully
            try:
                # Update account info when profile is available
                profile = result.get('profile', {})
                account.display_name = f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip() or account.display_name
                if profile.get('profile_picture'):
                    account.profile_image_url = profile.get('profile_picture')
                
                # Update count from LinkedIn connections (prefer connections)
                connection_count = profile.get('connection_count', 0) or profile.get('follower_count', 0)
                account.followers_count = connection_count
                
                account.is_verified = True
                account.save(update_fields=['display_name', 'profile_image_url', 'followers_count', 'is_verified'])
            except Exception:
                pass

            # Return success - token is verified and working
            return Response({
                'success': True,
                'message': 'LinkedIn account is connected and verified',
                'account': {
                    'id': str(account.id),
                    'platform': 'linkedin',
                    'username': account.username,
                    'display_name': account.display_name,
                    'profile_image_url': account.profile_image_url,
                    'connection_count': account.followers_count,
                    'follower_count': account.followers_count,  # backward-compatible alias
                    'is_verified': True,
                }
            }, status=status.HTTP_200_OK)
            
    except Exception as e:
        logger.error(f"Error verifying LinkedIn credentials: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    operation_id="post_linkedin_share",
    responses={
        201: OpenApiResponse(description="LinkedIn post shared successfully"),
        400: OpenApiResponse(description="Validation error or API error"),
        401: OpenApiResponse(description="Authentication required")
    },
    summary="Share a post on LinkedIn",
    description="Share a post on LinkedIn with the authenticated user's account"
)
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([permissions.IsAuthenticated])
def post_linkedin_share(request):
    """Share a post on LinkedIn"""
    try:
        content = request.data.get('content') or request.data.get('text')
        
        if not content:
            return Response({
                'success': False,
                'error': 'Content is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        account = IntegratedAccount.objects.filter(
            user=request.user, 
            platform=SocialMediaPlatform.LINKEDIN, 
            is_active=True
        ).first()
        
        if not account:
            return Response({
                'success': False,
                'error': 'No connected LinkedIn account'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        linkedin_integrator = LinkedInIntegrator()
        result = linkedin_integrator.publish_post(content, account.access_token)
        
        if result.get('success'):
            return Response({
                'success': True,
                'message': result.get('message'),
                'post_id': result.get('post_id'),
                'url': result.get('url'),
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'success': False,
                'error': result.get('error')
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error posting to LinkedIn: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
