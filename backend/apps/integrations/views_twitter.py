"""
Twitter/X API Views
"""
import logging
from datetime import datetime
from django.utils import timezone
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
        result = twitter_service.verify_credentials()
        
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
                'error': 'No active Twitter account found. Please verify your Twitter credentials first.'
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
            result = twitter_service.post_tweet(tweet_text, media_paths)
            
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
        
        result = twitter_service.get_user_tweets(count=count)
        
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
        result = twitter_service.get_tweet_analytics(tweet_id)
        
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
        
        result = twitter_service.search_tweets(query, count)
        
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
        result = twitter_service.delete_tweet(tweet_id)
        
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
        result = twitter_service.get_rate_limit_status()
        
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
