import logging
import os
import tempfile
from contextlib import contextmanager
import requests

from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from django.db import transaction

from celery import shared_task

from .models import Post
from apps.integrations.services.twitter_service import TwitterService
from apps.integrations.social_media_integrator import LinkedInIntegrator, FacebookIntegrator
from apps.authentication.models import SocialMediaAccount as AuthSocialMediaAccount
from apps.integrations.models import SocialMediaAccount as IntegratedAccount, SocialMediaPlatform

logger = logging.getLogger(__name__)


@contextmanager
def resolve_media_file(field_file):
    """
    Downloads remote cloud storage (e.g. Supabase) file to a local temp file for API upload.
    Yields local file path, and cleans up temporary file on exit.
    """
    if not field_file:
        yield None
        return

    # Check if local file exists (development fallback)
    try:
        if hasattr(field_file, 'path') and os.path.exists(field_file.path):
            yield field_file.path
            return
    except (AttributeError, NotImplementedError):
        pass

    # Remote cloud storage URL (Supabase)
    url = getattr(field_file, 'url', None)
    if not url:
        yield None
        return

    suffix = os.path.splitext(field_file.name)[-1] if hasattr(field_file, 'name') else '.tmp'
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name
            logger.info(f"Streaming remote media from {url} to temp file {tmp_path}")
            resp = requests.get(url, stream=True, timeout=60)
            resp.raise_for_status()
            for chunk in resp.iter_content(chunk_size=8192):
                tmp.write(chunk)

        yield tmp_path
    except Exception as e:
        logger.error(f"Failed to stream remote media from {url}: {e}")
        yield None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError as e:
                logger.warning(f"Could not remove temp media file {tmp_path}: {e}")


def publish_to_twitter_accounts(post, accounts, errors, source_type):
    """Helper function to publish to Twitter accounts with remote media support"""
    success_count = 0

    with resolve_media_file(post.image) as image_path, resolve_media_file(post.video) as video_path:
        media_paths = []
        if image_path:
            media_paths.append(image_path)
        if video_path:
            media_paths.append(video_path)

        for account in accounts:
            try:
                twitter_service = TwitterService()

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

    with resolve_media_file(post.image) as image_path:
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


def publish_to_facebook_accounts(post, accounts, errors):
    """Helper function to publish to Facebook accounts"""
    success_count = 0

    with resolve_media_file(post.image) as image_path:
        for account in accounts:
            try:
                facebook_integrator = FacebookIntegrator()

                credentials = {
                    'access_token': account.access_token
                }

                result = facebook_integrator.publish_post(
                    content=post.content,
                    credentials=credentials
                )

                if result.get('success'):
                    success_count += 1
                    logger.info(f"Successfully posted to Facebook account {account.id}: {result.get('post_id')}")
                else:
                    error_msg = result.get('error', 'Unknown error')
                    errors.append(f"Facebook Account {account.id}: {error_msg}")
                    logger.error(f"Failed to post to Facebook account {account.id}: {error_msg}")

            except Exception as e:
                error_msg = f"Facebook Account {account.id}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"Error posting to Facebook account {account.id}: {str(e)}")

    return success_count


def get_target_accounts_for_post(post, platform_name):
    """
    Resolve the exact social accounts targeted by this post.
    Prioritizes post.social_account, then post.social_set, and only falls back
    to user-wide accounts if no target was specified.
    """
    platform_lower = platform_name.lower()

    # 1. Post targets a specific account
    if post.social_account:
        acct = post.social_account
        if acct.platform.lower() in [platform_lower, 'twitter/x', 'x'] if platform_lower == 'twitter' else acct.platform.lower() == platform_lower:
            return [acct]
        return []

    # 2. Post targets a social set
    if post.social_set:
        return list(post.social_set.accounts.filter(
            platform__iexact=platform_lower,
            is_active=True
        ))

    # 3. Fallback to all connected accounts of that platform for this user
    logger.warning(f"Post {post.id} has no target account or social set specified; resolving all active {platform_name} accounts for user {post.user_id}")
    if platform_lower in ['twitter', 'x', 'twitter/x']:
        auth_accounts = list(AuthSocialMediaAccount.objects.filter(
            user=post.user,
            platform__in=['twitter', 'Twitter/X', 'x'],
            is_active=True
        ))
        integrated_accounts = list(IntegratedAccount.objects.filter(
            user=post.user,
            platform=SocialMediaPlatform.TWITTER,
            is_active=True
        ))
        return auth_accounts + integrated_accounts
    elif platform_lower == 'linkedin':
        return list(IntegratedAccount.objects.filter(
            user=post.user,
            platform=SocialMediaPlatform.LINKEDIN,
            is_active=True
        ))
    elif platform_lower == 'facebook':
        return list(IntegratedAccount.objects.filter(
            user=post.user,
            platform=SocialMediaPlatform.FACEBOOK,
            is_active=True
        ))
    return []


@shared_task
def publish_scheduled_post(post_id):
    """Publish a scheduled post to social media platforms with strict status check"""
    try:
        # Atomic fetch: only process if status is 'publishing' or 'scheduled'
        with transaction.atomic():
            post = Post.objects.select_for_update().filter(
                id=post_id,
                status__in=["scheduled", "publishing"]
            ).first()

            if not post:
                logger.info(f"Post {post_id} not found or already processed (status is not scheduled/publishing)")
                return

            if post.status == "scheduled":
                # Check if it's time to publish
                if post.scheduled_time > timezone.now():
                    logger.info(f"Post {post_id} not ready for publishing yet")
                    return
                post.status = "publishing"
                post.save(update_fields=['status'])

        logger.info(f"Publishing post {post_id} for user {post.user.id} ({post.user.username}) to platform: {post.platform}")

        success_count = 0
        errors = []
        platform_lower = post.platform.lower()

        target_accounts = get_target_accounts_for_post(post, post.platform)
        logger.info(f"Post {post_id} targeting {len(target_accounts)} account(s) for platform {post.platform}")

        if not target_accounts:
            post.status = "failed"
            post.error_message = f"No connected or matching {post.platform} accounts found for target"
            post.save(update_fields=['status', 'error_message'])
            return

        if platform_lower in ['twitter', 'x', 'twitter/x']:
            auth_accounts = [a for a in target_accounts if isinstance(a, AuthSocialMediaAccount)]
            integrated_accounts = [a for a in target_accounts if isinstance(a, IntegratedAccount)]

            if auth_accounts:
                success_count += publish_to_twitter_accounts(post, auth_accounts, errors, "auth")
            if integrated_accounts:
                success_count += publish_to_twitter_accounts(post, integrated_accounts, errors, "integrated")

        elif platform_lower == 'linkedin':
            success_count += publish_to_linkedin_accounts(post, target_accounts, errors)

        elif platform_lower == 'facebook':
            success_count += publish_to_facebook_accounts(post, target_accounts, errors)

        else:
            error_msg = f"Unsupported platform: {post.platform}"
            logger.error(error_msg)
            errors.append(error_msg)

        # Update post status based on results
        if success_count > 0:
            post.status = "published"
            post.published_at = timezone.now()
            post.error_message = ""
            post.save(update_fields=['status', 'published_at', 'error_message'])
            logger.info(f"Post {post_id} published successfully to {success_count} account(s)")

            # Trigger evergreen recycling if configured
            if post.is_evergreen:
                try:
                    recycled_post = post.recycle()
                    if recycled_post:
                        logger.info(
                            f"Recycled evergreen post {post_id} into new scheduled post {recycled_post.id} "
                            f"at {recycled_post.scheduled_time} (recycle #{recycled_post.recycle_count})"
                        )
                except Exception as recycle_err:
                    logger.error(f"Failed to recycle evergreen post {post_id}: {recycle_err}")
        else:
            post.status = "failed"
            post.error_message = f"Failed to publish: {'; '.join(errors)}"
            post.save(update_fields=['status', 'error_message'])
            logger.error(f"Post {post_id} failed to publish. Errors: {'; '.join(errors)}")

    except Post.DoesNotExist:
        logger.error(f"Post {post_id} not found")
    except Exception as e:
        logger.error(f"Error publishing post {post_id}: {str(e)}")
        try:
            Post.objects.filter(id=post_id).update(status="failed", error_message=str(e))
        except Exception:
            pass


@shared_task
def check_scheduled_posts():
    """
    Check for posts that need to be published.
    Uses atomic select_for_update(skip_locked=True) to prevent duplicate
    dispatch across concurrent or back-to-back Celery Beat runs.
    """
    current_time = timezone.now()
    with transaction.atomic():
        posts_to_process = list(
            Post.objects.select_for_update(skip_locked=True)
            .filter(status="scheduled", scheduled_time__lte=current_time)
            .values_list('id', flat=True)
        )
        if posts_to_process:
            Post.objects.filter(id__in=posts_to_process).update(status="publishing")

    for post_id in posts_to_process:
        publish_scheduled_post.delay(post_id)

    if posts_to_process:
        logger.info(f"Queued {len(posts_to_process)} posts for publishing")


@shared_task
def recycle_due_evergreen_posts():
    """
    Periodic safety worker to scan published evergreen posts whose recycling
    interval has elapsed and re-queue them if no active scheduled instance exists.
    """
    from datetime import timedelta
    from django.db.models import F, Q

    now = timezone.now()
    recycled_count = 0

    evergreen_posts = Post.objects.filter(
        status="published",
        is_evergreen=True
    ).exclude(
        Q(max_recycle_count__isnull=False) & Q(recycle_count__gte=F('max_recycle_count'))
    )

    for post in evergreen_posts:
        interval_days = post.recycle_interval_days or 30
        last_event = post.last_recycled_at or post.published_at
        if not last_event or (now - last_event) >= timedelta(days=interval_days):
            # Verify if there is already an upcoming scheduled instance
            root_post = post.original_post or post
            has_pending = Post.objects.filter(
                Q(id=root_post.id) | Q(original_post=root_post),
                status__in=["scheduled", "publishing"]
            ).exists()
            if not has_pending:
                try:
                    cloned = post.recycle()
                    if cloned:
                        recycled_count += 1
                        logger.info(f"Periodic worker recycled post {post.id} into {cloned.id}")
                except Exception as e:
                    logger.error(f"Error in periodic recycling for post {post.id}: {e}")

    logger.info(f"Completed evergreen recycling check: {recycled_count} post(s) recycled")
    return recycled_count


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
        from apps.integrations.ai_service import get_ai_service
        ai_service = get_ai_service()

        # Analyze comments sentiment, passing the user_id for usage logging
        sentiment_analysis = ai_service.analyze_comments_sentiment(comments, user_id=post.user_id)

        # Add metadata
        sentiment_analysis["post_id"] = str(post.id)
        sentiment_analysis["analysis_timestamp"] = timezone.now().isoformat()
        sentiment_analysis["task_type"] = "background_analysis"

        # Persist results to CommentAnalytics database model
        from apps.analytics.models import CommentAnalytics
        for i, result in enumerate(sentiment_analysis.get("individual_results", [])):
            CommentAnalytics.objects.update_or_create(
                post=post,
                comment_id=f"batch_{post_id}_{i}",
                defaults={
                    "comment_text": result["comment"],
                    "author_username": "unknown",
                    "sentiment": result["sentiment"],
                    "sentiment_score": result["scores"].get(result["sentiment"], 0.0),
                    "confidence_score": result["confidence"],
                    "created_at": timezone.now(),
                },
            )

        logger.info(f"Background sentiment analysis completed and saved for post {post_id}")
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

        # Query CommentAnalytics for the posts found
        from apps.analytics.models import CommentAnalytics
        comments_analytics = CommentAnalytics.objects.filter(post__in=user_posts)

        total_comments = comments_analytics.count()
        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
        
        for comment_item in comments_analytics:
            if comment_item.sentiment in sentiment_counts:
                sentiment_counts[comment_item.sentiment] += 1

        overall_sentiment = "neutral"
        if total_comments > 0:
            overall_sentiment = max(sentiment_counts.keys(), key=lambda k: sentiment_counts[k])

        sentiment_trends = {
            "user_id": user_id,
            "analysis_period": f"{days} days",
            "posts_analyzed": user_posts.count(),
            "comments_analyzed": total_comments,
            "overall_sentiment": overall_sentiment,
            "sentiment_counts": sentiment_counts,
            "sentiment_distribution": {
                k: round(v / total_comments * 100, 1) if total_comments > 0 else 0
                for k, v in sentiment_counts.items()
            },
            "analysis_timestamp": timezone.now().isoformat(),
        }

        logger.info(f"Sentiment trends analysis completed for user {user_id}")
        return sentiment_trends

    except Exception as e:
        logger.error(f"Error analyzing sentiment trends for user {user_id}: {str(e)}")
        return None
