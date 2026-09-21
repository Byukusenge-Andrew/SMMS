"""
Celery tasks for Twitter/X integrations
"""
import logging
from datetime import datetime, timezone as dt_timezone
from celery import shared_task
from django.utils import timezone
from django.db import transaction

from .models import TwitterPost, PostStatus, ScheduledPostQueue
from .services.twitter_service import twitter_service

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def post_scheduled_tweet(self, twitter_post_id):
    """
    Post a scheduled tweet
    
    Args:
        twitter_post_id (str): UUID of the TwitterPost to publish
        
    Returns:
        dict: Result of the tweet posting operation
    """
    try:
        with transaction.atomic():
            twitter_post = TwitterPost.objects.select_for_update().get(
                id=twitter_post_id,
                status=PostStatus.SCHEDULED
            )
            
            # Double-check it's time to post
            if twitter_post.scheduled_at and twitter_post.scheduled_at > timezone.now():
                logger.warning(f"Tweet {twitter_post_id} is not ready to be posted yet")
                return {
                    'success': False,
                    'error': 'Tweet is not ready to be posted yet',
                    'retry': True
                }
            
            # Update status to publishing
            twitter_post.status = PostStatus.PUBLISHING
            twitter_post.save()
        
        # Post the tweet
        result = twitter_service.post_tweet(
            text=twitter_post.tweet_text,
            media_paths=twitter_post.media_paths or []
        )
        
        # Update the post with results
        with transaction.atomic():
            twitter_post.refresh_from_db()
            
            if result['success']:
                twitter_post.tweet_id = result['tweet_id']
                twitter_post.status = PostStatus.PUBLISHED
                twitter_post.published_at = timezone.now()
                twitter_post.error_message = None
                twitter_post.save()
                
                logger.info(f"Successfully posted scheduled tweet {twitter_post_id}: {result['tweet_id']}")
                
                return {
                    'success': True,
                    'tweet_id': result['tweet_id'],
                    'url': result['url'],
                    'posted_at': twitter_post.published_at.isoformat()
                }
            else:
                twitter_post.status = PostStatus.FAILED
                twitter_post.error_message = result['error']
                twitter_post.save()
                
                logger.error(f"Failed to post scheduled tweet {twitter_post_id}: {result['error']}")
                
                return {
                    'success': False,
                    'error': result['error'],
                    'retry': False
                }
                
    except TwitterPost.DoesNotExist:
        logger.error(f"TwitterPost {twitter_post_id} not found or not scheduled")
        return {
            'success': False,
            'error': 'Tweet not found or not scheduled',
            'retry': False
        }
    
    except Exception as exc:
        logger.error(f"Error posting scheduled tweet {twitter_post_id}: {exc}")
        
        # Update post status to failed if we can
        try:
            with transaction.atomic():
                twitter_post = TwitterPost.objects.get(id=twitter_post_id)
                twitter_post.status = PostStatus.FAILED
                twitter_post.error_message = str(exc)
                twitter_post.save()
        except Exception:
            pass
        
        # Retry the task if retries are available
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying scheduled tweet {twitter_post_id} (attempt {self.request.retries + 1})")
            raise self.retry(exc=exc)
        
        return {
            'success': False,
            'error': str(exc),
            'retry': False
        }


@shared_task
def process_scheduled_tweets():
    """
    Process all tweets that are scheduled to be posted now
    
    This task should be run every minute by Celery Beat
    """
    try:
        current_time = timezone.now()
        
        # Get tweets that are scheduled and ready to be posted
        scheduled_tweets = TwitterPost.objects.filter(
            status=PostStatus.SCHEDULED,
            scheduled_at__lte=current_time
        )
        
        logger.info(f"Found {scheduled_tweets.count()} tweets ready to be posted")
        
        results = []
        for tweet in scheduled_tweets:
            try:
                # Queue the tweet for posting
                task_result = post_scheduled_tweet.apply_async(
                    args=[str(tweet.id)],
                    countdown=0
                )
                
                results.append({
                    'tweet_id': str(tweet.id),
                    'task_id': task_result.id,
                    'scheduled_at': tweet.scheduled_at.isoformat()
                })
                
                logger.info(f"Queued scheduled tweet {tweet.id} for posting (task: {task_result.id})")
                
            except Exception as e:
                logger.error(f"Error queuing scheduled tweet {tweet.id}: {e}")
                
                # Mark as failed
                tweet.status = PostStatus.FAILED
                tweet.error_message = f"Failed to queue for posting: {str(e)}"
                tweet.save()
        
        return {
            'success': True,
            'processed_count': len(results),
            'tasks_queued': results
        }
        
    except Exception as e:
        logger.error(f"Error processing scheduled tweets: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def update_tweet_analytics(tweet_id):
    """
    Update analytics for a specific tweet
    
    Args:
        tweet_id (str): Twitter tweet ID
        
    Returns:
        dict: Result of the analytics update
    """
    try:
        # Get analytics from Twitter API
        result = twitter_service.get_tweet_analytics(tweet_id)
        
        if not result['success']:
            logger.error(f"Failed to get analytics for tweet {tweet_id}: {result['error']}")
            return {
                'success': False,
                'error': result['error']
            }
        
        # Update TwitterPost if it exists
        try:
            twitter_post = TwitterPost.objects.get(tweet_id=tweet_id)
            metrics = result['metrics']
            
            twitter_post.retweet_count = metrics['retweet_count']
            twitter_post.like_count = metrics['like_count']
            twitter_post.reply_count = metrics['reply_count']
            twitter_post.quote_count = metrics['quote_count']
            twitter_post.impression_count = metrics.get('impression_count', 0)
            twitter_post.last_analytics_update = timezone.now()
            twitter_post.save()
            
            logger.info(f"Updated analytics for tweet {tweet_id}")
            
            return {
                'success': True,
                'tweet_id': tweet_id,
                'metrics': metrics,
                'updated_at': twitter_post.last_analytics_update.isoformat()
            }
            
        except TwitterPost.DoesNotExist:
            logger.warning(f"TwitterPost not found for tweet_id {tweet_id}")
            return {
                'success': False,
                'error': 'TwitterPost not found in database',
                'twitter_metrics': result['metrics']
            }
    
    except Exception as e:
        logger.error(f"Error updating analytics for tweet {tweet_id}: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def bulk_update_tweet_analytics(user_id=None, hours_back=24):
    """
    Update analytics for multiple tweets
    
    Args:
        user_id (int): User ID to update tweets for (None for all users)
        hours_back (int): How many hours back to update analytics for
        
    Returns:
        dict: Summary of the analytics update operation
    """
    try:
        from django.contrib.auth.models import User
        from datetime import timedelta
        
        # Build queryset
        queryset = TwitterPost.objects.filter(
            status=PostStatus.PUBLISHED,
            tweet_id__isnull=False,
            published_at__gte=timezone.now() - timedelta(hours=hours_back)
        )
        
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        tweets = queryset[:100]  # Limit to prevent API rate limiting
        
        logger.info(f"Updating analytics for {tweets.count()} tweets")
        
        results = {
            'total_processed': 0,
            'successful_updates': 0,
            'failed_updates': 0,
            'errors': []
        }
        
        for tweet in tweets:
            try:
                # Queue individual analytics update
                task_result = update_tweet_analytics.apply_async(
                    args=[tweet.tweet_id],
                    countdown=2  # Small delay to respect rate limits
                )
                
                results['total_processed'] += 1
                logger.info(f"Queued analytics update for tweet {tweet.tweet_id} (task: {task_result.id})")
                
            except Exception as e:
                results['failed_updates'] += 1
                results['errors'].append({
                    'tweet_id': tweet.tweet_id,
                    'error': str(e)
                })
                logger.error(f"Error queuing analytics update for tweet {tweet.tweet_id}: {e}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error in bulk analytics update: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def cleanup_old_posts(days_old=30):
    """
    Clean up old posts and analytics data
    
    Args:
        days_old (int): Delete posts older than this many days
        
    Returns:
        dict: Summary of cleanup operation
    """
    try:
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=days_old)
        
        # Count posts to be deleted
        old_posts = TwitterPost.objects.filter(
            created_at__lt=cutoff_date,
            status__in=[PostStatus.DELETED, PostStatus.FAILED]
        )
        
        count = old_posts.count()
        
        if count > 0:
            # Delete old failed and deleted posts
            old_posts.delete()
            logger.info(f"Cleaned up {count} old Twitter posts")
        
        return {
            'success': True,
            'deleted_posts': count,
            'cutoff_date': cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up old posts: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def sync_twitter_profile(user_id):
    """
    Sync Twitter profile information for a user
    
    Args:
        user_id (int): User ID to sync profile for
        
    Returns:
        dict: Result of the profile sync
    """
    try:
        from django.contrib.auth.models import User
        from .models import SocialMediaAccount, SocialMediaPlatform
        
        user = User.objects.get(id=user_id)
        
        # Get user's profile from Twitter
        result = twitter_service.verify_credentials()
        
        if result['success']:
            # Update the account information
            account, created = SocialMediaAccount.objects.update_or_create(
                user=user,
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
                    'last_sync': timezone.now()
                }
            )
            
            logger.info(f"Synced Twitter profile for user {user_id}")
            
            return {
                'success': True,
                'user_id': user_id,
                'account_id': str(account.id),
                'created': created,
                'profile': {
                    'username': result['username'],
                    'name': result['name'],
                    'followers_count': result.get('followers_count', 0),
                    'verified': result.get('verified', False)
                }
            }
        else:
            logger.error(f"Failed to sync Twitter profile for user {user_id}: {result['error']}")
            return {
                'success': False,
                'error': result['error']
            }
            
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {
            'success': False,
            'error': 'User not found'
        }
    
    except Exception as e:
        logger.error(f"Error syncing Twitter profile for user {user_id}: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def refresh_expiring_social_tokens():
    """
    Proactively refresh social media OAuth tokens that expire within the next 48 hours.
    Prevents scheduled post failures due to expired credentials.
    """
    from datetime import timedelta
    import requests
    from django.conf import settings
    from .models import SocialMediaAccount, SocialMediaPlatform

    now = timezone.now()
    threshold = now + timedelta(hours=48)
    
    # Query active accounts with expiring tokens
    expiring_accounts = SocialMediaAccount.objects.filter(
        is_active=True,
        token_expires_at__lte=threshold
    )

    refreshed_count = 0
    failed_count = 0

    for account in expiring_accounts:
        try:
            if account.platform == SocialMediaPlatform.TWITTER:
                client_id = getattr(settings, 'TWITTER_CLIENT_ID', '')
                client_secret = getattr(settings, 'TWITTER_CLIENT_SECRET', '')
                if not client_id or not account.refresh_token:
                    continue

                token_url = "https://api.twitter.com/2/oauth2/token"
                data = {
                    'grant_type': 'refresh_token',
                    'refresh_token': account.refresh_token,
                    'client_id': client_id,
                }
                auth = (client_id, client_secret) if client_secret else None
                resp = requests.post(token_url, data=data, auth=auth, timeout=15)
                if resp.status_code == 200:
                    token_data = resp.json()
                    account.access_token = token_data.get('access_token', account.access_token)
                    if token_data.get('refresh_token'):
                        account.refresh_token = token_data['refresh_token']
                    expires_in = token_data.get('expires_in')
                    if expires_in:
                        account.set_token_expiry_from_expires_in(expires_in)
                    account.save(update_fields=['access_token', 'refresh_token', 'token_expires_at', 'last_updated'])
                    refreshed_count += 1
                    logger.info(f"Refreshed Twitter token for account {account.username} ({account.id})")
                else:
                    logger.warning(f"Failed to refresh Twitter token for {account.id}: {resp.text}")
                    failed_count += 1

            elif account.platform == SocialMediaPlatform.FACEBOOK:
                app_id = getattr(settings, 'FACEBOOK_APP_ID', '')
                app_secret = getattr(settings, 'FACEBOOK_APP_SECRET', '')
                if app_id and app_secret and account.access_token:
                    url = "https://graph.facebook.com/v18.0/oauth/access_token"
                    params = {
                        'grant_type': 'fb_exchange_token',
                        'client_id': app_id,
                        'client_secret': app_secret,
                        'fb_exchange_token': account.access_token,
                    }
                    resp = requests.get(url, params=params, timeout=15)
                    if resp.status_code == 200:
                        token_data = resp.json()
                        account.access_token = token_data.get('access_token', account.access_token)
                        expires_in = token_data.get('expires_in', 5184000)  # Default 60 days
                        account.set_token_expiry_from_expires_in(expires_in)
                        account.save(update_fields=['access_token', 'token_expires_at', 'last_updated'])
                        refreshed_count += 1
                        logger.info(f"Refreshed Facebook long-lived token for account {account.username} ({account.id})")
                    else:
                        failed_count += 1

        except Exception as e:
            logger.error(f"Exception refreshing token for account {account.id} ({account.platform}): {e}")
            failed_count += 1

    logger.info(f"Token refresh job completed. Refreshed: {refreshed_count}, Failed: {failed_count}")
    return {'refreshed': refreshed_count, 'failed': failed_count}

