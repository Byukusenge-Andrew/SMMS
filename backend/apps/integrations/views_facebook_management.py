"""
Facebook Account Management Views
Handles Facebook account settings, permissions, and management features
"""
import logging
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings

from apps.integrations.models import SocialMediaAccount, SocialMediaPlatform
from apps.integrations.social_media_integrator import FacebookIntegrator
from apps.integrations.views_facebook import IsAuthenticatedOrOptions

logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrOptions])
def facebook_account_details(request):
    """Get detailed Facebook account information"""
    try:
        facebook_accounts = SocialMediaAccount.objects.filter(
            user=request.user,
            platform=SocialMediaPlatform.FACEBOOK,
            is_active=True
        )
        
        if not facebook_accounts.exists():
            return Response({
                'success': False,
                'message': 'No Facebook account connected'
            }, status=404)
        
        account = facebook_accounts.first()
        facebook_integrator = FacebookIntegrator()
        
        # Get basic account info
        credentials = {'access_token': account.access_token}
        account_info = facebook_integrator.get_account_info(credentials)
        
        if not account_info.get('verified'):
            return Response({
                'success': False,
                'message': 'Facebook account token is invalid',
                'error': account_info.get('error')
            }, status=400)
        
        # Get user's pages
        pages_response = requests.get(
            "https://graph.facebook.com/v18.0/me/accounts",
            params={"access_token": account.access_token, "fields": "id,name,category,access_token,tasks"},
            timeout=30
        )
        
        pages = []
        if pages_response.status_code == 200:
            pages_data = pages_response.json()
            pages = pages_data.get("data", [])
        
        # Get token permissions
        permissions_response = requests.get(
            "https://graph.facebook.com/v18.0/me/permissions",
            params={"access_token": account.access_token},
            timeout=30
        )
        
        permissions = []
        if permissions_response.status_code == 200:
            permissions_data = permissions_response.json()
            permissions = permissions_data.get("data", [])
        
        return Response({
            'success': True,
            'account': {
                'id': str(account.id),
                'username': account.username,
                'display_name': account.display_name,
                'profile_image_url': account.profile_image_url,
                'platform_user_id': account.platform_user_id,
                'is_verified': account.is_verified,
                'followers_count': account.followers_count,
                'signature': account.signature,
                'connected_at': account.created_at.isoformat() if account.created_at else None,
                'facebook_info': {
                    'user_id': account_info.get('user_id'),
                    'email': account_info.get('email', ''),
                    'name': account_info.get('username', ''),
                }
            },
            'pages': [{
                'id': page.get('id'),
                'name': page.get('name'),
                'category': page.get('category'),
                'has_manage_posts': 'MANAGE' in page.get('tasks', []),
                'has_page_token': bool(page.get('access_token'))
            } for page in pages],
            'permissions': [{
                'permission': perm.get('permission'),
                'status': perm.get('status')
            } for perm in permissions]
        })
        
    except Exception as e:
        logger.error(f"Error getting Facebook account details: {e}")
        return Response({
            'success': False,
            'message': 'Failed to get account details'
        }, status=500)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_facebook_account(request):
    """Update Facebook account settings"""
    try:
        facebook_accounts = SocialMediaAccount.objects.filter(
            user=request.user,
            platform=SocialMediaPlatform.FACEBOOK,
            is_active=True
        )
        
        if not facebook_accounts.exists():
            return Response({
                'success': False,
                'message': 'No Facebook account connected'
            }, status=404)
        
        account = facebook_accounts.first()
        data = request.data
        
        # Update allowed fields
        if 'signature' in data:
            account.signature = data['signature'][:120]  # Limit to 120 chars
        
        if 'display_name' in data:
            account.display_name = data['display_name'][:200]
        
        account.save()
        
        logger.info(f"Updated Facebook account settings for user {request.user.id}")
        
        return Response({
            'success': True,
            'message': 'Account settings updated successfully',
            'account': {
                'signature': account.signature,
                'display_name': account.display_name
            }
        })
        
    except Exception as e:
        logger.error(f"Error updating Facebook account: {e}")
        return Response({
            'success': False,
            'message': 'Failed to update account settings'
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def refresh_facebook_token(request):
    """Refresh Facebook access token"""
    try:
        facebook_accounts = SocialMediaAccount.objects.filter(
            user=request.user,
            platform=SocialMediaPlatform.FACEBOOK,
            is_active=True
        )
        
        if not facebook_accounts.exists():
            return Response({
                'success': False,
                'message': 'No Facebook account connected'
            }, status=404)
        
        account = facebook_accounts.first()
        
        # Try to extend the token
        app_id = settings.SOCIAL_MEDIA_CONFIGS['FACEBOOK']['APP_ID']
        app_secret = settings.SOCIAL_MEDIA_CONFIGS['FACEBOOK']['APP_SECRET']
        
        extend_response = requests.get(
            "https://graph.facebook.com/v18.0/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": app_id,
                "client_secret": app_secret,
                "fb_exchange_token": account.access_token
            },
            timeout=30
        )
        
        if extend_response.status_code == 200:
            token_data = extend_response.json()
            new_token = token_data.get('access_token')
            
            if new_token:
                account.access_token = new_token
                account.save()
                
                logger.info(f"Refreshed Facebook token for user {request.user.id}")
                
                return Response({
                    'success': True,
                    'message': 'Token refreshed successfully'
                })
        
        return Response({
            'success': False,
            'message': 'Failed to refresh token. Please reconnect your account.'
        }, status=400)
        
    except Exception as e:
        logger.error(f"Error refreshing Facebook token: {e}")
        return Response({
            'success': False,
            'message': 'Failed to refresh token'
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def facebook_posting_analytics(request):
    """Get Facebook posting analytics and insights"""
    try:
        from apps.posts.models import Post
        from django.utils import timezone
        from datetime import timedelta
        
        # Get Facebook posts from last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        facebook_posts = Post.objects.filter(
            user=request.user,
            platform__icontains='facebook',
            created_at__gte=thirty_days_ago
        )
        
        # Calculate statistics
        total_posts = facebook_posts.count()
        published_posts = facebook_posts.filter(status='published').count()
        failed_posts = facebook_posts.filter(status='failed').count()
        scheduled_posts = facebook_posts.filter(status='scheduled').count()
        
        # Get recent posts
        recent_posts = facebook_posts.order_by('-created_at')[:10]
        
        return Response({
            'success': True,
            'analytics': {
                'total_posts': total_posts,
                'published_posts': published_posts,
                'failed_posts': failed_posts,
                'scheduled_posts': scheduled_posts,
                'success_rate': round((published_posts / total_posts * 100) if total_posts > 0 else 0, 1)
            },
            'recent_posts': [{
                'id': str(post.id),
                'content': post.content[:100] + '...' if len(post.content) > 100 else post.content,
                'status': post.status,
                'created_at': post.created_at.isoformat(),
                'scheduled_time': post.scheduled_time.isoformat() if post.scheduled_time else None,
                'published_at': post.published_at.isoformat() if post.published_at else None
            } for post in recent_posts]
        })
        
    except Exception as e:
        logger.error(f"Error getting Facebook analytics: {e}")
        return Response({
            'success': False,
            'message': 'Failed to get analytics'
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_facebook_connection(request):
    """Test Facebook connection and posting capability"""
    try:
        facebook_accounts = SocialMediaAccount.objects.filter(
            user=request.user,
            platform=SocialMediaPlatform.FACEBOOK,
            is_active=True
        )
        
        if not facebook_accounts.exists():
            return Response({
                'success': False,
                'message': 'No Facebook account connected'
            }, status=404)
        
        account = facebook_accounts.first()
        facebook_integrator = FacebookIntegrator()
        
        # Test account verification
        credentials = {'access_token': account.access_token}
        account_info = facebook_integrator.verify_account(credentials)
        
        if not account_info.get('verified'):
            return Response({
                'success': False,
                'message': 'Facebook account verification failed',
                'error': account_info.get('error')
            })
        
        # Test getting pages
        pages_response = requests.get(
            "https://graph.facebook.com/v18.0/me/accounts",
            params={"access_token": account.access_token},
            timeout=30
        )
        
        pages_available = pages_response.status_code == 200
        pages_count = len(pages_response.json().get("data", [])) if pages_available else 0
        
        # Test permissions
        permissions_response = requests.get(
            "https://graph.facebook.com/v18.0/me/permissions",
            params={"access_token": account.access_token},
            timeout=30
        )
        
        has_required_permissions = False
        if permissions_response.status_code == 200:
            permissions_data = permissions_response.json()
            permissions = permissions_data.get("data", [])
            granted_permissions = [p.get('permission') for p in permissions if p.get('status') == 'granted']
            
            required_permissions = ['pages_manage_posts', 'pages_read_engagement']
            has_required_permissions = all(perm in granted_permissions for perm in required_permissions)
        
        return Response({
            'success': True,
            'connection_status': {
                'account_verified': True,
                'pages_accessible': pages_available,
                'pages_count': pages_count,
                'has_required_permissions': has_required_permissions,
                'can_post': pages_available and has_required_permissions,
                'account_name': account_info.get('username', 'Unknown')
            }
        })
        
    except Exception as e:
        logger.error(f"Error testing Facebook connection: {e}")
        return Response({
            'success': False,
            'message': 'Failed to test connection'
        }, status=500)
