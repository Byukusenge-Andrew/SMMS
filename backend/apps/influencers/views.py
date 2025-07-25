import logging
from datetime import timedelta

from django.db import models
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.analytics.models import AnalyticsData  # Import from analytics app
from apps.posts.models import Post  # Import Post from posts app

# Fix imports - import from correct apps
from .models import Campaign, CampaignApplication, Influencer
from .serializers import (CampaignApplicationSerializer,
                          CampaignListSerializer, CampaignSerializer,
                          InfluencerAnalyticsSerializer,
                          InfluencerDashboardSerializer,
                          InfluencerImportSerializer, InfluencerListSerializer,
                          InfluencerSerializer)

logger = logging.getLogger(__name__)


class InfluencerProfileView(generics.RetrieveUpdateAPIView):
    """View for influencer profile management"""

    serializer_class = InfluencerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        influencer, created = Influencer.objects.get_or_create(
            user=self.request.user,
            defaults={
                "bio": "",
                "niche": "lifestyle",  # default niche
                "total_followers": 0,
                "avg_engagement_rate": 0.0,
            },
        )
        return influencer


class CampaignListCreateView(generics.ListCreateAPIView):
    """List campaigns or create new campaign"""

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return CampaignListSerializer
        return CampaignSerializer

    def get_queryset(self):
        return Campaign.objects.filter(creator=self.request.user)

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)


class CampaignDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete campaign"""

    serializer_class = CampaignSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Campaign.objects.filter(creator=self.request.user)


class CampaignApplicationListCreateView(generics.ListCreateAPIView):
    """List applications or apply to campaign"""

    serializer_class = CampaignApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CampaignApplication.objects.filter(influencer__user=self.request.user)

    def perform_create(self, serializer):
        influencer = get_object_or_404(Influencer, user=self.request.user)
        serializer.save(influencer=influencer)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def influencer_dashboard(request):
    """Get influencer dashboard data"""
    try:
        # Get or create influencer profile
        influencer, created = Influencer.objects.get_or_create(
            user=request.user,
            defaults={
                "bio": "",
                "niche": "lifestyle",
                "total_followers": 0,
                "avg_engagement_rate": 0.0,
            },
        )

        # Get campaign applications
        applications = CampaignApplication.objects.filter(influencer=influencer).select_related("campaign")

        # Get basic stats
        total_applications = applications.count()
        approved_applications = applications.filter(status="approved").count()
        pending_applications = applications.filter(status="pending").count()

        # Get recent campaigns
        recent_campaigns = Campaign.objects.filter(status="active").order_by("-created_at")[:5]

        dashboard_data = {
            "influencer_profile": InfluencerSerializer(influencer).data,
            "stats": {
                "total_applications": total_applications,
                "approved_applications": approved_applications,
                "pending_applications": pending_applications,
                "follower_count": influencer.total_followers,  # Fixed field name
                "engagement_rate": influencer.avg_engagement_rate,  # Fixed field name
            },
            "recent_applications": CampaignApplicationSerializer(applications.order_by("-applied_at")[:5], many=True).data,
            "available_campaigns": CampaignListSerializer(recent_campaigns, many=True).data,
        }

        return Response(dashboard_data)

    except Exception as e:
        logger.error(f"Error getting influencer dashboard: {str(e)}")
        return Response({"error": "Failed to load dashboard"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def import_influencers(request):
    """Import influencer database from various sources"""
    try:
        serializer = InfluencerImportSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        source = serializer.validated_data["source"]

        if source == "csv":
            csv_file = request.FILES.get("file")

            # Process CSV file
            import csv
            import io

            decoded_file = csv_file.read().decode("utf-8")
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)

            created_count = 0
            for row in reader:
                # Create a user first or use existing user
                from django.contrib.auth.models import User

                username = row.get("username", "")
                email = row.get("email", "")

                user, user_created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        "email": email,
                        "first_name": row.get("first_name", ""),
                        "last_name": row.get("last_name", ""),
                    },
                )

                influencer, created = Influencer.objects.get_or_create(
                    user=user,
                    defaults={
                        "bio": row.get("bio", ""),
                        "niche": row.get("niche", "lifestyle"),
                        "website": row.get("website", ""),
                        "total_followers": int(row.get("total_followers", 0)),
                        "avg_engagement_rate": float(row.get("avg_engagement_rate", 0.0)),
                        "post_rate": float(row.get("post_rate", 0)) if row.get("post_rate") else None,
                        "story_rate": float(row.get("story_rate", 0)) if row.get("story_rate") else None,
                        "reel_rate": float(row.get("reel_rate", 0)) if row.get("reel_rate") else None,
                    },
                )
                if created:
                    created_count += 1

            return Response(
                {"message": f"Imported {created_count} influencers from CSV", "source": "csv", "total_imported": created_count}
            )

        elif source == "manual":
            influencers_data = serializer.validated_data["influencers"]

            created_count = 0
            for influencer_data in influencers_data:
                from django.contrib.auth.models import User

                username = influencer_data.get("username")
                user, user_created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        "email": influencer_data.get("email", ""),
                        "first_name": influencer_data.get("first_name", ""),
                        "last_name": influencer_data.get("last_name", ""),
                    },
                )

                influencer, created = Influencer.objects.get_or_create(
                    user=user,
                    defaults={
                        "bio": influencer_data.get("bio", ""),
                        "niche": influencer_data.get("niche", "lifestyle"),
                        "website": influencer_data.get("website", ""),
                        "total_followers": influencer_data.get("total_followers", 0),
                        "avg_engagement_rate": influencer_data.get("avg_engagement_rate", 0.0),
                    },
                )
                if created:
                    created_count += 1

            return Response(
                {"message": f"Imported {created_count} influencers", "source": "manual", "total_imported": created_count}
            )

        return Response({"error": "Invalid source. Use 'csv' or 'manual'"}, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(f"Error importing influencers: {str(e)}")
        return Response({"error": "Failed to import influencers"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def influencer_analytics(request):
    """Get analytics for influencer interactions"""
    try:
        influencer_id = request.query_params.get("influencer_id")
        days = int(request.query_params.get("days", 30))

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        if influencer_id:
            # Analytics for specific influencer
            try:
                influencer = Influencer.objects.get(id=influencer_id, user=request.user)
            except Influencer.DoesNotExist:
                return Response({"error": "Influencer not found"}, status=status.HTTP_404_NOT_FOUND)

            # Get posts that mentioned this influencer
            mentioned_posts = Post.objects.filter(
                user=request.user,
                content__icontains=f"@{influencer.user.username}",  # Fixed: use user.username
                created_at__date__gte=start_date,
            )

            analytics_data = []
            for post in mentioned_posts:
                # Get analytics for this post if they exist
                try:
                    post_analytics = AnalyticsData.objects.filter(post=post, date__gte=start_date).aggregate(
                        total_likes=models.Sum("value", filter=models.Q(metric_type="likes")),
                        total_comments=models.Sum("value", filter=models.Q(metric_type="comments")),
                        total_shares=models.Sum("value", filter=models.Q(metric_type="shares")),
                    )
                except:
                    post_analytics = {"total_likes": 0, "total_comments": 0, "total_shares": 0}

                analytics_data.append(
                    {
                        "post_id": str(post.id),
                        "content": post.content[:100],
                        "analytics": post_analytics,
                        "created_at": post.created_at,
                    }
                )

            return Response(
                {
                    "influencer": {
                        "id": str(influencer.id),
                        "username": influencer.user.username,  # Fixed: use user.username
                        "niche": influencer.niche,
                        "total_followers": influencer.total_followers,
                    },
                    "mentioned_posts": analytics_data,
                    "summary": {"total_mentions": len(mentioned_posts), "date_range": f"{start_date} to {end_date}"},
                }
            )

        else:
            # Overall influencer analytics
            influencers = Influencer.objects.filter(user=request.user)

            analytics_summary = []
            for influencer in influencers:
                mention_count = Post.objects.filter(
                    user=request.user,
                    content__icontains=f"@{influencer.user.username}",  # Fixed: use user.username
                    created_at__date__gte=start_date,
                ).count()

                analytics_summary.append(
                    {
                        "influencer_id": str(influencer.id),
                        "username": influencer.user.username,  # Fixed: use user.username
                        "niche": influencer.niche,
                        "mention_count": mention_count,
                        "total_followers": influencer.total_followers,
                    }
                )

            return Response(
                {
                    "influencers_analytics": analytics_summary,
                    "date_range": f"{start_date} to {end_date}",
                    "total_influencers": len(analytics_summary),
                }
            )

    except Exception as e:
        logger.error(f"Error getting influencer analytics: {str(e)}")
        return Response({"error": "Failed to get influencer analytics"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
