"""
Twitter/X API Views
"""
import json
import logging
import time
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
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse

from apps.authentication.models import SocialMediaAccount
from .services.twitter_service import twitter_service
from .models import TwitterPost, SocialMediaAccount as IntegratedAccount, SocialMediaPlatform, PostStatus
from .serializers import TwitterPostSerializer, TwitterPostCreateSerializer

logger = logging.getLogger(__name__)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([permissions.IsAuthenticated])
def twitter_authorize(request):
    """Initiate Twitter OAuth 2.0 flow (Authorization Code with PKCE)."""
    client_id = getattr(settings, 'TWITTER_CLIENT_ID', None) or ''
    redirect_uri = getattr(settings, 'TWITTER_REDIRECT_URI', None) or request.build_absolute_uri('/api/integrations/twitter/callback/')
    scope = getattr(settings, 'TWITTER_SCOPES', 'tweet.read tweet.write users.read offline.access')

    if not client_id:
        return Response({'success': False, 'error': 'TWITTER_CLIENT_ID not configured'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Generate PKCE parameters
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
    
    # Generate a per-request state and store in session for CSRF protection
    state_data = {
        'csrf_token': secrets.token_urlsafe(16),
        'user_id': request.user.id,
        'timestamp': int(time.time())
    }
    state_val = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
    
    # Ensure session is created and working
    if not request.session.session_key:
        request.session.create()
        logger.info(f"Twitter authorize: Created new session with key={request.session.session_key}")
    
    oauth_data = {
        'state': state_val,
        'redirect_uri': redirect_uri,
        'popup_mode': True,
        'user_id': request.user.id,
        'code_verifier': code_verifier,
        'created_at': int(time.time()),  # Track when this was created
    }
    
    # Store in session
    request.session['twitter_oauth'] = oauth_data
    request.session.modified = True
    
    # Verify data was saved correctly
    saved_data = request.session.get('twitter_oauth')
    if not saved_data or saved_data.get('code_verifier') != code_verifier:
        logger.error("Twitter authorize: Session data not saved correctly!")
        logger.error(f"Expected: {oauth_data}")
        logger.error(f"Got: {saved_data}")
        return Response({
            'success': False,
            'error': 'Session storage failed'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    # Force save and verify session is working
    request.session.save()
    verify_key = request.session.session_key
    logger.info(f"Twitter authorize: Verified session key={verify_key}")
    logger.info(f"Twitter authorize: Session contains: {list(request.session.keys())}")
    logger.info(f"Twitter authorize: OAuth data saved: {json.dumps(saved_data, default=str)}")

    params = {
        'response_type': 'code',
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'scope': scope,
        'state': state_val,
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256'
    }
    url = f"https://twitter.com/i/oauth2/authorize?{urlencode(params)}"
    
    # Debug: Log the complete authorization URL and parameters
    logger.info(f"Twitter OAuth URL generated: {url}")
    logger.info(f"Twitter OAuth params: {params}")
    logger.info(f"Redirect URI being used: {redirect_uri}")
    
    return Response({'authorize_url': url})


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def twitter_callback(request):
    """Handle OAuth 2.0 callback: exchange code for tokens and persist account."""
    from requests import post

    code = request.GET.get('code')
    state = request.GET.get('state')
    
    # Log incoming request details
    logger.info(f"Twitter callback received - Code: {code[:10]}... State: {state[:10]}...")
    logger.info(f"Request session key: {request.session.session_key}")
    logger.info(f"Available session keys: {list(request.session.keys())}")
    
    if not code:
        return Response({'success': False, 'error': 'Missing code'}, status=status.HTTP_400_BAD_REQUEST)

    # Attempt to get OAuth data from session
    session_data = request.session.get('twitter_oauth') or {}
    if not session_data:
        logger.error("Twitter callback: No OAuth data found in session!")
        logger.error(f"Session contains: {list(request.session.keys())}")
        return Response({
            'success': False,
            'error': 'Session data lost - please try authorizing again'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Extract key data with validation
    popup_mode = session_data.get('popup_mode', False)
    expected_state = session_data.get('state')
    code_verifier = session_data.get('code_verifier')
    created_at = session_data.get('created_at', 0)
    
    if not code_verifier:
        logger.error("Twitter callback: No code verifier in session data!")
        logger.error(f"Session data contains: {list(session_data.keys())}")
        return Response({
            'success': False,
            'error': 'PKCE verification failed - missing code verifier'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check for session expiry (30 minute limit)
    if created_at and (time.time() - created_at) > 1800:  # 30 minutes
        logger.error(f"Twitter callback: Session too old - created at {datetime.fromtimestamp(created_at).isoformat()}")
        return Response({
            'success': False,
            'error': 'Authorization session expired - please try again'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Log detailed session state
    logger.info("Twitter callback session data:")
    logger.info(f"- State (expected): {expected_state[:30] if expected_state else 'None'}")
    logger.info(f"- State (received): {state[:30] if state else 'None'}")
    logger.info(f"- Has code verifier: {'Yes' if code_verifier else 'No'}")
    logger.info(f"- Created at: {datetime.fromtimestamp(created_at).isoformat() if created_at else 'Unknown'}")
    logger.info(f"- Popup mode: {popup_mode}")
    logger.info(f"- User ID: {session_data.get('user_id')}")
    
    # Handle accept headers for popup/redirect mode
    accept = (request.META.get('HTTP_ACCEPT') or '')
    state_ok = (not expected_state) or (expected_state == state)
    
    if 'application/json' not in accept:
        if popup_mode:
            # Handle popup mode - return HTML that posts message to parent
            try:
                if not state_ok:
                    error_data = {'success': False, 'error': 'Invalid OAuth state. Please retry connection.'}
                    return HttpResponse(f"""
                    <script>
                        window.opener.postMessage({{
                            source: 'twitter-oauth',
                            data: '{json.dumps(error_data)}'
                        }}, '*');
                        window.close();
                    </script>
                    """, content_type='text/html')
                
                # Proceed with token exchange for popup mode
                # (rest of token exchange logic will be added below)
            except Exception as e:
                error_data = {'success': False, 'error': str(e)}
                return HttpResponse(f"""
                <script>
                    window.opener.postMessage({{
                        source: 'twitter-oauth',
                        data: '{json.dumps(error_data)}'
                    }}, '*');
                    window.close();
                </script>
                """, content_type='text/html')
        else:
            # Handle redirect mode
            try:
                from urllib.parse import quote
                frontend_url = getattr(settings, 'FRONTEND_URL', '').rstrip('/') or ''
                if frontend_url:
                    target = f"{frontend_url}/dashboard/integrations/twitter/callback"
                    sep = '?' if ('?' not in target) else '&'
                    if not state_ok:
                        return redirect(f"{target}{sep}error=state_mismatch")
                    # Preserve code & state for the SPA page to call JSON mode
                    return redirect(f"{target}{sep}code={quote(code)}&state={quote(state or '')}")
            except Exception:
                # Fall through to JSON mode if redirect prep fails
                pass

    if not state_ok:
        # JSON mode state failure
        try:
            del request.session['twitter_oauth']
        except Exception:
            pass
        return Response({'success': False, 'error': 'Invalid OAuth state. Please retry connection.'}, status=status.HTTP_400_BAD_REQUEST)

    client_id = getattr(settings, 'TWITTER_CLIENT_ID', None)
    client_secret = getattr(settings, 'TWITTER_CLIENT_SECRET', None)
    redirect_uri = getattr(settings, 'TWITTER_REDIRECT_URI', None) or request.build_absolute_uri('/api/integrations/twitter/callback/')
    code_verifier = session_data.get('code_verifier', '')
    
    if not client_id or not client_secret:
        return Response({'success': False, 'error': 'Twitter client credentials not configured'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Prepare token exchange data
    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri,
        'client_id': client_id,
        'client_secret': client_secret,
    }
    
    # Add PKCE code verifier if available
    if code_verifier:
        token_data['code_verifier'] = code_verifier
        logger.info(f"Twitter callback: Using PKCE code verifier")
    else:
        logger.warning(f"Twitter callback: No PKCE code verifier found in session")

    try:
        token_resp = post(
            'https://api.twitter.com/2/oauth2/token',
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data=token_data,
            timeout=15
        )
        logger.info(f"Twitter token exchange response status: {token_resp.status_code}")
        
        if token_resp.status_code >= 400:
            logger.error(f"Twitter token exchange failed: {token_resp.status_code} - {token_resp.text}")
            error_msg = 'Token exchange failed'
            try:
                error_detail = token_resp.json()
                error_msg = f"Token exchange failed: {error_detail}"
                logger.error(f"Twitter token exchange error details: {error_detail}")
            except Exception:
                logger.error(f"Twitter token exchange error (raw): {token_resp.text}")
            
            if popup_mode:
                error_data = {'success': False, 'error': error_msg}
                return HttpResponse(f"""
                <script>
                    window.opener.postMessage({{
                        source: 'twitter-oauth',
                        data: '{json.dumps(error_data)}'
                    }}, '*');
                    window.close();
                </script>
                """, content_type='text/html')
            return Response({'success': False, 'error': error_msg}, status=token_resp.status_code)
    except Exception as e:
        logger.error(f"Twitter token exchange request failed: {e}")
        error_msg = f'Token exchange request failed: {str(e)}'
        if popup_mode:
            error_data = {'success': False, 'error': error_msg}
            return HttpResponse(f"""
            <script>
                window.opener.postMessage({{
                    source: 'twitter-oauth',
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

    # Fetch user identity using the new token
    try:
        import requests as _r
        me = _r.get(
            'https://api.twitter.com/2/users/me',
            headers={'Authorization': f'Bearer {access_token}'},
            params={'user.fields': 'id,name,username,profile_image_url,public_metrics,verified'},
            timeout=15
        )
        me.raise_for_status()
        me_json = me.json().get('data', {})
    except Exception as e:
        logger.error(f"Twitter /users/me failed: {e}")
        if popup_mode:
            error_data = {'success': False, 'error': 'Failed to fetch user profile'}
            return HttpResponse(f"""
            <script>
                window.opener.postMessage({{
                    source: 'twitter-oauth',
                    data: '{json.dumps(error_data)}'
                }}, '*');
                window.close();
            </script>
            """, content_type='text/html')
        return Response({'success': False, 'error': 'Failed to fetch user profile'}, status=status.HTTP_502_BAD_GATEWAY)

    # Bind tokens to the user's account
    user_id = session_data.get('user_id')
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
                logger.info(f"Twitter callback: Found user from state parameter: {current_user.username} (ID: {state_user_id})")
        except Exception as e:
            logger.warning(f"Twitter callback: Could not decode user from state parameter: {e}")
    
    # Fallback: Try to get user from session
    if user_id and not current_user:
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            current_user = User.objects.get(id=user_id)
            logger.info(f"Twitter callback: Found user from session: {current_user.username} (ID: {user_id})")
        except Exception as e:
            logger.error(f"Twitter callback: Could not get user from session user_id {user_id}: {e}")
    
    if current_user:
        try:
            platform_user_id = me_json.get('id')
            
            # Create/update IntegratedAccount
            integrated_account, created = IntegratedAccount.objects.update_or_create(
                user=current_user,
                platform='twitter',
                platform_user_id=platform_user_id,
                defaults={
                    'username': me_json.get('username', ''),
                    'display_name': me_json.get('name', ''),
                    'email': '',  # Twitter doesn't provide email in basic scope
                    'profile_image_url': me_json.get('profile_image_url', ''),
                    'followers_count': (me_json.get('public_metrics') or {}).get('followers_count', 0),
                    'following_count': (me_json.get('public_metrics') or {}).get('following_count', 0),
                    'posts_count': (me_json.get('public_metrics') or {}).get('tweet_count', 0),
                    'is_verified': me_json.get('verified', False),
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'token_expires_at': timezone.now() + timezone.timedelta(seconds=expires_in) if expires_in else None,
                    'is_active': True,
                }
            )
            
            # Mirror to apps.analytics.models.SocialMediaAccount if needed
            try:
                from apps.analytics.models import SocialMediaAccount
                platform_obj, _ = SocialMediaPlatform.objects.get_or_create(name='twitter')
                analytics_account, created = SocialMediaAccount.objects.update_or_create(
                    user=current_user,
                    platform=platform_obj,
                    platform_user_id=platform_user_id,
                    defaults={
                        'username': me_json.get('username', ''),
                        'access_token': access_token,
                        'refresh_token': refresh_token,
                        'is_active': True,
                    }
                )
                logger.info(f"Twitter tokens bound successfully for user {current_user.id}, platform_user_id: {platform_user_id}")
            except Exception as e:
                logger.error(f"Failed to create analytics SocialMediaAccount for Twitter: {e}")
                
        except Exception as e:
            logger.error(f"Failed to bind Twitter tokens for user {current_user.id}: {e}")
    else:
        logger.warning("Twitter callback: No user context found - tokens cannot be saved")

    # Prepare response data
    response_data = {
        'success': True,
        'account': {
            'platform': 'twitter',
            'platform_user_id': me_json.get('id'),
            'username': me_json.get('username'),
            'display_name': me_json.get('name'),
            'profile_image_url': me_json.get('profile_image_url'),
            'followers_count': (me_json.get('public_metrics') or {}).get('followers_count', 0),
            'following_count': (me_json.get('public_metrics') or {}).get('following_count', 0),
            'posts_count': (me_json.get('public_metrics') or {}).get('tweet_count', 0),
            'is_verified': me_json.get('verified', False),
        },
        'tokens': {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_in': expires_in
        }
    }

    # Clear used state
    try:
        del request.session['twitter_oauth']
    except Exception:
        pass

    # Handle popup mode
    if popup_mode:
        return HttpResponse(f"""
        <script>
            window.opener.postMessage({{
                source: 'twitter-oauth',
                data: {json.dumps(response_data)}
            }}, '*');
            window.close();
        </script>
        """, content_type='text/html')

    # Return JSON response for non-popup mode
    return Response(response_data)


@extend_schema(
    operation_id="verify_twitter_credentials",
    responses={
        200: OpenApiResponse(description="Twitter credentials verified successfully"),
        400: OpenApiResponse(description="Invalid credentials or API error"),
        401: OpenApiResponse(description="Authentication required")
    },
    summary="Verify Twitter API credentials",
    description="Verify the Twitter API credentials and return authenticated user information"
)
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([permissions.IsAuthenticated])
def verify_twitter_credentials(request):
    """Verify Twitter API credentials"""
    try:
        account = IntegratedAccount.objects.filter(user=request.user, platform=SocialMediaPlatform.TWITTER, is_active=True).first()
        
        if not account:
            # No connected Twitter account found
            return Response({
                'success': False,
                'error': 'No connected Twitter account found'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        result = twitter_service.verify_credentials(account=account)
        
        if result['success']:
            # Store/update the Twitter account in the database
            account, created = IntegratedAccount.objects.update_or_create(
                user=request.user,
                platform=SocialMediaPlatform.TWITTER,
                platform_user_id=result['user_id'],
                defaults={
                    'username': result['username'],
                    'display_name': result['name'],
                    'profile_image_url': result.get('profile_image_url', ''),
                    'followers_count': result.get('followers_count', 0),
                    'following_count': result.get('following_count', 0),
                    'posts_count': result.get('tweet_count', 0),
                    'is_verified': result.get('verified', False),
                    'is_active': True,
                    'last_sync': timezone.now()
                }
            )
            
            logger.info(f"Twitter account {'created' if created else 'updated'} for user {request.user.username}")
            
            return Response({
                'success': True,
                'message': 'Twitter credentials verified successfully',
                'account': {
                    'id': str(account.id),
                    'username': result['username'],
                    'name': result['name'],
                    'followers_count': result.get('followers_count', 0),
                    'following_count': result.get('following_count', 0),
                    'verified': result.get('verified', False),
                    'created': created
                }
            })
        else:
            return Response({
                'success': False,
                'error': result['error']
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error verifying Twitter credentials: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    operation_id="post_tweet",
    request=TwitterPostCreateSerializer,
    responses={
        201: OpenApiResponse(description="Tweet posted successfully"),
        400: OpenApiResponse(description="Validation error or API error"),
        401: OpenApiResponse(description="Authentication required")
    },
    summary="Post a new tweet",
    description="Post a new tweet with optional media attachments"
)
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([permissions.IsAuthenticated])
def post_tweet(request):
    """Post a new tweet"""
    try:
        serializer = TwitterPostCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        tweet_text = serializer.validated_data['tweet_text']
        media_paths = serializer.validated_data.get('media_paths', [])
        scheduled_at = serializer.validated_data.get('scheduled_at')
        
        # Get user's Twitter account
        try:
            twitter_account = IntegratedAccount.objects.get(
                user=request.user,
                platform=SocialMediaPlatform.TWITTER,
                is_active=True
            )
        except IntegratedAccount.DoesNotExist:
            return Response({
                'success': False,
                'error': 'No active Twitter account found. Please connect your Twitter account first.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create TwitterPost object
        twitter_post = TwitterPost.objects.create(
            user=request.user,
            social_media_account=twitter_account,
            tweet_text=tweet_text,
            media_paths=media_paths,
            scheduled_at=scheduled_at,
            status=PostStatus.SCHEDULED if scheduled_at else PostStatus.DRAFT
        )
        
        # If not scheduled, post immediately
        if not scheduled_at:
            result = twitter_service.post_tweet(tweet_text, media_paths, account=twitter_account)
            
            if result['success']:
                twitter_post.tweet_id = result['tweet_id']
                twitter_post.status = PostStatus.PUBLISHED
                twitter_post.published_at = timezone.now()
                twitter_post.save()
                
                logger.info(f"Tweet posted successfully: {result['tweet_id']}")
                
                return Response({
                    'success': True,
                    'message': 'Tweet posted successfully',
                    'tweet': {
                        'id': str(twitter_post.id),
                        'tweet_id': result['tweet_id'],
                        'text': tweet_text,
                        'url': result['url'],
                        'published_at': twitter_post.published_at.isoformat()
                    }
                }, status=status.HTTP_201_CREATED)
            else:
                twitter_post.status = PostStatus.FAILED
                twitter_post.error_message = result['error']
                twitter_post.save()
                
                return Response({
                    'success': False,
                    'error': result['error']
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Scheduled tweet
            logger.info(f"Tweet scheduled for {scheduled_at}")
            return Response({
                'success': True,
                'message': f'Tweet scheduled for {scheduled_at}',
                'tweet': {
                    'id': str(twitter_post.id),
                    'text': tweet_text,
                    'scheduled_at': scheduled_at.isoformat(),
                    'status': twitter_post.status
                }
            }, status=status.HTTP_201_CREATED)
            
    except Exception as e:
        logger.error(f"Error posting tweet: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    operation_id="get_user_tweets",
    parameters=[
        OpenApiParameter('count', int, description='Number of tweets to retrieve (max 100)', default=10),
    ],
    responses={
        200: OpenApiResponse(description="User tweets retrieved successfully"),
        400: OpenApiResponse(description="API error"),
        401: OpenApiResponse(description="Authentication required")
    },
    summary="Get user's recent tweets",
    description="Retrieve recent tweets from the authenticated user's Twitter account"
)
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([permissions.IsAuthenticated])
def get_user_tweets(request):
    """Get user's recent tweets"""
    try:
        count = min(int(request.GET.get('count', 10)), 100)
        account = IntegratedAccount.objects.filter(user=request.user, platform=SocialMediaPlatform.TWITTER, is_active=True).first()
        if not account:
            return Response({'success': False, 'error': 'No connected Twitter account'}, status=status.HTTP_400_BAD_REQUEST)
        
        result = twitter_service.get_user_tweets(count=count, account=account)
        
        if result['success']:
            return Response({
                'success': True,
                'tweets': result['tweets'],
                'count': result['count']
            })
        else:
            return Response({
                'success': False,
                'error': result['error']
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error getting user tweets: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    operation_id="get_tweet_analytics",
    parameters=[
        OpenApiParameter('tweet_id', str, description='Twitter tweet ID', required=True),
    ],
    responses={
        200: OpenApiResponse(description="Tweet analytics retrieved successfully"),
        400: OpenApiResponse(description="Invalid tweet ID or API error"),
        401: OpenApiResponse(description="Authentication required")
    },
    summary="Get analytics for a specific tweet",
    description="Retrieve engagement metrics and analytics for a specific tweet"
)
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([permissions.IsAuthenticated])
def get_tweet_analytics(request, tweet_id):
    """Get analytics for a specific tweet"""
    try:
        account = IntegratedAccount.objects.filter(user=request.user, platform=SocialMediaPlatform.TWITTER, is_active=True).first()
        if not account:
            return Response({'success': False, 'error': 'No connected Twitter account'}, status=status.HTTP_400_BAD_REQUEST)
        result = twitter_service.get_tweet_analytics(tweet_id, account=account)
        
        if result['success']:
            # Update local TwitterPost if it exists
            try:
                twitter_post = TwitterPost.objects.get(
                    user=request.user,
                    tweet_id=tweet_id
                )
                metrics = result['metrics']
                twitter_post.retweet_count = metrics['retweet_count']
                twitter_post.like_count = metrics['like_count']
                twitter_post.reply_count = metrics['reply_count']
                twitter_post.quote_count = metrics['quote_count']
                twitter_post.impression_count = metrics.get('impression_count', 0)
                twitter_post.last_analytics_update = timezone.now()
                twitter_post.save()
                
                logger.info(f"Updated analytics for tweet {tweet_id}")
            except TwitterPost.DoesNotExist:
                logger.warning(f"TwitterPost not found for tweet_id {tweet_id}")
            
            return Response({
                'success': True,
                'analytics': result
            })
        else:
            return Response({
                'success': False,
                'error': result['error']
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error getting tweet analytics: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    operation_id="search_tweets",
    parameters=[
        OpenApiParameter('query', str, description='Search query', required=True),
        OpenApiParameter('count', int, description='Number of tweets to retrieve (max 100)', default=10),
    ],
    responses={
        200: OpenApiResponse(description="Search results retrieved successfully"),
        400: OpenApiResponse(description="Invalid query or API error"),
        401: OpenApiResponse(description="Authentication required")
    },
    summary="Search for tweets",
    description="Search for tweets based on keywords, hashtags, or mentions"
)
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([permissions.IsAuthenticated])
def search_tweets(request):
    """Search for tweets"""
    try:
        query = request.GET.get('query')
        if not query:
            return Response({
                'success': False,
                'error': 'Query parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        count = min(int(request.GET.get('count', 10)), 100)
        account = IntegratedAccount.objects.filter(user=request.user, platform=SocialMediaPlatform.TWITTER, is_active=True).first()
        if not account:
            return Response({'success': False, 'error': 'No connected Twitter account'}, status=status.HTTP_400_BAD_REQUEST)
        
        result = twitter_service.search_tweets(query, count, account=account)
        
        if result['success']:
            return Response({
                'success': True,
                'query': result['query'],
                'tweets': result['tweets'],
                'count': result['count']
            })
        else:
            return Response({
                'success': False,
                'error': result['error']
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error searching tweets: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    operation_id="delete_tweet",
    responses={
        200: OpenApiResponse(description="Tweet deleted successfully"),
        400: OpenApiResponse(description="Invalid tweet ID or API error"),
        401: OpenApiResponse(description="Authentication required")
    },
    summary="Delete a tweet",
    description="Delete a specific tweet by its ID"
)
@api_view(['DELETE'])
@authentication_classes([TokenAuthentication])
@permission_classes([permissions.IsAuthenticated])
def delete_tweet(request, tweet_id):
    """Delete a tweet"""
    try:
        account = IntegratedAccount.objects.filter(user=request.user, platform=SocialMediaPlatform.TWITTER, is_active=True).first()
        if not account:
            return Response({'success': False, 'error': 'No connected Twitter account'}, status=status.HTTP_400_BAD_REQUEST)
        result = twitter_service.delete_tweet(tweet_id, account=account)
        
        if result['success']:
            # Update local TwitterPost if it exists
            try:
                twitter_post = TwitterPost.objects.get(
                    user=request.user,
                    tweet_id=tweet_id
                )
                twitter_post.status = PostStatus.DELETED
                twitter_post.save()
                
                logger.info(f"Marked tweet {tweet_id} as deleted in database")
            except TwitterPost.DoesNotExist:
                logger.warning(f"TwitterPost not found for tweet_id {tweet_id}")
            
            return Response({
                'success': True,
                'message': 'Tweet deleted successfully',
                'tweet_id': tweet_id
            })
        else:
            return Response({
                'success': False,
                'error': result['error']
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error deleting tweet: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    operation_id="get_my_twitter_posts",
    parameters=[
        OpenApiParameter('status', str, description='Filter by post status (draft, scheduled, published, failed)', required=False),
        OpenApiParameter('limit', int, description='Number of posts to retrieve', default=20),
    ],
    responses={
        200: OpenApiResponse(description="Twitter posts retrieved successfully"),
        401: OpenApiResponse(description="Authentication required")
    },
    summary="Get user's Twitter posts",
    description="Retrieve the user's Twitter posts from the database with optional filtering"
)
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([permissions.IsAuthenticated])
def get_my_twitter_posts(request):
    """Get user's Twitter posts from database"""
    try:
        queryset = TwitterPost.objects.filter(user=request.user)
        
        # Filter by status if provided
        status_filter = request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Limit results
        limit = min(int(request.GET.get('limit', 20)), 100)
        posts = queryset[:limit]
        
        # Serialize posts
        serializer = TwitterPostSerializer(posts, many=True)
        
        return Response({
            'success': True,
            'posts': serializer.data,
            'count': len(serializer.data)
        })
        
    except Exception as e:
        logger.error(f"Error getting user's Twitter posts: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    operation_id="get_twitter_rate_limit",
    responses={
        200: OpenApiResponse(description="Rate limit status retrieved successfully"),
        400: OpenApiResponse(description="API error"),
        401: OpenApiResponse(description="Authentication required")
    },
    summary="Get Twitter API rate limit status",
    description="Check the current rate limit status for Twitter API endpoints"
)
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([permissions.IsAuthenticated])
def get_twitter_rate_limit(request):
    """Get Twitter API rate limit status"""
    try:
        account = IntegratedAccount.objects.filter(user=request.user, platform=SocialMediaPlatform.TWITTER, is_active=True).first()
        result = twitter_service.get_rate_limit_status(account=account)
        
        return Response({
            'success': result['success'],
            'data': result,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting Twitter rate limit: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([permissions.IsAuthenticated])
def twitter_bind_tokens(request):
    """Bind Twitter tokens and profile to authenticated user"""
    logger.info(f"Twitter bind tokens called for user: {request.user}")
    try:
        data = request.data or {}
        logger.info(f"Twitter bind tokens data: {data}")
        account_data = data.get('account') or {}
        tokens = data.get('tokens') or {}
        
        platform_user_id = account_data.get('platform_user_id')
        username = account_data.get('username', '')
        display_name = account_data.get('display_name', '')
        profile_image_url = account_data.get('profile_image_url', '')
        
        access_token = tokens.get('access_token', '')
        refresh_token = tokens.get('refresh_token', '')
        expires_in = tokens.get('expires_in')
        
        if not platform_user_id or not access_token:
            return Response({
                'success': False,
                'error': 'Missing required account/token fields'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not display_name:
            display_name = f"Twitter User {platform_user_id}"
        if not username:
            username = f"twitter_{platform_user_id}"
        
        # Store in IntegratedAccount
        account, created = IntegratedAccount.objects.update_or_create(
            user=request.user,
            platform=SocialMediaPlatform.TWITTER,
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
                user=request.user,
                platform='twitter',
                username=username,
                defaults=auth_defaults,
            )
        except Exception as e:
            logger.error(f"Failed to sync auth SocialMediaAccount for Twitter: {e}")
        
        logger.info(f"Twitter tokens bound successfully for user {request.user}, account_id: {account.id}")
        return Response({'success': True, 'account_id': str(account.id)})
        
    except Exception as e:
        logger.error(f"Error binding Twitter tokens: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([permissions.IsAuthenticated])
def twitter_disconnect(request):
    """Deactivate user's Twitter integration and purge tokens."""
    try:
        acct = IntegratedAccount.objects.filter(user=request.user, platform=SocialMediaPlatform.TWITTER, is_active=True).first()
        if not acct:
            return Response({'success': False, 'error': 'No active Twitter account'}, status=status.HTTP_400_BAD_REQUEST)
        acct.is_active = False
        acct.access_token = ''
        acct.refresh_token = ''
        acct.save(update_fields=['is_active', 'access_token', 'refresh_token'])
        # Also disable mirrored auth SocialMediaAccount if present
        try:
            from apps.authentication.models import SocialMediaAccount as AuthSMA
            AuthSMA.objects.filter(user=request.user, platform='twitter', username=acct.username).update(is_active=False, access_token='')
        except Exception:
            pass
        return Response({'success': True, 'message': 'Twitter disconnected'})
    except Exception as e:
        logger.error(f"Error disconnecting Twitter: {e}")
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
