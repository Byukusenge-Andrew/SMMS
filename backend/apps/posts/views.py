import logging
import uuid

from django.db import models
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta

from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Holiday, Post, PostSuggestion, PostTemplate, SocialSet
from .serializers import (
    HolidaySerializer,
    PostSerializer,
    PostSuggestionSerializer,
    PostTemplateSerializer,
    SocialSetSerializer,
)
from .tasks import generate_post_suggestions, publish_scheduled_post, bulk_post_operation

# Import for analytics
from apps.analytics.models import AnalyticsData

logger = logging.getLogger(__name__)


class PostListCreateView(ListCreateAPIView):
    """List posts or create a new post"""

    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Post.objects.filter(user=self.request.user)

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
            engagement_score=models.Avg("analytics__value", filter=models.Q(analytics__metric_type="engagement_rate"))
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
