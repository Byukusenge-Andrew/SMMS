from datetime import timedelta
import logging

from django.db import models
from django.utils import timezone

from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import AnalyticsData, BestPerformingPost, PerformanceReport, PlatformAverage
from .serializers import BestPerformingPostSerializer, PerformanceReportSerializer
from .tasks import analyze_comment_sentiment, collect_analytics_data, generate_performance_report

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def analytics_dashboard(request):
    """Get analytics dashboard data"""
    user = request.user

    # Get recent analytics data
    recent_data = AnalyticsData.objects.filter(user=user, date__gte=timezone.now().date() - timedelta(days=7))

    # Platform breakdown
    platform_stats = {}
    platforms = user.social_accounts.values_list("platform", flat=True).distinct()

    for platform in platforms:
        platform_data = recent_data.filter(platform=platform)
        platform_stats[platform] = {
            "impressions": sum(platform_data.filter(metric_type="impressions").values_list("value", flat=True)),
            "reach": sum(platform_data.filter(metric_type="reach").values_list("value", flat=True)),
            "engagement": sum(platform_data.filter(metric_type="engagement").values_list("value", flat=True)),
        }

    return Response(
        {
            "platform_stats": platform_stats,
            "total_posts": user.posts.count(),
            "total_followers": sum(user.social_accounts.values_list("follower_count", flat=True)),
        }
    )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def collect_analytics(request):
    """Trigger analytics collection"""
    platform = request.data.get("platform")
    collect_analytics_data.delay(request.user.id, platform)
    return Response({"message": "Analytics collection started"}, status=status.HTTP_202_ACCEPTED)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def comment_sentiment_analysis(request):
    """Analyze comment sentiment for a post"""
    post_id = request.data.get("post_id")
    if not post_id:
        return Response({"error": "post_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    analyze_comment_sentiment.delay(post_id)
    return Response({"message": "Sentiment analysis started"}, status=status.HTTP_202_ACCEPTED)


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def performance_reports(request):
    """Get or generate performance reports"""
    if request.method == "GET":
        reports = PerformanceReport.objects.filter(user=request.user)
        serializer = PerformanceReportSerializer(reports, many=True)
        return Response(serializer.data)

    elif request.method == "POST":
        report_type = request.data.get("type", "weekly")
        generate_performance_report.delay(request.user.id, report_type)
        return Response({"message": "Report generation started"}, status=status.HTTP_202_ACCEPTED)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def best_performing_posts(request):
    """Get best performing posts"""
    platform = request.query_params.get("platform")
    metric_type = request.query_params.get("metric", "engagement_rate")

    queryset = BestPerformingPost.objects.filter(user=request.user, metric_type=metric_type)
    if platform:
        queryset = queryset.filter(platform=platform)

    serializer = BestPerformingPostSerializer(queryset[:10], many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def platform_averages(request):
    """Get platform averages"""
    period_type = request.query_params.get("period", "weekly")

    averages = PlatformAverage.objects.filter(user=request.user, period_type=period_type).order_by("-calculated_at")[:10]

    data = []
    for avg in averages:
        data.append(
            {
                "platform": avg.platform or "Overall",
                "avg_impressions": avg.avg_impressions,
                "avg_reach": avg.avg_reach,
                "avg_engagement_rate": avg.avg_engagement_rate,
                "avg_likes": avg.avg_likes,
                "avg_shares": avg.avg_shares,
                "avg_comments": avg.avg_comments,
                "period": f"{avg.period_start} to {avg.period_end}",
            }
        )

    return Response(data)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def location_heatmap(request):
    """Get location-based analytics for heat map visualization"""
    try:
        user = request.user
        platform = request.query_params.get("platform")
        days = int(request.query_params.get("days", 30))

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        # Get location data from posts and analytics
        location_data = AnalyticsData.objects.filter(
            user=user,
            date__gte=start_date,
            date__lte=end_date,
            country__isnull=False,
        )

        if platform:
            location_data = location_data.filter(platform=platform)

        # Aggregate by location
        heatmap_data = location_data.values("country", "city").annotate(
            total_engagement=models.Sum("value"),
            post_count=models.Count("post", distinct=True),
            avg_engagement=models.Avg("value"),
        ).order_by("-total_engagement")

        return Response(
            {
                "heatmap_data": list(heatmap_data),
                "date_range": f"{start_date} to {end_date}",
                "total_locations": heatmap_data.count(),
            }
        )

    except Exception as e:
        logger.error(f"Error generating location heatmap: {str(e)}")
        return Response(
            {"error": "Failed to generate location heatmap"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def reels_analytics(request):
    """Get analytics specifically for reels/video content"""
    try:
        user = request.user
        platform = request.query_params.get("platform", "instagram")
        days = int(request.query_params.get("days", 30))

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        # Filter for video/reel content
        reels_data = AnalyticsData.objects.filter(
            user=user,
            platform=platform,
            date__gte=start_date,
            date__lte=end_date,
            post__content_type__in=["video", "reel"],
        ).aggregate(
            total_views=models.Sum("value", filter=models.Q(metric_type="views")),
            total_likes=models.Sum("value", filter=models.Q(metric_type="likes")),
            total_shares=models.Sum("value", filter=models.Q(metric_type="shares")),
            total_comments=models.Sum("value", filter=models.Q(metric_type="comments")),
            avg_watch_time=models.Avg("value", filter=models.Q(metric_type="watch_time")),
        )

        # Get top performing reels
        top_reels = AnalyticsData.objects.filter(
            user=user,
            platform=platform,
            date__gte=start_date,
            post__content_type__in=["video", "reel"],
            metric_type="views",
        ).select_related("post").order_by("-value")[:10]

        return Response(
            {
                "overview": reels_data,
                "top_reels": [
                    {
                        "post_id": str(reel.post.id),
                        "content": reel.post.content[:100],
                        "views": reel.value,
                        "created_at": reel.post.created_at,
                    }
                    for reel in top_reels
                ],
                "date_range": f"{start_date} to {end_date}",
            }
        )

    except Exception as e:
        logger.error(f"Error getting reels analytics: {str(e)}")
        return Response(
            {"error": "Failed to get reels analytics"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def weekly_report(request):
    """Get or generate weekly performance report"""
    try:
        user = request.user
        
        # Check if report exists for this week
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        
        report = PerformanceReport.objects.filter(
            user=user,
            report_type='weekly',
            start_date=week_start
        ).first()
        
        if not report:
            # Generate new report
            from .tasks import generate_performance_report
            report_id = generate_performance_report(user.id, 'weekly')
            report = PerformanceReport.objects.get(id=report_id)
        
        serializer = PerformanceReportSerializer(report)
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Error getting weekly report: {str(e)}")
        return Response(
            {"error": "Failed to get weekly report"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def monthly_report(request):
    """Get or generate monthly performance report"""
    try:
        user = request.user
        
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        report = PerformanceReport.objects.filter(
            user=user,
            report_type='monthly',
            start_date=month_start
        ).first()
        
        if not report:
            from .tasks import generate_performance_report
            report_id = generate_performance_report(user.id, 'monthly')
            report = PerformanceReport.objects.get(id=report_id)
        
        serializer = PerformanceReportSerializer(report)
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Error getting monthly report: {str(e)}")
        return Response(
            {"error": "Failed to get monthly report"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def yearly_report(request):
    """Get or generate yearly performance report"""
    try:
        user = request.user
        
        today = timezone.now().date()
        year_start = today.replace(month=1, day=1)
        
        report = PerformanceReport.objects.filter(
            user=user,
            report_type='yearly',
            start_date=year_start
        ).first()
        
        if not report:
            from .tasks import generate_performance_report
            report_id = generate_performance_report(user.id, 'yearly')
            report = PerformanceReport.objects.get(id=report_id)
        
        serializer = PerformanceReportSerializer(report)
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Error getting yearly report: {str(e)}")
        return Response(
            {"error": "Failed to get yearly report"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
