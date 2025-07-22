from celery import shared_task
from django.utils import timezone
from django.contrib.auth.models import User
from .models import Post
import logging

logger = logging.getLogger(__name__)


@shared_task
def publish_scheduled_post(post_id):
    """Publish a scheduled post - simplified version"""
    try:
        post = Post.objects.get(id=post_id, status="scheduled")

        # Check if it's time to publish
        if post.scheduled_time > timezone.now():
            logger.info(f"Post {post_id} not ready for publishing yet")
            return

        # For now, just mark as published (integration will be added later)
        post.status = "published"
        post.published_at = timezone.now()
        post.save()
        logger.info(f"Post {post_id} marked as published")

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
        user = User.objects.get(id=user_id)

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
