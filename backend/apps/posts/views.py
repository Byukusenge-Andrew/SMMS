from django.db.models import Q
from django.utils import timezone

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Holiday, Post, PostSuggestion, PostTemplate, SocialSet
from .serializers import (
    BulkPostSerializer,
    HolidaySerializer,
    PostCreateSerializer,
    PostSerializer,
    PostSuggestionSerializer,
    PostTemplateSerializer,
    SocialSetSerializer,
)
from .tasks import bulk_post_operation, generate_hashtag_suggestions, generate_post_suggestions, publish_scheduled_post


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class PostListCreateView(ListCreateAPIView):
    serializer_class = PostSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["platform", "status", "post_type", "is_locked"]
    search_fields = ["content", "caption", "hashtags"]
    ordering_fields = ["scheduled_time", "created_at", "updated_at"]
    ordering = ["-scheduled_time"]

    def get_queryset(self):
        return Post.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return PostCreateSerializer
        return PostSerializer

    def perform_create(self, serializer):
        post = serializer.save()

        # Schedule the post for publishing
        if post.status == "scheduled":
            publish_scheduled_post.apply_async(args=[post.id], eta=post.scheduled_time)

        # Generate suggestions if requested
        if self.request.data.get("generate_suggestions"):
            generate_post_suggestions.delay(self.request.user.id, post.platform)


class PostDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = PostSerializer

    def get_queryset(self):
        return Post.objects.filter(user=self.request.user)

    def update(self, request, *args, **kwargs):
        post = self.get_object()

        # Check if post can be edited
        if not post.can_edit():
            return Response(
                {"error": "Post cannot be edited (locked or already published)"}, status=status.HTTP_400_BAD_REQUEST
            )

        return super().update(request, *args, **kwargs)


class PostTemplateListCreateView(ListCreateAPIView):
    serializer_class = PostTemplateSerializer

    def get_queryset(self):
        return PostTemplate.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PostTemplateDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = PostTemplateSerializer

    def get_queryset(self):
        return PostTemplate.objects.filter(user=self.request.user)


class SocialSetListCreateView(ListCreateAPIView):
    serializer_class = SocialSetSerializer

    def get_queryset(self):
        return SocialSet.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SocialSetDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = SocialSetSerializer

    def get_queryset(self):
        return SocialSet.objects.filter(user=self.request.user)


class HolidayListView(ListCreateAPIView):
    serializer_class = HolidaySerializer
    queryset = Holiday.objects.filter(is_active=True)
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["country", "category"]

    def get_queryset(self):
        queryset = super().get_queryset()
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)

        return queryset.order_by("date")


class PostSuggestionListView(ListCreateAPIView):
    serializer_class = PostSuggestionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["suggestion_type", "platform", "is_used"]

    def get_queryset(self):
        return PostSuggestion.objects.filter(user=self.request.user)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def generate_suggestions(request):
    """Generate AI-powered suggestions"""
    platform = request.data.get("platform")
    content = request.data.get("content", "")
    suggestion_type = request.data.get("type", "content")

    if not platform:
        return Response({"error": "Platform is required"}, status=status.HTTP_400_BAD_REQUEST)

    if suggestion_type == "content":
        generate_post_suggestions.delay(request.user.id, platform)
    elif suggestion_type == "hashtag" and content:
        generate_hashtag_suggestions.delay(request.user.id, content, platform)
    else:
        return Response({"error": "Invalid suggestion type or missing content"}, status=status.HTTP_400_BAD_REQUEST)

    return Response({"message": "Suggestions are being generated"}, status=status.HTTP_202_ACCEPTED)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def bulk_post_actions(request):
    """Perform bulk actions on posts"""
    serializer = BulkPostSerializer(data=request.data)
    if serializer.is_valid():
        post_ids = serializer.validated_data["post_ids"]
        action = serializer.validated_data["action"]

        # Verify user owns these posts
        user_posts = Post.objects.filter(id__in=post_ids, user=request.user).values_list("id", flat=True)

        if len(user_posts) != len(post_ids):
            return Response({"error": "Some posts not found or not owned by user"}, status=status.HTTP_400_BAD_REQUEST)

        # Execute bulk operation
        kwargs = {}
        if action == "reschedule":
            kwargs["scheduled_time"] = serializer.validated_data["scheduled_time"]

        bulk_post_operation.delay(post_ids, action, request.user.id, **kwargs)

        return Response({"message": f"Bulk {action} operation initiated"}, status=status.HTTP_202_ACCEPTED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def calendar_view(request):
    """Get posts for calendar view"""
    date_from = request.query_params.get("date_from")
    date_to = request.query_params.get("date_to")

    queryset = Post.objects.filter(user=request.user)

    if date_from:
        queryset = queryset.filter(scheduled_time__gte=date_from)
    if date_to:
        queryset = queryset.filter(scheduled_time__lte=date_to)

    posts = queryset.order_by("scheduled_time")

    # Group posts by date for calendar view
    calendar_data = {}
    for post in posts:
        date_key = post.scheduled_time.date().isoformat()
        if date_key not in calendar_data:
            calendar_data[date_key] = []
        calendar_data[date_key].append(PostSerializer(post).data)

    return Response(
        {
            "calendar_data": calendar_data,
            "holidays": HolidaySerializer(
                Holiday.objects.filter(date__gte=date_from, date__lte=date_to, is_active=True), many=True
            ).data,
        }
    )


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
