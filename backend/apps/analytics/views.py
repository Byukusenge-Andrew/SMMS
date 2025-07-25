import logging
from datetime import timedelta

from django.db import models
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.integrations.ai_service import AIService

from .models import (AnalyticsData, BestPerformingPost, PerformanceReport,
                     PlatformAverage)
from .serializers import (BestPerformingPostSerializer,
                          PerformanceReportSerializer)
from .tasks import (analyze_comment_sentiment, collect_analytics_data,
                    generate_performance_report)

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
        heatmap_data = (
            location_data.values("country", "city")
            .annotate(
                total_engagement=models.Sum("value"),
                post_count=models.Count("post", distinct=True),
                avg_engagement=models.Avg("value"),
            )
            .order_by("-total_engagement")
        )

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
        top_reels = (
            AnalyticsData.objects.filter(
                user=user,
                platform=platform,
                date__gte=start_date,
                post__content_type__in=["video", "reel"],
                metric_type="views",
            )
            .select_related("post")
            .order_by("-value")[:10]
        )

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

        report = PerformanceReport.objects.filter(user=user, report_type="weekly", start_date=week_start).first()

        if not report:
            # Generate new report
            from .tasks import generate_performance_report

            report_id = generate_performance_report(user.id, "weekly")
            report = PerformanceReport.objects.get(id=report_id)

        serializer = PerformanceReportSerializer(report)
        return Response(serializer.data)

    except Exception as e:
        logger.error(f"Error getting weekly report: {str(e)}")
        return Response({"error": "Failed to get weekly report"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def monthly_report(request):
    """Get or generate monthly performance report"""
    try:
        user = request.user

        today = timezone.now().date()
        month_start = today.replace(day=1)

        report = PerformanceReport.objects.filter(user=user, report_type="monthly", start_date=month_start).first()

        if not report:
            from .tasks import generate_performance_report

            report_id = generate_performance_report(user.id, "monthly")
            report = PerformanceReport.objects.get(id=report_id)

        serializer = PerformanceReportSerializer(report)
        return Response(serializer.data)

    except Exception as e:
        logger.error(f"Error getting monthly report: {str(e)}")
        return Response({"error": "Failed to get monthly report"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def yearly_report(request):
    """Get or generate yearly performance report"""
    try:
        user = request.user

        today = timezone.now().date()
        year_start = today.replace(month=1, day=1)

        report = PerformanceReport.objects.filter(user=user, report_type="yearly", start_date=year_start).first()

        if not report:
            from .tasks import generate_performance_report

            report_id = generate_performance_report(user.id, "yearly")
            report = PerformanceReport.objects.get(id=report_id)

        serializer = PerformanceReportSerializer(report)
        return Response(serializer.data)

    except Exception as e:
        logger.error(f"Error getting yearly report: {str(e)}")
        return Response(
            {"error": "Failed to generate yearly report"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# AI-Powered Analytics Endpoints


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def ai_insights(request):
    """Get AI-powered insights based on analytics data"""
    try:
        user = request.user
        days = int(request.query_params.get("days", 30))
        platform = request.query_params.get("platform")

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        # Get analytics data
        analytics_query = AnalyticsData.objects.filter(user=user, date__gte=start_date, date__lte=end_date)

        if platform:
            analytics_query = analytics_query.filter(platform=platform)

        analytics_data = []
        for data in analytics_query:
            analytics_data.append(
                {
                    "date": data.date,
                    "platform": data.platform,
                    "metric_type": data.metric_type,
                    "value": data.value,
                    "engagement": data.value if data.metric_type == "engagement" else 0,
                    "reach": data.value if data.metric_type == "reach" else 0,
                    "impressions": data.value if data.metric_type == "impressions" else 0,
                    "content_type": getattr(data.post, "post_type", "post") if data.post else "post",
                    "hour": data.created_at.hour,
                }
            )

        # Get user context
        user_context = {
            "total_followers": sum(user.social_accounts.values_list("follower_count", flat=True)),
            "account_age_days": (timezone.now().date() - user.date_joined.date()).days,
            "platforms": list(user.social_accounts.values_list("platform", flat=True)),
        }

        # Generate AI insights
        ai_service = AIService()
        insights = ai_service.analyze_performance_data(analytics_data, user_context)

        return Response(
            {"ai_insights": insights, "data_period": f"{start_date} to {end_date}", "total_data_points": len(analytics_data)}
        )

    except Exception as e:
        logger.error(f"Error generating AI insights: {str(e)}")
        return Response({"error": "Failed to generate AI insights"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def ai_recommendations(request):
    """Get AI-powered content and strategy recommendations"""
    try:
        user = request.user
        platform = request.query_params.get("platform", "instagram")

        # Get recent analytics data for recommendations
        recent_data = AnalyticsData.objects.filter(user=user, date__gte=timezone.now().date() - timedelta(days=14))

        if platform:
            recent_data = recent_data.filter(platform=platform)

        analytics_data = []
        for data in recent_data:
            analytics_data.append(
                {
                    "date": data.date,
                    "platform": data.platform,
                    "metric_type": data.metric_type,
                    "value": data.value,
                    "engagement": data.value if data.metric_type == "engagement" else 0,
                    "reach": data.value if data.metric_type == "reach" else 0,
                    "impressions": data.value if data.metric_type == "impressions" else 0,
                    "content_type": getattr(data.post, "post_type", "post") if data.post else "post",
                    "hour": data.created_at.hour,
                }
            )

        ai_service = AIService()

        # Get performance analysis for recommendations
        performance_analysis = ai_service.analyze_performance_data(analytics_data)

        # Get content suggestions based on analytics
        content_suggestions = ai_service.generate_content_suggestions_based_on_analytics(analytics_data, platform)

        return Response(
            {
                "recommendations": performance_analysis.get("recommendations", []),
                "content_suggestions": content_suggestions,
                "optimization_tips": {
                    "posting_time": f"Best time to post: {performance_analysis.get('trends', {}).get('best_posting_hour', 12)}:00",
                    "engagement_trend": performance_analysis.get("trends", {}).get("engagement_trend", "stable"),
                    "performance_score": performance_analysis.get("summary", {}).get("performance_score", 0),
                },
                "platform": platform,
                "based_on_days": 14,
            }
        )

    except Exception as e:
        logger.error(f"Error generating AI recommendations: {str(e)}")
        return Response({"error": "Failed to generate AI recommendations"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def analyze_competitor(request):
    """Analyze competitor performance and provide insights"""
    try:
        competitor_data = request.data.get("competitor_data", {})
        user_platform = request.data.get("platform", "instagram")

        if not competitor_data:
            return Response({"error": "competitor_data is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Get user's data for comparison
        user_data = AnalyticsData.objects.filter(
            user=request.user, platform=user_platform, date__gte=timezone.now().date() - timedelta(days=30)
        )

        user_metrics = {
            "avg_engagement": user_data.filter(metric_type="engagement").aggregate(avg=models.Avg("value"))["avg"] or 0,
            "avg_reach": user_data.filter(metric_type="reach").aggregate(avg=models.Avg("value"))["avg"] or 0,
            "avg_impressions": user_data.filter(metric_type="impressions").aggregate(avg=models.Avg("value"))["avg"] or 0,
        }

        # Simple competitor analysis
        competitor_engagement = competitor_data.get("avg_engagement", 0)
        competitor_reach = competitor_data.get("avg_reach", 0)

        analysis = {
            "comparison": {
                "engagement_gap": competitor_engagement - user_metrics["avg_engagement"],
                "reach_gap": competitor_reach - user_metrics["avg_reach"],
                "performance_vs_competitor": "above" if user_metrics["avg_engagement"] > competitor_engagement else "below",
            },
            "insights": [],
            "action_items": [],
        }

        # Generate insights
        if competitor_engagement > user_metrics["avg_engagement"]:
            gap_percentage = (
                ((competitor_engagement - user_metrics["avg_engagement"]) / user_metrics["avg_engagement"]) * 100
                if user_metrics["avg_engagement"] > 0
                else 0
            )
            analysis["insights"].append(
                {
                    "type": "gap_analysis",
                    "message": f"Competitor has {gap_percentage:.1f}% higher engagement rate",
                    "priority": "high" if gap_percentage > 50 else "medium",
                }
            )
            analysis["action_items"].extend(
                [
                    "Analyze competitor's top-performing content",
                    "Identify content gaps in your strategy",
                    "Experiment with similar content formats",
                ]
            )

        if competitor_reach > user_metrics["avg_reach"]:
            analysis["insights"].append(
                {
                    "type": "reach_analysis",
                    "message": "Competitor has higher reach - consider hashtag and posting time optimization",
                    "priority": "medium",
                }
            )
            analysis["action_items"].extend(
                ["Optimize hashtag strategy", "Post at competitor's optimal times", "Increase posting frequency"]
            )

        return Response(
            {
                "competitor_analysis": analysis,
                "your_metrics": user_metrics,
                "competitor_metrics": competitor_data,
                "recommendations_generated": len(analysis["action_items"]),
            }
        )

    except Exception as e:
        logger.error(f"Error analyzing competitor: {str(e)}")
        return Response({"error": "Failed to analyze competitor data"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def predict_performance(request):
    """Predict content performance using AI"""
    try:
        content = request.query_params.get("content", "")
        platform = request.query_params.get("platform", "instagram")
        post_time = request.query_params.get("post_time", "12:00")

        if not content:
            return Response({"error": "content parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Get user's historical data for prediction
        user = request.user
        historical_data = AnalyticsData.objects.filter(
            user=user, platform=platform, date__gte=timezone.now().date() - timedelta(days=60)
        )

        # Calculate baseline metrics
        avg_engagement = historical_data.filter(metric_type="engagement").aggregate(avg=models.Avg("value"))["avg"] or 0
        avg_reach = historical_data.filter(metric_type="reach").aggregate(avg=models.Avg("value"))["avg"] or 0

        # Simple AI prediction based on content analysis
        ai_service = AIService()

        # Analyze content sentiment
        sentiment = ai_service.analyze_sentiment(content)

        # Generate hashtags
        hashtags = ai_service.generate_hashtags(content, platform)

        # Predict performance factors
        prediction_factors = {
            "sentiment_boost": (
                1.2 if sentiment["sentiment"] == "positive" else 0.8 if sentiment["sentiment"] == "negative" else 1.0
            ),
            "hashtag_boost": 1.1 if len(hashtags) >= 5 else 0.9,
            "length_factor": 1.0 if 50 <= len(content) <= 150 else 0.8,
            "time_factor": 1.2 if 9 <= int(post_time.split(":")[0]) <= 17 else 0.9,
        }

        # Calculate predicted metrics
        total_boost = (
            prediction_factors["sentiment_boost"]
            * prediction_factors["hashtag_boost"]
            * prediction_factors["length_factor"]
            * prediction_factors["time_factor"]
        )

        predicted_engagement = int(avg_engagement * total_boost)
        predicted_reach = int(avg_reach * total_boost)

        # Confidence score based on data availability
        data_points = historical_data.count()
        confidence = min(95, 30 + (data_points * 2))  # Max 95% confidence

        return Response(
            {
                "prediction": {
                    "predicted_engagement": predicted_engagement,
                    "predicted_reach": predicted_reach,
                    "confidence_score": confidence,
                    "performance_category": "high" if total_boost > 1.1 else "medium" if total_boost > 0.9 else "low",
                },
                "analysis": {
                    "content_sentiment": sentiment,
                    "suggested_hashtags": hashtags,
                    "content_length": len(content),
                    "optimal_length_range": "50-150 characters",
                },
                "factors": prediction_factors,
                "recommendations": [
                    "Add more positive language" if sentiment["sentiment"] != "positive" else "Great positive sentiment!",
                    f"Consider using these hashtags: {', '.join(hashtags[:5])}",
                    (
                        "Optimal post length achieved"
                        if 50 <= len(content) <= 150
                        else "Consider adjusting content length to 50-150 characters"
                    ),
                ],
            }
        )

    except Exception as e:
        logger.error(f"Error predicting performance: {str(e)}")
        return Response({"error": "Failed to predict performance"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({"error": "Failed to get yearly report"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
