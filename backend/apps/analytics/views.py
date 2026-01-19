import logging
from datetime import timedelta

from django.db import models
from django.utils import timezone

from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.integrations.ai_service import AIService
from .real_analytics_collector import RealAnalyticsCollector

from .models import AnalyticsData, BestPerformingPost, PerformanceReport, PlatformAverage
from .serializers import BestPerformingPostSerializer, PerformanceReportSerializer
from .tasks import analyze_comment_sentiment, collect_analytics_data, generate_performance_report

logger = logging.getLogger(__name__)


def get_user_social_accounts(user):
    """Get social accounts from both auth and integrations apps"""
    # Get accounts from both legacy (auth) and new (integrations) models
    auth_accounts = user.social_accounts.all()
    integrated_accounts = user.connected_social_accounts.all()
    
    # Combine platforms from both sources
    platforms = set()
    total_followers = 0
    
    for account in auth_accounts:
        platforms.add(account.platform)
        total_followers += account.follower_count or 0
    
    for account in integrated_accounts:
        platforms.add(account.platform)
        total_followers += account.followers_count or 0
    
    return {
        'platforms': list(platforms),
        'total_followers': total_followers,
        'auth_accounts': auth_accounts,
        'integrated_accounts': integrated_accounts
    }


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def analytics_dashboard(request):
    """Get analytics dashboard data with real metrics from connected accounts"""
    user = request.user
    
    # Initialize real analytics collector
    collector = RealAnalyticsCollector()
    
    # Check if we should refresh data (only if last update was >1 hour ago)
    should_refresh = request.GET.get('refresh', 'false').lower() == 'true'
    
    if should_refresh:
        try:
            # Collect fresh analytics data
            collection_results = collector.collect_all_user_analytics(user)
            logger.info(f"Analytics collection results for user {user.id}: {collection_results}")
        except Exception as e:
            logger.error(f"Error collecting analytics for user {user.id}: {e}")
    
    # Get recent analytics data (last 30 days)
    recent_data = AnalyticsData.objects.filter(
        user=user, 
        date__gte=timezone.now().date() - timedelta(days=30)
    )
    
    # Get social accounts from integrations app
    from apps.integrations.models import SocialMediaAccount
    connected_accounts = SocialMediaAccount.objects.filter(user=user, is_active=True)
    
    # Calculate real metrics
    total_followers = sum(account.followers_count or 0 for account in connected_accounts)
    total_following = sum(account.following_count or 0 for account in connected_accounts)
    connected_platforms = list(connected_accounts.values_list('platform', flat=True).distinct())
    
    # Platform breakdown with real data
    platform_stats = {}
    for platform in connected_platforms:
        platform_data = recent_data.filter(platform=platform)
        platform_account = connected_accounts.filter(platform=platform).first()
        
        # Get latest metrics for this platform
        latest_followers = platform_data.filter(metric_type="followers").order_by('-date').first()
        latest_engagement = platform_data.filter(metric_type="engagement").aggregate(
            total=models.Sum('value')
        )['total'] or 0
        
        platform_stats[platform] = {
            "followers": latest_followers.value if latest_followers else (platform_account.followers_count if platform_account else 0),
            "following": platform_account.following_count if platform_account else 0,
            "engagement": latest_engagement,
            "account_username": platform_account.username if platform_account else "",
            "account_verified": platform_account.is_verified if platform_account else False,
            "last_updated": platform_account.last_sync.isoformat() if platform_account and platform_account.last_sync else None
        }
    
    # Get growth trends (compare last 7 days vs previous 7 days)
    last_week = timezone.now().date() - timedelta(days=7)
    prev_week = timezone.now().date() - timedelta(days=14)
    
    current_week_followers = recent_data.filter(
        metric_type="followers", 
        date__gte=last_week
    ).aggregate(avg=models.Avg('value'))['avg'] or 0
    
    previous_week_followers = recent_data.filter(
        metric_type="followers", 
        date__gte=prev_week,
        date__lt=last_week
    ).aggregate(avg=models.Avg('value'))['avg'] or 0
    
    follower_growth = current_week_followers - previous_week_followers if previous_week_followers > 0 else 0
    growth_percentage = (follower_growth / previous_week_followers * 100) if previous_week_followers > 0 else 0

    return Response(
        {
            "platform_stats": platform_stats,
            "total_posts": user.posts.count(),
            "total_followers": total_followers,
            "total_following": total_following,
            "connected_platforms": connected_platforms,
            "growth_metrics": {
                "follower_growth": round(follower_growth, 0),
                "growth_percentage": round(growth_percentage, 2),
                "period": "7 days"
            },
            "last_updated": timezone.now().isoformat(),
            "accounts_count": connected_accounts.count()
        }
    )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def collect_analytics(request):
    """Trigger analytics collection for real data from connected accounts"""
    user = request.user
    platform = request.data.get("platform")  # Optional: collect for specific platform only
    
    try:
        collector = RealAnalyticsCollector()
        
        if platform:
            # Collect for specific platform
            from apps.integrations.models import SocialMediaAccount
            account = SocialMediaAccount.objects.filter(
                user=user, 
                platform=platform, 
                is_active=True
            ).first()
            
            if not account:
                return Response(
                    {"error": f"No active {platform} account found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            result = collector._collect_platform_analytics(account)
            
            if result['success']:
                collector._update_account_metrics(account, result['data'])
                return Response({
                    "message": f"Analytics collected for {platform}",
                    "data": result['data']
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "error": f"Failed to collect {platform} analytics",
                    "details": result['error']
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Collect for all connected accounts
            results = collector.collect_all_user_analytics(user)
            
            return Response({
                "message": "Analytics collection completed",
                "summary": results['summary'],
                "successful_platforms": len(results['success']),
                "failed_platforms": len(results['errors']),
                "details": {
                    "success": results['success'],
                    "errors": results['errors']
                }
            }, status=status.HTTP_200_OK)
            
    except Exception as e:
        logger.error(f"Error in analytics collection: {e}")
        return Response({
            "error": "Failed to collect analytics",
            "details": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def platform_insights(request):
    """Get detailed insights for specific platform or all platforms"""
    user = request.user
    platform = request.GET.get('platform')  # Optional: filter by platform
    days = int(request.GET.get('days', 30))  # Default to 30 days
    
    try:
        collector = RealAnalyticsCollector()
        insights = collector.get_platform_insights(user, platform=platform, days=days)
        
        # Add connected account info
        from apps.integrations.models import SocialMediaAccount
        connected_accounts = SocialMediaAccount.objects.filter(user=user, is_active=True)
        
        if platform:
            connected_accounts = connected_accounts.filter(platform=platform)
        
        account_info = {}
        for account in connected_accounts:
            account_info[account.platform] = {
                'username': account.username,
                'display_name': account.display_name,
                'followers_count': account.followers_count,
                'following_count': account.following_count,
                'is_verified': account.is_verified,
                'last_sync': account.last_sync.isoformat() if account.last_sync else None,
                'profile_image_url': account.profile_image_url
            }
        
        return Response({
            'insights': insights,
            'account_info': account_info,
            'period_days': days,
            'generated_at': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting platform insights: {e}")
        return Response({
            'error': 'Failed to get platform insights',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def analytics_overview(request):
    """Get comprehensive analytics overview with real data"""
    user = request.user
    
    try:
        # Get connected accounts
        from apps.integrations.models import SocialMediaAccount
        connected_accounts = SocialMediaAccount.objects.filter(user=user, is_active=True)
        
        if not connected_accounts.exists():
            return Response({
                'message': 'No connected social media accounts found',
                'suggestion': 'Connect your social media accounts to see analytics',
                'connected_accounts': 0,
                'available_platforms': ['twitter', 'linkedin', 'facebook', 'instagram']
            })
        
        # Calculate overview metrics
        total_followers = sum(account.followers_count or 0 for account in connected_accounts)
        total_following = sum(account.following_count or 0 for account in connected_accounts)
        
        # Get recent analytics data for trends
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        recent_analytics = AnalyticsData.objects.filter(
            user=user,
            date__gte=start_date
        )
        
        # Platform breakdown
        platform_breakdown = []
        for account in connected_accounts:
            platform_analytics = recent_analytics.filter(platform=account.platform)
            
            # Get latest engagement data
            engagement_data = platform_analytics.filter(
                metric_type__in=['likes', 'shares', 'comments', 'engagement']
            ).aggregate(
                total_engagement=models.Sum('value')
            )
            
            platform_breakdown.append({
                'platform': account.platform,
                'username': account.username,
                'display_name': account.display_name,
                'followers': account.followers_count or 0,
                'following': account.following_count or 0,
                'verified': account.is_verified,
                'total_engagement': engagement_data['total_engagement'] or 0,
                'last_synced': account.last_synced.isoformat() if account.last_synced else None
            })
        
        # Top performing platform (by followers)
        top_platform = max(platform_breakdown, key=lambda x: x['followers']) if platform_breakdown else None
        
        return Response({
            'overview': {
                'total_followers': total_followers,
                'total_following': total_following,
                'connected_platforms': len(platform_breakdown),
                'total_posts': user.posts.count(),
                'top_platform': top_platform['platform'] if top_platform else None
            },
            'platform_breakdown': platform_breakdown,
            'last_updated': timezone.now().isoformat(),
            'data_period': '30 days'
        })
        
    except Exception as e:
        logger.error(f"Error getting analytics overview: {e}")
        return Response({
            'error': 'Failed to get analytics overview',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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

        # Get user context using our helper function
        social_data = get_user_social_accounts(user)
        user_context = {
            "total_followers": social_data['total_followers'],
            "account_age_days": (timezone.now().date() - user.date_joined.date()).days,
            "platforms": social_data['platforms'],
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
