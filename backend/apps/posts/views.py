import logging
import uuid
from datetime import timedelta

from django.db import models
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# Import for analytics
from apps.analytics.models import AnalyticsData

from .models import Holiday, Post, PostSuggestion, PostTemplate, SocialSet
from .serializers import (
    HolidaySerializer,
    PostSerializer,
    PostSuggestionSerializer,
    PostTemplateSerializer,
    SocialSetSerializer,
)
from .tasks import bulk_post_operation, generate_post_suggestions, publish_scheduled_post

logger = logging.getLogger(__name__)


class PostListCreateView(ListCreateAPIView):
    """List posts or create a new post"""

    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Post.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
        except Exception as e:
            msg = str(e)
            # Surface Supabase auth/policy failures clearly to the client
            if "signature verification failed" in msg or "Supabase" in msg:
                from django.conf import settings as dj_settings
                hint = (
                    "Storage upload failed. Ensure the backend uses a Supabase service role key (SUPABASE_SERVICE_ROLE_KEY) "
                    "or that your Storage bucket policies allow inserts for the provided key."
                )
                env_hint = {
                    "SUPABASE_URL_set": bool(getattr(dj_settings, "SUPABASE_URL", None)),
                    "SUPABASE_KEY_set": bool(getattr(dj_settings, "SUPABASE_KEY", None)),
                    "SUPABASE_SERVICE_ROLE_KEY_set": bool(getattr(dj_settings, "SUPABASE_SERVICE_ROLE_KEY", None)),
                    "SUPABASE_BUCKET": getattr(dj_settings, "SUPABASE_BUCKET", ""),
                }
                return Response(
                    {"error": "Media upload to storage failed: signature verification failed", "hint": hint, "env": env_hint},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            raise
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PostDetailView(RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a post"""

    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Post.objects.filter(user=self.request.user)


class PostTemplateListCreateView(ListCreateAPIView):
    """List templates or create a new template"""

    serializer_class = PostTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PostTemplate.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PostTemplateDetailView(RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a template"""

    serializer_class = PostTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PostTemplate.objects.filter(user=self.request.user)


class SocialSetListCreateView(ListCreateAPIView):
    """List social sets or create a new social set"""

    serializer_class = SocialSetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SocialSet.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SocialSetDetailView(RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a social set"""

    serializer_class = SocialSetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SocialSet.objects.filter(user=self.request.user)


class HolidayListView(ListCreateAPIView):
    """List holidays"""

    serializer_class = HolidaySerializer
    permission_classes = [IsAuthenticated]
    queryset = Holiday.objects.all()


class PostSuggestionListView(ListCreateAPIView):
    """List post suggestions"""

    serializer_class = PostSuggestionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PostSuggestion.objects.filter(user=self.request.user)


class ScheduledPostListCreateView(ListCreateAPIView):
    """List or create scheduled posts (uses Post model with scheduled_time)"""

    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Post.objects.filter(user=self.request.user)
        # Scheduled posts: future scheduled_time or status scheduled
        return qs.filter(models.Q(status="scheduled") | models.Q(scheduled_time__gt=timezone.now()))

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, status="scheduled")


class ScheduledPostDetailView(RetrieveUpdateDestroyAPIView):
    """Retrieve/update a scheduled post"""

    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Post.objects.filter(user=self.request.user)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def generate_suggestions(request):
    """Generate AI-powered suggestions"""
    niche = request.data.get("niche", "general")
    platform = request.data.get("platform", "instagram")
    count = request.data.get("count", 5)

    # Trigger async task
    generate_post_suggestions.delay(request.user.id, platform)

    return Response({"message": "Suggestions generation started"}, status=status.HTTP_202_ACCEPTED)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def bulk_post_actions(request):
    """Perform bulk actions on posts"""
    action = request.data.get("action")
    post_ids = request.data.get("post_ids", [])

    if not action or not post_ids:
        return Response({"error": "Action and post_ids are required"}, status=status.HTTP_400_BAD_REQUEST)

    posts = Post.objects.filter(id__in=post_ids, user=request.user)

    if action == "delete":
        count = posts.count()
        posts.delete()
        return Response({"message": f"Deleted {count} posts"})

    elif action == "publish":
        count = 0
        for post in posts:
            if post.status == "draft":
                post.status = "scheduled" if post.scheduled_time else "published"
                post.save()
                count += 1
        return Response({"message": f"Published {count} posts"})

    elif action == "schedule":
        scheduled_time = request.data.get("scheduled_time")
        if not scheduled_time:
            return Response({"error": "scheduled_time is required for schedule action"}, status=status.HTTP_400_BAD_REQUEST)

        count = posts.update(scheduled_time=scheduled_time, status="scheduled")
        return Response({"message": f"Scheduled {count} posts"})

    return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def calendar_view(request):
    """Get posts for calendar view"""
    user = request.user

    # Get date range from query params
    start_date = request.query_params.get("start_date")
    end_date = request.query_params.get("end_date")

    if start_date and end_date:
        posts = Post.objects.filter(user=user, scheduled_time__date__gte=start_date, scheduled_time__date__lte=end_date)
    else:
        # Default to current month
        now = timezone.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if now.month == 12:
            end_of_month = now.replace(year=now.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_of_month = now.replace(month=now.month + 1, day=1) - timedelta(days=1)

        posts = Post.objects.filter(user=user, scheduled_time__gte=start_of_month, scheduled_time__lte=end_of_month)

    # Format for calendar
    calendar_posts = []
    for post in posts:
        calendar_posts.append(
            {
                "id": str(post.id),
                "title": post.content[:50] + "..." if len(post.content) > 50 else post.content,
                "start": post.scheduled_time.isoformat() if post.scheduled_time else None,
                "platform": post.platform,
                "status": post.status,
                "color": {"draft": "#gray-500", "scheduled": "#blue-500", "published": "#green-500", "failed": "#red-500"}.get(
                    post.status, "#gray-500"
                ),
            }
        )

    return Response({"posts": calendar_posts})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def dashboard_stats(request):
    """Get dashboard statistics"""
    user = request.user
    now = timezone.now()

    # Get post statistics
    total_posts = Post.objects.filter(user=user).count()
    scheduled_posts = Post.objects.filter(user=user, status="scheduled").count()
    published_posts = Post.objects.filter(user=user, status="published").count()
    failed_posts = Post.objects.filter(user=user, status="failed").count()

    # Posts by platform
    platform_stats = {}
    platforms = Post.objects.filter(user=user).values_list("platform", flat=True).distinct()
    for platform in platforms:
        platform_stats[platform] = Post.objects.filter(user=user, platform=platform).count()

    # Recent activity
    recent_posts = Post.objects.filter(user=user, created_at__gte=now - timezone.timedelta(days=7)).count()

    return Response(
        {
            "total_posts": total_posts,
            "scheduled_posts": scheduled_posts,
            "published_posts": published_posts,
            "failed_posts": failed_posts,
            "platform_stats": platform_stats,
            "recent_posts": recent_posts,
            "social_sets_count": SocialSet.objects.filter(user=user).count(),
            "templates_count": PostTemplate.objects.filter(user=user).count(),
        }
    )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def share_calendar(request):
    """Share calendar via Slack or email"""
    try:
        share_type = request.data.get("type")  # 'slack' or 'email'
        recipients = request.data.get("recipients", [])
        date_range = request.data.get("date_range", 30)  # days

        user = request.user
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=date_range)

        # Get scheduled posts for the period
        posts = Post.objects.filter(
            user=user,
            scheduled_time__date__gte=start_date,
            scheduled_time__date__lte=end_date,
            status__in=["scheduled", "published"],
        ).order_by("scheduled_time")

        # Create calendar data
        calendar_data = []
        for post in posts:
            calendar_data.append(
                {
                    "id": str(post.id),
                    "title": post.content[:50] + "..." if len(post.content) > 50 else post.content,
                    "platform": post.platform,
                    "scheduled_time": post.scheduled_time,
                    "status": post.status,
                }
            )

        if share_type == "slack":
            from .tasks import share_calendar_slack

            share_calendar_slack.delay(user.id, calendar_data, recipients)

        elif share_type == "email":
            from .tasks import share_calendar_email

            share_calendar_email.delay(user.id, calendar_data, recipients)

        return Response(
            {
                "message": f"Calendar shared via {share_type}",
                "posts_count": len(calendar_data),
                "date_range": f"{start_date} to {end_date}",
            }
        )

    except Exception as e:
        logger.error(f"Error sharing calendar: {str(e)}")
        return Response({"error": "Failed to share calendar"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def multi_platform_post(request):
    """Post same content to multiple platforms"""
    try:
        platforms = request.data.get("platforms", [])
        content = request.data.get("content")
        media_urls = request.data.get("media_urls", [])
        scheduled_time = request.data.get("scheduled_time")
        location = request.data.get("location")
        tags = request.data.get("tags", [])

        if not platforms or not content:
            return Response({"error": "Platforms and content are required"}, status=status.HTTP_400_BAD_REQUEST)

        created_posts = []
        multi_platform_group_id = uuid.uuid4()  # Group related posts

        for platform in platforms:
            # Adapt content for platform-specific requirements
            adapted_content = adapt_content_for_platform(content, platform)
            adapted_media = adapt_media_for_platform(media_urls, platform)

            post = Post.objects.create(
                user=request.user,
                content=adapted_content,
                platform=platform,
                media_urls=adapted_media,
                scheduled_time=scheduled_time,
                location=location,
                tags=tags,
                status="scheduled" if scheduled_time else "draft",
                # Store multi-platform group ID in metadata or create separate field
            )

            created_posts.append(
                {
                    "id": str(post.id),
                    "platform": platform,
                    "content": adapted_content[:100] + "..." if len(adapted_content) > 100 else adapted_content,
                    "status": post.status,
                }
            )

            # Schedule for immediate publishing if no scheduled time
            if not scheduled_time:
                publish_scheduled_post.delay(post.id)

        return Response(
            {
                "message": f"Created posts for {len(platforms)} platforms",
                "posts": created_posts,
                "multi_platform_group_id": str(multi_platform_group_id),
            }
        )

    except Exception as e:
        logger.error(f"Error creating multi-platform post: {str(e)}")
        return Response({"error": "Failed to create multi-platform post"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def adapt_content_for_platform(content, platform):
    """Adapt content based on platform requirements"""
    if platform == "twitter" and len(content) > 280:
        return content[:276] + "..."
    elif platform == "instagram" and len(content) > 2200:
        return content[:2196] + "..."
    elif platform == "linkedin":
        # Add professional tone adaptations
        if not content.endswith("."):
            content += "."

    return content


def adapt_media_for_platform(media_urls, platform):
    """Adapt media based on platform requirements"""
    if platform == "twitter":
        # Twitter supports max 4 images or 1 video
        return media_urls[:4]
    elif platform == "instagram":
        # Instagram supports max 10 images/videos
        return media_urls[:10]
    elif platform == "linkedin":
        # LinkedIn supports max 1 image or video per post
        return media_urls[:1]

    return media_urls


@api_view(["GET"])
@permission_classes([permissions.AllowAny])  # Public endpoint
def brand_wall(request):
    """Get posts for brand wall display (social proof)"""
    try:
        hashtag = request.query_params.get("hashtag")
        tag = request.query_params.get("tag")
        platform = request.query_params.get("platform")
        limit = int(request.query_params.get("limit", 20))

        # Base query for published posts only
        posts = Post.objects.filter(
            status="published",
            # Only show posts marked as public - add this field to Post model if needed
        ).select_related("user")

        # Filter by hashtag
        if hashtag:
            posts = posts.filter(content__icontains=f"#{hashtag}")

        # Filter by tag
        if tag:
            posts = posts.filter(tags__contains=[tag])

        # Filter by platform
        if platform:
            posts = posts.filter(platform=platform)

        # Order by engagement and recent posts
        posts = posts.annotate(
            engagement_score=models.Avg("value", filter=models.Q(analytics__metric_type="engagement_rate"))
        ).order_by("-engagement_score", "-created_at")[:limit]

        brand_wall_data = []
        for post in posts:
            # Get analytics for the post
            analytics = AnalyticsData.objects.filter(post=post).aggregate(
                likes=models.Sum("value", filter=models.Q(metric_type="likes")),
                comments=models.Sum("value", filter=models.Q(metric_type="comments")),
                shares=models.Sum("value", filter=models.Q(metric_type="shares")),
            )

            brand_wall_data.append(
                {
                    "id": str(post.id),
                    "content": post.content,
                    "platform": post.platform,
                    "media_urls": post.media_urls,
                    "created_at": post.created_at,
                    "user": {
                        "username": post.user.username,
                        "profile_image": getattr(post.user.profile, "avatar", None) if hasattr(post.user, "profile") else None,
                    },
                    "analytics": analytics,
                    "hashtags": extract_hashtags(post.content),
                    "engagement_score": post.engagement_score or 0,
                }
            )

        return Response(
            {
                "posts": brand_wall_data,
                "total_count": len(brand_wall_data),
                "filters": {"hashtag": hashtag, "tag": tag, "platform": platform},
            }
        )

    except Exception as e:
        logger.error(f"Error getting brand wall: {str(e)}")
        return Response({"error": "Failed to get brand wall posts"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def extract_hashtags(content):
    """Extract hashtags from post content"""
    import re

    hashtag_pattern = r"#\w+"
    hashtags = re.findall(hashtag_pattern, content)
    return [tag.lower() for tag in hashtags]


# AI-Powered Content Suggestions


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def ai_content_suggestions(request):
    """Get AI-powered content suggestions based on analytics"""
    try:
        platform = request.query_params.get("platform", "instagram")

        # Get user's analytics data for better suggestions
        from apps.analytics.models import AnalyticsData

        recent_analytics = AnalyticsData.objects.filter(
            user=request.user, platform=platform, date__gte=timezone.now().date() - timedelta(days=30)
        )

        # Convert to AI service format
        analytics_data = []
        for data in recent_analytics:
            analytics_data.append(
                {
                    "date": data.date,
                    "platform": data.platform,
                    "engagement": data.value if data.metric_type == "engagement" else 0,
                    "reach": data.value if data.metric_type == "reach" else 0,
                    "content_type": getattr(data.post, "post_type", "post") if data.post else "post",
                }
            )

        # Generate AI suggestions
        from apps.integrations.ai_service import AIService

        ai_service = AIService()

        suggestions = ai_service.generate_content_suggestions_based_on_analytics(analytics_data, platform)

        # Also get general suggestions
        general_suggestions = ai_service.generate_post_suggestions(request.user, platform)

        return Response(
            {
                "analytics_based_suggestions": suggestions,
                "general_suggestions": general_suggestions,
                "platform": platform,
                "based_on_days": 30,
            }
        )

    except Exception as e:
        logger.error(f"Error generating AI content suggestions: {str(e)}")
        return Response({"error": "Failed to generate AI content suggestions"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def analyze_content_performance(request):
    """Analyze content performance and get suggestions"""
    try:
        content = request.data.get("content", "")
        platform = request.data.get("platform", "instagram")

        if not content:
            return Response({"error": "content is required"}, status=status.HTTP_400_BAD_REQUEST)

        from apps.integrations.ai_service import AIService

        ai_service = AIService()

        # Analyze content
        sentiment = ai_service.analyze_sentiment(content)
        hashtags = ai_service.generate_hashtags(content, platform)
        optimized_content = ai_service.optimize_content_for_platform(content, platform)

        # Get user's historical performance for comparison
        from apps.analytics.models import AnalyticsData

        user_avg_engagement = (
            AnalyticsData.objects.filter(user=request.user, platform=platform, metric_type="engagement").aggregate(
                avg=models.Avg("value")
            )["avg"]
            or 0
        )

        # Simple performance prediction
        sentiment_multiplier = 1.2 if sentiment["sentiment"] == "positive" else 0.8
        hashtag_boost = 1.1 if len(hashtags) >= 5 else 0.9
        length_factor = 1.0 if 50 <= len(content) <= 150 else 0.8

        predicted_engagement = int(user_avg_engagement * sentiment_multiplier * hashtag_boost * length_factor)

        return Response(
            {
                "content_analysis": {
                    "sentiment": sentiment,
                    "content_length": len(content),
                    "suggested_hashtags": hashtags,
                    "optimized_content": optimized_content,
                },
                "performance_prediction": {
                    "predicted_engagement": predicted_engagement,
                    "user_avg_engagement": user_avg_engagement,
                    "improvement_factors": {
                        "sentiment": sentiment_multiplier,
                        "hashtags": hashtag_boost,
                        "length": length_factor,
                    },
                },
                "recommendations": [
                    (
                        "Great positive sentiment!"
                        if sentiment["sentiment"] == "positive"
                        else "Consider adding more positive language"
                    ),
                    f"Suggested hashtags: {', '.join(hashtags[:5])}",
                    "Good content length" if 50 <= len(content) <= 150 else "Consider adjusting length to 50-150 characters",
                ],
            }
        )

    except Exception as e:
        logger.error(f"Error analyzing content: {str(e)}")
        return Response({"error": "Failed to analyze content"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_optimal_posting_times(request):
    """Get AI-suggested optimal posting times"""
    try:
        platform = request.query_params.get("platform")

        # Trigger AI analysis task
        from apps.analytics.tasks import predict_optimal_posting_times

        result = predict_optimal_posting_times.delay(request.user.id)

        # Get existing insights if available
        from apps.analytics.models import AnalyticsInsight

        recent_insights = AnalyticsInsight.objects.filter(
            user=request.user,
            insight_type="prediction",
            title="Optimal Posting Times",
            created_at__gte=timezone.now() - timedelta(days=7),
        ).first()

        if recent_insights:
            return Response(
                {
                    "optimal_times": recent_insights.data,
                    "generated_at": recent_insights.created_at,
                    "confidence": recent_insights.confidence_score,
                }
            )

        # Return default suggestions while analysis runs
        default_times = {"instagram": [9, 12, 15], "twitter": [9, 12, 18], "linkedin": [8, 12, 17], "facebook": [12, 15, 18]}

        platform_times = default_times.get(platform, [9, 12, 15])

        return Response(
            {
                "message": "AI analysis started, showing default optimal times",
                "optimal_times": [
                    {"hour": hour, "recommendation": f"Post at {hour}:00 for good engagement", "confidence": 0.6}
                    for hour in platform_times
                ],
                "task_id": result.id,
            }
        )

    except Exception as e:
        logger.error(f"Error getting optimal posting times: {str(e)}")
        return Response({"error": "Failed to get optimal posting times"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def trigger_ai_insights(request):
    """Trigger comprehensive AI insights generation"""
    try:
        days = int(request.data.get("days", 30))

        # Trigger various AI analysis tasks
        from apps.analytics.tasks import (
            analyze_content_performance_trends,
            generate_ai_insights,
            predict_optimal_posting_times,
        )

        # Start all AI analysis tasks
        insights_task = generate_ai_insights.delay(request.user.id, days)
        trends_task = analyze_content_performance_trends.delay(request.user.id)
        timing_task = predict_optimal_posting_times.delay(request.user.id)

        return Response(
            {
                "message": "AI insights generation started",
                "tasks": {"insights": insights_task.id, "trends": trends_task.id, "timing": timing_task.id},
                "analysis_period": f"{days} days",
                "estimated_completion": "2-3 minutes",
            }
        )

    except Exception as e:
        logger.error(f"Error triggering AI insights: {str(e)}")
        return Response({"error": "Failed to trigger AI insights"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def analyze_comment_sentiment(request, post_id):
    """Analyze sentiment of comments on a specific post using AI models"""
    try:
        # Get the post
        post = get_object_or_404(Post, id=post_id, user=request.user)

        # Get comments from request data
        comments = request.data.get("comments", [])

        if not comments:
            return Response({"error": "No comments provided for analysis"}, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(comments, list):
            return Response({"error": "Comments must be provided as a list"}, status=status.HTTP_400_BAD_REQUEST)

        # Initialize AI service
        from apps.integrations.ai_service import AIService

        ai_service = AIService()

        # Analyze comments sentiment
        sentiment_analysis = ai_service.analyze_comments_sentiment(comments)

        # Add post information to response
        sentiment_analysis["post_id"] = str(post.id)
        sentiment_analysis["post_title"] = post.title if hasattr(post, "title") else "Post"
        sentiment_analysis["analysis_timestamp"] = timezone.now().isoformat()

        # Log the analysis for potential future use
        logger.info(f"Sentiment analysis completed for post {post_id} by user {request.user.id}")

        return Response(sentiment_analysis)

    except Exception as e:
        logger.error(f"Error analyzing comment sentiment: {str(e)}")
        return Response(
            {"error": "Failed to analyze comment sentiment", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def analyze_single_comment_sentiment(request):
    """Analyze sentiment of a single comment using AI models"""
    try:
        comment_text = request.data.get("comment", "")

        if not comment_text or not comment_text.strip():
            return Response({"error": "Comment text is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Initialize AI service
        from apps.integrations.ai_service import AIService

        ai_service = AIService()

        # Analyze single comment sentiment
        sentiment_result = ai_service.analyze_sentiment(comment_text)

        # Add metadata
        sentiment_result["comment"] = comment_text[:200] + "..." if len(comment_text) > 200 else comment_text
        sentiment_result["analysis_timestamp"] = timezone.now().isoformat()

        return Response(sentiment_result)

    except Exception as e:
        logger.error(f"Error analyzing single comment sentiment: {str(e)}")
        return Response(
            {"error": "Failed to analyze comment sentiment", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def batch_analyze_post_comments(request):
    """Analyze sentiment for comments across multiple posts"""
    try:
        post_comments_data = request.data.get("posts", [])

        if not post_comments_data:
            return Response({"error": "Post comments data is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Initialize AI service
        from apps.integrations.ai_service import AIService

        ai_service = AIService()

        results = []
        overall_stats = {
            "total_posts": 0,
            "total_comments": 0,
            "overall_sentiment_distribution": {"positive": 0, "negative": 0, "neutral": 0},
        }

        for post_data in post_comments_data:
            post_id = post_data.get("post_id")
            comments = post_data.get("comments", [])

            if not post_id or not comments:
                continue

            # Verify post ownership
            try:
                post = get_object_or_404(Post, id=post_id, user=request.user)
            except Http404:
                continue

            # Analyze comments for this post
            sentiment_analysis = ai_service.analyze_comments_sentiment(comments)

            # Add post info
            sentiment_analysis["post_id"] = str(post_id)
            sentiment_analysis["post_title"] = post.title if hasattr(post, "title") else f"Post {post_id}"

            results.append(sentiment_analysis)

            # Update overall stats
            overall_stats["total_posts"] += 1
            overall_stats["total_comments"] += sentiment_analysis["comments_analyzed"]

            # Aggregate sentiment counts
            for sentiment, count in sentiment_analysis["sentiment_counts"].items():
                overall_stats["overall_sentiment_distribution"][sentiment] += count

        # Calculate overall percentages
        total_comments = overall_stats["total_comments"]
        if total_comments > 0:
            for sentiment in overall_stats["overall_sentiment_distribution"]:
                count = overall_stats["overall_sentiment_distribution"][sentiment]
                overall_stats["overall_sentiment_distribution"][sentiment] = {
                    "count": count,
                    "percentage": round((count / total_comments) * 100, 1),
                }

        return Response(
            {
                "results": results,
                "overall_stats": overall_stats,
                "analysis_timestamp": timezone.now().isoformat(),
                "posts_analyzed": len(results),
            }
        )

    except Exception as e:
        logger.error(f"Error in batch comment sentiment analysis: {str(e)}")
        return Response(
            {"error": "Failed to analyze comments sentiment", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
