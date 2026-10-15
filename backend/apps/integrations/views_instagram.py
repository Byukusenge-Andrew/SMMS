import logging
from django.conf import settings
from django.http import JsonResponse
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from apps.authentication.models import SocialMediaAccount as AuthSocialMediaAccount
from apps.integrations.models import SocialMediaAccount, SocialMediaPlatform
from apps.influencers.models import Influencer

logger = logging.getLogger(__name__)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def instagram_connect(request):
    """
    Connect an Instagram account by handle/username or API token
    """
    try:
        data = request.data or {}
        raw_username = data.get('username', '').strip()
        if not raw_username:
            return JsonResponse({'success': False, 'error': 'Instagram username is required'}, status=400)
        
        # Clean username (remove leading @ and whitespace)
        username = raw_username.lstrip('@').strip()
        followers_count = int(data.get('followers_count', 0) or 0)
        display_name = data.get('display_name', '') or username
        profile_image_url = data.get('profile_image_url', '')
        
        # 1. Update or create in integrations.SocialMediaAccount
        account, created = SocialMediaAccount.objects.update_or_create(
            user=request.user,
            platform=SocialMediaPlatform.INSTAGRAM,
            platform_user_id=f"ig_{username}",
            defaults={
                'username': username,
                'display_name': display_name,
                'profile_image_url': profile_image_url,
                'followers_count': followers_count,
                'is_active': True,
                'is_verified': True,
                'access_token': data.get('access_token', 'connected_by_handle')
            }
        )
        
        # 2. Update or create in auth.SocialMediaAccount
        AuthSocialMediaAccount.objects.update_or_create(
            user=request.user,
            platform='instagram',
            defaults={
                'username': username,
                'access_token': data.get('access_token', 'connected_by_handle'),
                'is_active': True,
            }
        )
        
        # 3. If Influencer profile exists, sync total followers
        try:
            influencer = Influencer.objects.filter(user=request.user).first()
            if influencer:
                from django.db.models import Sum
                total = SocialMediaAccount.objects.filter(user=request.user, is_active=True).aggregate(t=Sum('followers_count'))['t'] or 0
                influencer.total_followers = total
                influencer.save(update_fields=['total_followers'])
        except Exception as e:
            logger.warning(f"Failed to update influencer total followers: {e}")
        
        return JsonResponse({
            'success': True,
            'message': f'Instagram account @{username} connected successfully',
            'account': {
                'id': str(account.id),
                'platform': 'instagram',
                'username': username,
                'display_name': display_name,
                'followers_count': followers_count,
                'is_active': True
            }
        })
    except Exception as e:
        logger.error(f"Error connecting Instagram account: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def instagram_verify(request):
    """
    Check if Instagram account is connected
    """
    try:
        account = SocialMediaAccount.objects.filter(
            user=request.user,
            platform=SocialMediaPlatform.INSTAGRAM,
            is_active=True
        ).first()
        
        if account:
            return JsonResponse({
                'success': True,
                'message': 'Instagram account is connected',
                'account': {
                    'id': str(account.id),
                    'platform': 'instagram',
                    'username': account.username,
                    'display_name': account.display_name,
                    'followers_count': account.followers_count,
                    'is_verified': account.is_verified,
                    'is_active': True
                }
            })
        return JsonResponse({
            'success': False,
            'message': 'No Instagram account connected'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def instagram_disconnect(request):
    """
    Disconnect Instagram account
    """
    try:
        SocialMediaAccount.objects.filter(
            user=request.user,
            platform=SocialMediaPlatform.INSTAGRAM
        ).update(is_active=False)
        
        AuthSocialMediaAccount.objects.filter(
            user=request.user,
            platform='instagram'
        ).update(is_active=False)
        
        return JsonResponse({
            'success': True,
            'message': 'Instagram account disconnected successfully'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
