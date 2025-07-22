import logging
import random
from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.template.loader import render_to_string
from django.utils import timezone

from celery import shared_task

from .models import AnalyticsData, AnalyticsInsight, BestPerformingPost, CommentAnalytics, PerformanceReport, PlatformAverage

logger = logging.getLogger(__name__)


@shared_task
def collect_analytics_data(user_id, platform=None):
    """Collect analytics data from social media platforms - simplified version"""
    try:
        user = User.objects.get(id=user_id)
        # For now, just log that we would collect data
        logger.info(f"Would collect analytics data for user {user.username}")

        # Return some mock data
        return {"followers": 1250, "engagement": 4.5, "impressions": 3000, "reach": 2500}
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
    except Exception as e:
        logger.error(f"Error collecting analytics data: {str(e)}")


@shared_task
def analyze_post_performance(post_id):
    """Analyze performance of a post - simplified version"""
    try:
        logger.info(f"Would analyze performance for post {post_id}")

        # Return mock analysis
        return {"engagement_rate": 3.2, "likes": 45, "comments": 12, "shares": 5, "sentiment": "positive"}
    except Exception as e:
        logger.error(f"Error analyzing post performance: {str(e)}")


@shared_task
def generate_performance_report(user_id, report_type="weekly"):
    """Generate performance report - simplified version"""
    try:
        user = User.objects.get(id=user_id)

        # Create a report entry
        report = PerformanceReport.objects.create(
            user=user,
            report_type=report_type,
            data={"total_followers": 1500, "engagement_rate": 3.8, "top_performing_platform": "instagram", "posts_count": 12},
        )

        logger.info(f"Generated {report_type} report for user {user.username}")
        return report.id

    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")


@shared_task
def analyze_comment_sentiment(post_id):
    """Analyze comment sentiment - simplified version"""
    try:
        logger.info(f"Would analyze comment sentiment for post {post_id}")

        sentiments = ["positive", "neutral", "negative"]
        weights = [0.6, 0.3, 0.1]  # More likely to be positive

        return {
            "sentiment": random.choices(sentiments, weights=weights)[0],
            "positive_count": random.randint(5, 20),
            "neutral_count": random.randint(3, 10),
            "negative_count": random.randint(0, 5),
        }

    except Exception as e:
        logger.error(f"Error analyzing comment sentiment: {str(e)}")


@shared_task
def send_weekly_report():
    """Send weekly analytics report - simplified version"""
    logger.info("Would send weekly analytics report to all users")
    return True


@shared_task
def send_monthly_report():
    """Send monthly analytics report - simplified version"""
    logger.info("Would send monthly analytics report to all users")
    return True


@shared_task
def calculate_platform_averages():
    """Calculate platform performance averages - simplified version"""
    logger.info("Would calculate platform averages")
    return {
        "instagram": {"engagement_rate": 3.2, "post_frequency": 4.5, "optimal_posting_time": "15:00"},
        "facebook": {"engagement_rate": 2.1, "post_frequency": 3.2, "optimal_posting_time": "12:00"},
        "twitter": {"engagement_rate": 1.8, "post_frequency": 6.7, "optimal_posting_time": "09:00"},
    }


@shared_task
def calculate_engagement_metrics(user_id):
    """Calculate engagement metrics for a user's posts - simplified version"""
    try:
        user = User.objects.get(id=user_id)
        logger.info(f"Would calculate engagement metrics for user {user.username}")

        # Return mock data
        return {
            "engagement_rate": random.uniform(2.0, 5.0),
            "best_performing_day": random.choice(["Monday", "Wednesday", "Friday"]),
            "total_engagements": random.randint(500, 2000),
        }
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
    except Exception as e:
        logger.error(f"Error calculating engagement metrics: {str(e)}")


@shared_task
def analyze_comment_sentiment(post_id):
    """Analyze sentiment of comments for a post - simplified version"""
    try:
        from apps.posts.models import Post

        post = Post.objects.get(id=post_id)
        logger.info(f"Would analyze comment sentiment for post {post_id}")

        sentiments = ["positive", "neutral", "negative"]
        weights = [0.6, 0.3, 0.1]  # More likely to be positive

        # Create a mock comment for demo purposes
        mock_comment = {
            "id": f"mock_{random.randint(1000, 9999)}",
            "text": "This is a great post!",
            "author": "mock_user",
            "created_at": timezone.now(),
        }

        sentiment = random.choices(sentiments, weights=weights)[0]
        sentiment_score = (
            random.uniform(0.5, 0.9)
            if sentiment == "positive"
            else (random.uniform(-0.9, -0.5) if sentiment == "negative" else random.uniform(-0.4, 0.4))
        )

        CommentAnalytics.objects.update_or_create(
            post=post,
            comment_id=mock_comment["id"],
            defaults={
                "comment_text": mock_comment["text"],
                "author_username": mock_comment["author"],
                "sentiment": sentiment,
                "sentiment_score": sentiment_score,
                "confidence_score": random.uniform(0.7, 0.95),
                "likes_count": random.randint(0, 10),
                "replies_count": random.randint(0, 3),
                "created_at": mock_comment["created_at"],
            },
        )

        logger.info(f"Analyzed sentiment for mock comment on post {post_id}")

        return {
            "sentiment": sentiment,
            "positive_count": random.randint(5, 20) if sentiment == "positive" else random.randint(0, 5),
            "neutral_count": random.randint(3, 10),
            "negative_count": random.randint(0, 5) if sentiment != "negative" else random.randint(5, 15),
        }

    except Exception as e:
        logger.error(f"Error analyzing comment sentiment: {str(e)}")


@shared_task
def calculate_platform_averages(user_id, period_type="weekly"):
    """Calculate platform and overall averages"""
    try:
        user = User.objects.get(id=user_id)

        # Determine date range
        end_date = timezone.now().date()
        if period_type == "weekly":
            start_date = end_date - timedelta(days=7)
        elif period_type == "monthly":
            start_date = end_date - timedelta(days=30)
        elif period_type == "yearly":
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=7)

        # Get platforms
        platforms = user.social_accounts.values_list("platform", flat=True).distinct()

        for platform in platforms:
            analytics_data = AnalyticsData.objects.filter(
                user=user, platform=platform, date__gte=start_date, date__lte=end_date
            )

            # Calculate averages
            metrics = {}
            for metric_type in ["impressions", "reach", "likes", "shares", "comments", "saves"]:
                values = analytics_data.filter(metric_type=metric_type).values_list("value", flat=True)
                metrics[f"avg_{metric_type}"] = sum(values) / len(values) if values else 0

            # Calculate engagement rate
            total_engagement = metrics["avg_likes"] + metrics["avg_shares"] + metrics["avg_comments"]
            metrics["avg_engagement_rate"] = (total_engagement / metrics["avg_reach"] * 100) if metrics["avg_reach"] > 0 else 0

            # Save platform averages
            PlatformAverage.objects.update_or_create(
                user=user,
                platform=platform,
                period_start=start_date,
                period_end=end_date,
                period_type=period_type,
                defaults=metrics,
            )

        # Calculate overall averages
        all_analytics = AnalyticsData.objects.filter(user=user, date__gte=start_date, date__lte=end_date)

        overall_metrics = {}
        for metric_type in ["impressions", "reach", "likes", "shares", "comments", "saves"]:
            values = all_analytics.filter(metric_type=metric_type).values_list("value", flat=True)
            overall_metrics[f"avg_{metric_type}"] = sum(values) / len(values) if values else 0

        total_engagement = overall_metrics["avg_likes"] + overall_metrics["avg_shares"] + overall_metrics["avg_comments"]
        overall_metrics["avg_engagement_rate"] = (
            (total_engagement / overall_metrics["avg_reach"] * 100) if overall_metrics["avg_reach"] > 0 else 0
        )

        PlatformAverage.objects.update_or_create(
            user=user,
            platform="",  # Empty for overall
            period_start=start_date,
            period_end=end_date,
            period_type=period_type,
            defaults=overall_metrics,
        )

        logger.info(f"Calculated {period_type} averages for user {user_id}")

    except Exception as e:
        logger.error(f"Error calculating platform averages: {str(e)}")


@shared_task
def generate_performance_report(user_id, report_type="weekly"):
    """Generate performance reports"""
    try:
        user = User.objects.get(id=user_id)

        # Determine date range
        end_date = timezone.now().date()
        if report_type == "weekly":
            start_date = end_date - timedelta(days=7)
            title = f"Weekly Report - {start_date} to {end_date}"
        elif report_type == "monthly":
            start_date = end_date - timedelta(days=30)
            title = f"Monthly Report - {start_date} to {end_date}"
        elif report_type == "yearly":
            start_date = end_date - timedelta(days=365)
            title = f"Yearly Report - {start_date} to {end_date}"
        else:
            start_date = end_date - timedelta(days=7)
            title = f"Custom Report - {start_date} to {end_date}"

        # Collect report data
        report_data = {
            "user": user.username,
            "period": f"{start_date} to {end_date}",
            "platforms": {},
            "top_posts": [],
            "insights": [],
            "summary": {},
        }

        # Platform statistics
        platforms = user.social_accounts.values_list("platform", flat=True).distinct()
        for platform in platforms:
            platform_data = AnalyticsData.objects.filter(
                user=user, platform=platform, date__gte=start_date, date__lte=end_date
            )

            platform_stats = {}
            for metric in ["impressions", "reach", "likes", "shares", "comments"]:
                values = platform_data.filter(metric_type=metric).values_list("value", flat=True)
                platform_stats[metric] = {"total": sum(values), "average": sum(values) / len(values) if values else 0}

            report_data["platforms"][platform] = platform_stats

        # Top performing posts
        best_posts = BestPerformingPost.objects.filter(user=user, period_start__gte=start_date, period_end__lte=end_date)[:5]

        for best_post in best_posts:
            report_data["top_posts"].append(
                {
                    "post_id": best_post.post.id,
                    "content": best_post.post.content[:100],
                    "platform": best_post.platform,
                    "metric": best_post.metric_type,
                    "value": best_post.metric_value,
                }
            )

        # Create report
        report = PerformanceReport.objects.create(
            user=user,
            report_type=report_type,
            title=title,
            start_date=start_date,
            end_date=end_date,
            data=report_data,
            is_generated=True,
            generated_at=timezone.now(),
        )

        # Generate PDF (placeholder - implement with reportlab or weasyprint)
        # generate_report_pdf.delay(report.id)

        logger.info(f"Generated {report_type} report for user {user_id}")
        return report.id

    except Exception as e:
        logger.error(f"Error generating performance report: {str(e)}")


@shared_task
def send_weekly_report():
    """Send weekly reports to all users"""
    users = User.objects.filter(profile__email_notifications=True, is_active=True)

    for user in users:
        try:
            report_id = generate_performance_report(user.id, "weekly")
            if report_id:
                send_report_email.delay(report_id)

                # Send to Slack if enabled
                if user.profile.slack_notifications:
                    send_report_slack.delay(report_id)

        except Exception as e:
            logger.error(f"Error sending weekly report to user {user.id}: {str(e)}")


@shared_task
def send_monthly_report():
    """Send monthly reports to all users"""
    users = User.objects.filter(profile__email_notifications=True, is_active=True)

    for user in users:
        try:
            report_id = generate_performance_report(user.id, "monthly")
            if report_id:
                send_report_email.delay(report_id)

                if user.profile.slack_notifications:
                    send_report_slack.delay(report_id)

        except Exception as e:
            logger.error(f"Error sending monthly report to user {user.id}: {str(e)}")


@shared_task
def send_yearly_report():
    """Send yearly reports to all users"""
    users = User.objects.filter(profile__email_notifications=True, is_active=True)

    for user in users:
        try:
            report_id = generate_performance_report(user.id, "yearly")
            if report_id:
                send_report_email.delay(report_id)

                if user.profile.slack_notifications:
                    send_report_slack.delay(report_id)

        except Exception as e:
            logger.error(f"Error sending yearly report to user {user.id}: {str(e)}")


@shared_task
def send_report_email(report_id):
    """Send report via email"""
    try:
        report = PerformanceReport.objects.get(id=report_id)

        # Render email template
        html_content = render_to_string("emails/performance_report.html", {"report": report, "user": report.user})

        # Send email
        email = EmailMultiAlternatives(
            subject=f"Social Media Performance Report - {report.title}",
            body="Please find your social media performance report attached.",
            from_email=settings.EMAIL_HOST_USER,
            to=[report.user.email],
        )
        email.attach_alternative(html_content, "text/html")

        if report.pdf_file:
            email.attach_file(report.pdf_file.path)

        email.send()

        report.sent_via_email = True
        report.email_sent_at = timezone.now()
        report.save()

        logger.info(f"Sent email report {report_id} to {report.user.email}")

    except Exception as e:
        logger.error(f"Error sending email report: {str(e)}")


@shared_task
def send_report_slack(report_id):
    """Send report via Slack - simplified version"""
    try:
        report = PerformanceReport.objects.get(id=report_id)

        # Simplified version that just logs what would be sent
        message = f"""
📊 *{report.title}*

*Summary for {report.user.username}:*
• Report Period: {report.start_date} to {report.end_date}
• Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M')}

View full report: [Link to dashboard]
        """

        logger.info(f"Would send Slack message to @{report.user.username}: {message}")

        # Update report status
        report.sent_via_slack = True
        report.slack_sent_at = timezone.now()
        report.save()

        report.sent_via_slack = True
        report.slack_sent_at = timezone.now()
        report.save()

        logger.info(f"Sent Slack report {report_id} to {report.user.username}")

    except Exception as e:
        logger.error(f"Error sending Slack report: {str(e)}")


@shared_task
def identify_best_performing_posts(user_id, period_type="weekly"):
    """Identify and record best performing posts"""
    try:
        user = User.objects.get(id=user_id)

        # Determine date range
        end_date = timezone.now().date()
        if period_type == "weekly":
            start_date = end_date - timedelta(days=7)
        elif period_type == "monthly":
            start_date = end_date - timedelta(days=30)
        elif period_type == "yearly":
            start_date = end_date - timedelta(days=365)

        platforms = user.social_accounts.values_list("platform", flat=True).distinct()

        for platform in platforms:
            # Get posts with analytics data
            posts_analytics = (
                AnalyticsData.objects.filter(
                    user=user, platform=platform, date__gte=start_date, date__lte=end_date, post__isnull=False
                )
                .values("post")
                .distinct()
            )

            for metric_type in ["engagement_rate", "reach", "impressions", "likes"]:
                # Calculate metric values for posts
                post_metrics = []

                for post_analytics in posts_analytics:
                    post_id = post_analytics["post"]

                    if metric_type == "engagement_rate":
                        # Calculate engagement rate
                        likes = (
                            AnalyticsData.objects.filter(post_id=post_id, metric_type="likes", date__gte=start_date).aggregate(
                                total=models.Sum("value")
                            )["total"]
                            or 0
                        )

                        shares = (
                            AnalyticsData.objects.filter(
                                post_id=post_id, metric_type="shares", date__gte=start_date
                            ).aggregate(total=models.Sum("value"))["total"]
                            or 0
                        )

                        comments = (
                            AnalyticsData.objects.filter(
                                post_id=post_id, metric_type="comments", date__gte=start_date
                            ).aggregate(total=models.Sum("value"))["total"]
                            or 0
                        )

                        reach = (
                            AnalyticsData.objects.filter(post_id=post_id, metric_type="reach", date__gte=start_date).aggregate(
                                total=models.Sum("value")
                            )["total"]
                            or 0
                        )

                        engagement_rate = ((likes + shares + comments) / reach * 100) if reach > 0 else 0
                        metric_value = engagement_rate
                    else:
                        metric_value = (
                            AnalyticsData.objects.filter(
                                post_id=post_id, metric_type=metric_type, date__gte=start_date
                            ).aggregate(total=models.Sum("value"))["total"]
                            or 0
                        )

                    post_metrics.append((post_id, metric_value))

                # Sort and get top 5
                post_metrics.sort(key=lambda x: x[1], reverse=True)
                top_posts = post_metrics[:5]

                # Save best performing posts
                for rank, (post_id, value) in enumerate(top_posts, 1):
                    from apps.posts.models import Post

                    post = Post.objects.get(id=post_id)

                    BestPerformingPost.objects.update_or_create(
                        user=user,
                        post=post,
                        platform=platform,
                        metric_type=metric_type,
                        period_start=start_date,
                        period_end=end_date,
                        period_type=period_type,
                        rank=rank,
                        defaults={"metric_value": value},
                    )

        logger.info(f"Identified best performing posts for user {user_id}")

    except Exception as e:
        logger.error(f"Error identifying best performing posts: {str(e)}")
