from datetime import timedelta

from django.utils import timezone

from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import AnalyticsData, BestPerformingPost, CommentAnalytics, PerformanceReport, PlatformAverage
from .serializers import AnalyticsDataSerializer, BestPerformingPostSerializer, PerformanceReportSerializer
from .tasks import analyze_comment_sentiment, collect_analytics_data, generate_performance_report


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
