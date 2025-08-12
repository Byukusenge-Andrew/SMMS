import logging
import os

from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings

from celery import shared_task

from .models import Post
from apps.integrations.services.twitter_service import TwitterService
from apps.integrations.social_media_integrator import LinkedInIntegrator
from apps.authentication.models import SocialMediaAccount as AuthSocialMediaAccount
from apps.integrations.models import SocialMediaAccount as IntegratedAccount, SocialMediaPlatform

logger = logging.getLogger(__name__)


def publish_to_twitter_accounts(post, accounts, errors, source_type):
    """Helper function to publish to Twitter accounts"""
    success_count = 0
    
    for account in accounts:
        try:
            twitter_service = TwitterService()
            
            # Prepare media paths if there are attachments
            media_paths = []
            if post.image:
                media_path = post.image.path if hasattr(post.image, 'path') else None
                if media_path and os.path.exists(media_path):
                    media_paths.append(media_path)
                else:
                    # Try to handle Supabase storage
                    if hasattr(post.image, 'url') and post.image.url:
                        logger.info(f"Media stored in Supabase, URL: {post.image.url}")
                        media_paths = []
            
            if post.video:
                video_path = post.video.path if hasattr(post.video, 'path') else None
                if video_path and os.path.exists(video_path):
                    media_paths.append(video_path)
            
            # Post to Twitter
            result = twitter_service.post_tweet(
                text=post.content,
                media_paths=media_paths if media_paths else None,
                account=account
            )
            
            if result.get('success'):
                success_count += 1
                logger.info(f"Successfully posted to {source_type} Twitter account {account.id}: {result.get('tweet_id')}")
            else:
                error_msg = result.get('error', 'Unknown error')
                errors.append(f"{source_type} Twitter Account {account.id}: {error_msg}")
                logger.error(f"Failed to post to {source_type} Twitter account {account.id}: {error_msg}")
                
        except Exception as e:
            error_msg = f"{source_type} Twitter Account {account.id}: {str(e)}"
            errors.append(error_msg)
            logger.error(f"Error posting to {source_type} Twitter account {account.id}: {str(e)}")
    
    return success_count


def publish_to_linkedin_accounts(post, accounts, errors):
    """Helper function to publish to LinkedIn accounts"""
    success_count = 0
    
    for account in accounts:
        try:
            linkedin_integrator = LinkedInIntegrator()
            
            # Post to LinkedIn
            result = linkedin_integrator.publish_post(
                content=post.content,
                access_token=account.access_token
            )
            
            if result.get('success'):
                success_count += 1
                logger.info(f"Successfully posted to LinkedIn account {account.id}: {result.get('post_id')}")
            else:
                error_msg = result.get('error', 'Unknown error')
                errors.append(f"LinkedIn Account {account.id}: {error_msg}")
                logger.error(f"Failed to post to LinkedIn account {account.id}: {error_msg}")
                
        except Exception as e:
            error_msg = f"LinkedIn Account {account.id}: {str(e)}"
            errors.append(error_msg)
            logger.error(f"Error posting to LinkedIn account {account.id}: {str(e)}")
    
    return success_count


@shared_task
def publish_scheduled_post(post_id):
    """Publish a scheduled post to social media platforms"""
    try:
        post = Post.objects.get(id=post_id, status="scheduled")

        # Check if it's time to publish
        if post.scheduled_time > timezone.now():
            logger.info(f"Post {post_id} not ready for publishing yet")
            return

        logger.info(f"Publishing post {post_id} for user {post.user.id} ({post.user.username}) to platform: {post.platform}")

        # Get connected social media accounts for the specific platform chosen in the post
        success_count = 0
        errors = []
        
        # Normalize platform name for comparison
        platform_lower = post.platform.lower()
        
        if platform_lower in ['twitter', 'x', 'twitter/x']:
            # Handle Twitter posting
            # Check authentication app for legacy Twitter accounts
            auth_twitter_accounts = AuthSocialMediaAccount.objects.filter(
                user=post.user,
                platform__in=['twitter', 'Twitter/X', 'x'],
                is_active=True
            )
            
            # Check integrations app for newer Twitter accounts
            integrated_twitter_accounts = IntegratedAccount.objects.filter(
                user=post.user,
                platform=SocialMediaPlatform.TWITTER,
                is_active=True
            )
            
            logger.info(f"Found {auth_twitter_accounts.count()} Twitter accounts in auth app")
            logger.info(f"Found {integrated_twitter_accounts.count()} Twitter accounts in integrations app")
            
            # Post to Twitter accounts in auth app
            success_count += publish_to_twitter_accounts(post, auth_twitter_accounts, errors, "auth")
            
            # Post to Twitter accounts in integrations app
            success_count += publish_to_twitter_accounts(post, integrated_twitter_accounts, errors, "integrated")
            
        elif platform_lower == 'linkedin':
            # Handle LinkedIn posting
            integrated_linkedin_accounts = IntegratedAccount.objects.filter(
                user=post.user,
                platform=SocialMediaPlatform.LINKEDIN,
                is_active=True
            )
            
            logger.info(f"Found {integrated_linkedin_accounts.count()} LinkedIn accounts in integrations app")
            
            # Post to LinkedIn accounts
            success_count += publish_to_linkedin_accounts(post, integrated_linkedin_accounts, errors)
            
        else:
            error_msg = f"Unsupported platform: {post.platform}"
            logger.error(error_msg)
            errors.append(error_msg)

        # Check if we have any accounts to post to
        if success_count == 0 and not errors:
            logger.warning(f"No connected {post.platform} accounts found for user {post.user.id}")
            post.status = "failed"
            post.error_message = f"No connected {post.platform} accounts found"
            post.save()
            return

        # Update post status based on results
        if success_count > 0:
            post.status = "published"
            post.published_at = timezone.now()
            logger.info(f"Post {post_id} published successfully to {success_count} account(s)")
        else:
            post.status = "failed"
            logger.error(f"Post {post_id} failed to publish to any accounts. Errors: {'; '.join(errors)}")
        
        post.save()

    except Post.DoesNotExist:
        logger.error(f"Post {post_id} not found")
    except Exception as e:
        logger.error(f"Error publishing post {post_id}: {str(e)}")


@shared_task
def check_scheduled_posts():
    """Check for posts that need to be published"""
    current_time = timezone.now()
    scheduled_posts = Post.objects.filter(status="scheduled", scheduled_time__lte=current_time)

    for post in scheduled_posts:
        publish_scheduled_post.delay(post.id)

    logger.info(f"Queued {scheduled_posts.count()} posts for publishing")


@shared_task
def generate_post_suggestions(user_id, platform):
    """Generate simple post suggestions - simplified version"""
    try:
        # user = User.objects.get(id=user_id)

        # Simple hardcoded suggestions for now
        suggestions = [
            {"content": "Good morning! Have a great day!", "confidence": 0.8},
            {"content": "Excited to share updates with you all!", "confidence": 0.7},
            {"content": "What's everyone up to today?", "confidence": 0.6},
        ]

        logger.info(f"Generated {len(suggestions)} post suggestions for user {user_id}")
        return suggestions

    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
    except Exception as e:
        logger.error(f"Error generating post suggestions: {str(e)}")


@shared_task
def generate_hashtag_suggestions(user_id, content, platform):
    """Generate simple hashtag suggestions - simplified version"""
    try:
        user = User.objects.get(id=user_id)

        # Simple hashtag generation based on content words
        import re

        words = re.findall(r"\w+", content.lower())
        hashtags = [f"#{word}" for word in words[:3] if len(word) > 3]
        hashtags.extend(["#socialmedia", "#content", "#marketing"])

        logger.info(f"Generated hashtag suggestions for user {user_id}")
        return hashtags[:5]

    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
    except Exception as e:
        logger.error(f"Error generating hashtag suggestions: {str(e)}")


@shared_task
def cleanup_old_suggestions():
    """Clean up old post suggestions"""
    from datetime import timedelta

    cutoff_date = timezone.now() - timedelta(days=30)
    # This would clean up suggestions when we have that model
    logger.info("Cleanup task completed")


@shared_task
def bulk_post_operation(post_ids, action, user_id, **kwargs):
    """Perform bulk operations on posts"""
    try:
        user = User.objects.get(id=user_id)
        posts = Post.objects.filter(id__in=post_ids, user=user)

        if action == "publish":
            for post in posts:
                if post.status == "scheduled":
                    publish_scheduled_post.delay(post.id)

        elif action == "cancel":
            posts.update(status="cancelled")

        elif action == "reschedule":
            new_time = kwargs.get("scheduled_time")
            if new_time:
                posts.update(scheduled_time=new_time, status="scheduled")

        elif action == "delete":
            posts.delete()

        logger.info(f"Bulk {action} operation completed for {posts.count()} posts")

    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
    except Exception as e:
        logger.error(f"Error in bulk operation: {str(e)}")


@shared_task
def analyze_post_comments_sentiment_background(post_id, comments):
    """Background task to analyze post comments sentiment using AI"""
    try:
        # Get the post
        post = Post.objects.get(id=post_id)

        # Initialize AI service
        from apps.integrations.ai_service import AIService

        ai_service = AIService()

        # Analyze comments sentiment
        sentiment_analysis = ai_service.analyze_comments_sentiment(comments)

        # Add metadata
        sentiment_analysis["post_id"] = str(post.id)
        sentiment_analysis["analysis_timestamp"] = timezone.now().isoformat()
        sentiment_analysis["task_type"] = "background_analysis"

        # Here you could save results to a database model if needed
        # For now, just log the results
        logger.info(f"Background sentiment analysis completed for post {post_id}")
        logger.info(
            f"Results: {sentiment_analysis['overall_sentiment']} sentiment, "
            f"{sentiment_analysis['comments_analyzed']} comments analyzed"
        )

        return sentiment_analysis

    except Post.DoesNotExist:
        logger.error(f"Post {post_id} not found for sentiment analysis")
        return None
    except Exception as e:
        logger.error(f"Error in background sentiment analysis for post {post_id}: {str(e)}")
        return None


@shared_task
def analyze_user_posts_sentiment_trends(user_id, days=30):
    """Analyze sentiment trends across user's posts for the past N days"""
    try:
        from datetime import timedelta

        # Get user's recent posts
        cutoff_date = timezone.now() - timedelta(days=days)
        user_posts = Post.objects.filter(user_id=user_id, created_at__gte=cutoff_date, status__in=["published", "active"])

        if not user_posts.exists():
            logger.info(f"No recent posts found for user {user_id}")
            return {"message": "No recent posts to analyze"}

        # Initialize AI service
        from apps.integrations.ai_service import AIService

        ai_service = AIService()

        # This is a placeholder - in a real implementation, you'd need to:
        # 1. Fetch actual comments from social media APIs
        # 2. Store comment data in your database
        # 3. Analyze real comment sentiment

        # For now, we'll return a summary structure
        sentiment_trends = {
            "user_id": user_id,
            "analysis_period": f"{days} days",
            "posts_analyzed": user_posts.count(),
            "analysis_timestamp": timezone.now().isoformat(),
            "message": "Sentiment trends analysis framework ready - integrate with social media APIs for real data",
        }

        logger.info(f"Sentiment trends analysis completed for user {user_id}")
        return sentiment_trends

    except Exception as e:
        logger.error(f"Error analyzing sentiment trends for user {user_id}: {str(e)}")
        return None
