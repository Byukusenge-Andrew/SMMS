"""
TikTok Integration Views

Handles TikTok OAuth authentication, video posting, and analytics
"""
import logging
import os
from django.shortcuts import redirect
from django.conf import settings
from django.core.files.storage import default_storage
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.request import Request

from .models import SocialMediaAccount, TikTokPost, SocialMediaPlatform, PostStatus
from .serializers import (
    TikTokPostCreateSerializer, 
    TikTokPostSerializer, 
    TikTokPostListSerializer,
    TikTokAnalyticsSerializer,
    TikTokVideoListSerializer,
    TikTokAuthSerializer
)
from .services.tiktok_service import TikTokService

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def tiktok_auth_url(request: Request):
    """Get TikTok OAuth authorization URL"""
    try:
        service = TikTokService()
        state = f"user_{request.user.id}_{timezone.now().timestamp()}"
        auth_url = service.get_authorization_url(state=state)
        
        return Response({
            'authorization_url': auth_url,
            'state': state
        })
    except Exception as e:
        logger.error(f"TikTok auth URL generation failed: {e}")
        return Response(
            {'error': 'Failed to generate authorization URL'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def tiktok_oauth_callback(request: Request):
    """Handle TikTok OAuth callback"""
    authorization_code = request.data.get('code')
    state = request.data.get('state')
    
    if not authorization_code:
        return Response(
            {'error': 'Authorization code is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        service = TikTokService()
        
        # Exchange code for tokens
        token_data = service.exchange_code_for_token(authorization_code)
        access_token = token_data.get('access_token')
        refresh_token = token_data.get('refresh_token')
        expires_in = token_data.get('expires_in')
        
        if not access_token:
            return Response(
                {'error': 'Failed to obtain access token'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get user info from TikTok
        user_info = service.get_user_info(access_token)
        open_id = user_info.get('open_id')
        display_name = user_info.get('display_name', '')
        avatar_url = user_info.get('avatar_url', '')
        
        if not open_id:
            return Response(
                {'error': 'Failed to get user information'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create or update social media account
        account, created = SocialMediaAccount.objects.update_or_create(
            user=request.user,
            platform=SocialMediaPlatform.TIKTOK,
            platform_user_id=open_id,
            defaults={
                'username': open_id,
                'display_name': display_name,
                'profile_image_url': avatar_url,
                'access_token': access_token,
                'refresh_token': refresh_token,
                'is_active': True,
                'is_verified': True,
            }
        )
        
        # Set token expiry
        if expires_in:
            account.set_token_expiry_from_expires_in(expires_in)
            account.save()
        
        return Response({
            'message': 'TikTok account connected successfully',
            'account_id': str(account.id),
            'display_name': display_name,
            'created': created
        })
        
    except Exception as e:
        logger.error(f"TikTok OAuth callback failed: {e}")
        return Response(
            {'error': 'Failed to connect TikTok account'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def tiktok_oauth_callback_get(request: Request):
    """Browser redirect style callback that forwards code to frontend for SPA binding (if ever needed)."""
    code = request.GET.get('code')
    state = request.GET.get('state')
    frontend = getattr(settings, 'FRONTEND_URL', '').rstrip('/')
    if not frontend:
        return Response({'error': 'FRONTEND_URL not configured'}, status=500)
    from urllib.parse import quote
    target = f"{frontend}/dashboard/integrations"  # Could create a dedicated callback page later
    if not code:
        return redirect(f"{target}?tiktok=error")
    return redirect(f"{target}?tiktok=code&code={quote(code)}&state={quote(state or '')}")


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def tiktok_accounts(request: Request):
    """Get user's connected TikTok accounts"""
    accounts = SocialMediaAccount.objects.filter(
        user=request.user,
        platform=SocialMediaPlatform.TIKTOK,
        is_active=True
    )
    
    account_data = []
    for account in accounts:
        account_data.append({
            'id': str(account.id),
            'display_name': account.display_name,
            'username': account.username,
            'profile_image_url': account.profile_image_url,
            'followers_count': account.followers_count,
            'is_verified': account.is_verified,
            'connected_at': account.connected_at,
            'token_expired': account.is_token_expired
        })
    
    return Response({
        'accounts': account_data,
        'count': len(account_data)
    })


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def tiktok_disconnect(request: Request, account_id: str):
    """Disconnect TikTok account"""
    try:
        account = SocialMediaAccount.objects.get(
            id=account_id,
            user=request.user,
            platform=SocialMediaPlatform.TIKTOK
        )
        
        # Revoke token from TikTok
        service = TikTokService()
        service.revoke_token(account.access_token)
        
        # Deactivate account
        account.is_active = False
        account.save()
        
        return Response({
            'message': 'TikTok account disconnected successfully'
        })
        
    except SocialMediaAccount.DoesNotExist:
        return Response(
            {'error': 'TikTok account not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"TikTok disconnect failed: {e}")
        return Response(
            {'error': 'Failed to disconnect TikTok account'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def tiktok_create_post(request: Request):
    """Create a new TikTok post"""
    serializer = TikTokPostCreateSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Invalid data', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get TikTok account
    account_id = request.data.get('account_id')
    if not account_id:
        return Response(
            {'error': 'TikTok account ID is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        account = SocialMediaAccount.objects.get(
            id=account_id,
            user=request.user,
            platform=SocialMediaPlatform.TIKTOK,
            is_active=True
        )
    except SocialMediaAccount.DoesNotExist:
        return Response(
            {'error': 'TikTok account not found or not active'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if token is expired
    if account.is_token_expired:
        return Response(
            {'error': 'TikTok access token expired. Please reconnect your account.'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    try:
        # Save uploaded video file
        video_file = serializer.validated_data['video_file']
        video_path = default_storage.save(
            f'tiktok_videos/{request.user.id}/{video_file.name}',
            video_file
        )
        
        # Create TikTok post record
        tiktok_post = TikTokPost.objects.create(
            user=request.user,
            social_media_account=account,
            title=serializer.validated_data.get('title', ''),
            description=serializer.validated_data.get('description', ''),
            video_path=video_path,
            privacy_level=serializer.validated_data['privacy_level'],
            disable_duet=serializer.validated_data['disable_duet'],
            disable_comment=serializer.validated_data['disable_comment'],
            disable_stitch=serializer.validated_data['disable_stitch'],
            brand_content_toggle=serializer.validated_data['brand_content_toggle'],
            brand_organic_toggle=serializer.validated_data['brand_organic_toggle'],
            video_cover_timestamp_ms=serializer.validated_data['video_cover_timestamp_ms'],
            hashtags=serializer.validated_data.get('hashtags', []),
            mentions=serializer.validated_data.get('mentions', []),
            scheduled_at=serializer.validated_data.get('scheduled_at'),
            file_size_bytes=video_file.size,
            status=PostStatus.SCHEDULED if serializer.validated_data.get('scheduled_at') else PostStatus.DRAFT
        )
        
        # If not scheduled, post immediately
        if not tiktok_post.scheduled_at:
            try:
                # Upload and publish video
                service = TikTokService()
                video_file_path = default_storage.path(video_path)
                
                # Upload video
                upload_result = service.upload_video(account.access_token, video_file_path)
                tiktok_post.upload_id = upload_result.get('upload_id')
                tiktok_post.tiktok_video_id = upload_result.get('video_id')
                
                # Publish video
                post_info = {
                    'title': tiktok_post.title,
                    'privacy_level': tiktok_post.privacy_level,
                    'disable_duet': tiktok_post.disable_duet,
                    'disable_comment': tiktok_post.disable_comment,
                    'disable_stitch': tiktok_post.disable_stitch,
                    'video_cover_timestamp_ms': tiktok_post.video_cover_timestamp_ms,
                    'brand_content_toggle': tiktok_post.brand_content_toggle,
                    'brand_organic_toggle': tiktok_post.brand_organic_toggle,
                }
                
                publish_result = service.publish_video(
                    account.access_token, 
                    tiktok_post.tiktok_video_id, 
                    post_info
                )
                
                tiktok_post.publish_id = publish_result.get('publish_id')
                tiktok_post.status = PostStatus.PUBLISHED
                tiktok_post.published_at = timezone.now()
                
            except Exception as e:
                logger.error(f"TikTok post upload/publish failed: {e}")
                tiktok_post.status = PostStatus.FAILED
                tiktok_post.error_message = str(e)
        
        tiktok_post.save()
        
        # Return post data
        response_serializer = TikTokPostSerializer(tiktok_post)
        return Response({
            'message': 'TikTok post created successfully',
            'post': response_serializer.data
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"TikTok post creation failed: {e}")
        return Response(
            {'error': 'Failed to create TikTok post', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def tiktok_posts(request: Request):
    """Get user's TikTok posts"""
    account_id = request.query_params.get('account_id')
    
    queryset = TikTokPost.objects.filter(user=request.user)
    
    if account_id:
        queryset = queryset.filter(social_media_account_id=account_id)
    
    posts = queryset.order_by('-created_at')
    serializer = TikTokPostListSerializer(posts, many=True)
    
    return Response({
        'posts': serializer.data,
        'count': len(serializer.data)
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def tiktok_post_detail(request: Request, post_id: str):
    """Get TikTok post details"""
    try:
        post = TikTokPost.objects.get(id=post_id, user=request.user)
        serializer = TikTokPostSerializer(post)
        return Response(serializer.data)
    except TikTokPost.DoesNotExist:
        return Response(
            {'error': 'TikTok post not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def tiktok_delete_post(request: Request, post_id: str):
    """Delete TikTok post"""
    try:
        post = TikTokPost.objects.get(id=post_id, user=request.user)
        
        # Clean up video file
        if post.video_path and default_storage.exists(post.video_path):
            default_storage.delete(post.video_path)
        
        post.delete()
        
        return Response({
            'message': 'TikTok post deleted successfully'
        })
    except TikTokPost.DoesNotExist:
        return Response(
            {'error': 'TikTok post not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def tiktok_video_analytics(request: Request):
    """Get TikTok video analytics"""
    account_id = request.query_params.get('account_id')
    video_ids = request.query_params.getlist('video_ids')
    
    if not account_id:
        return Response(
            {'error': 'TikTok account ID is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        account = SocialMediaAccount.objects.get(
            id=account_id,
            user=request.user,
            platform=SocialMediaPlatform.TIKTOK,
            is_active=True
        )
        
        if account.is_token_expired:
            return Response(
                {'error': 'TikTok access token expired. Please reconnect your account.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        service = TikTokService()
        analytics_data = service.get_video_analytics(account.access_token, video_ids)
        
        return Response(analytics_data)
        
    except SocialMediaAccount.DoesNotExist:
        return Response(
            {'error': 'TikTok account not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"TikTok analytics request failed: {e}")
        return Response(
            {'error': 'Failed to get TikTok analytics'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
