"""
API views for rate limiting management and monitoring
"""

from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models.rate_limit_models import IPBlacklist, IPWhitelist, RateLimitLog, RateLimitStats
from .serializers import IPBlacklistSerializer, IPWhitelistSerializer, RateLimitLogSerializer, RateLimitStatsSerializer


class RateLimitDashboardView(APIView):
    """
    Dashboard view showing rate limiting statistics
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        """Get rate limiting dashboard data"""
        now = timezone.now()

        # Last 24 hours stats
        last_24h = now - timedelta(hours=24)
        recent_logs = RateLimitLog.objects.filter(timestamp__gte=last_24h)

        # Last 7 days stats
        last_7d = now - timedelta(days=7)
        weekly_logs = RateLimitLog.objects.filter(timestamp__gte=last_7d)

        # Current hour stats
        current_hour_start = now.replace(minute=0, second=0, microsecond=0)
        current_hour_logs = RateLimitLog.objects.filter(timestamp__gte=current_hour_start)

        dashboard_data = {
            "current_hour": {
                "total_requests": current_hour_logs.count(),
                "denied_requests": current_hour_logs.filter(action="denied").count(),
                "burst_protections": current_hour_logs.filter(action="burst_protection").count(),
                "unique_ips": current_hour_logs.values("ip_address").distinct().count(),
            },
            "last_24_hours": {
                "total_requests": recent_logs.count(),
                "denied_requests": recent_logs.filter(action="denied").count(),
                "burst_protections": recent_logs.filter(action="burst_protection").count(),
                "unique_ips": recent_logs.values("ip_address").distinct().count(),
                "by_user_type": {
                    "anonymous": recent_logs.filter(user_type="anonymous").count(),
                    "authenticated": recent_logs.filter(user_type="authenticated").count(),
                    "premium": recent_logs.filter(user_type="premium").count(),
                    "admin": recent_logs.filter(user_type="admin").count(),
                },
            },
            "last_7_days": {
                "total_requests": weekly_logs.count(),
                "denied_requests": weekly_logs.filter(action="denied").count(),
                "burst_protections": weekly_logs.filter(action="burst_protection").count(),
                "unique_ips": weekly_logs.values("ip_address").distinct().count(),
                "daily_breakdown": self._get_daily_breakdown(weekly_logs, last_7d),
            },
            "top_blocked_ips": self._get_top_blocked_ips(recent_logs),
            "active_rules": self._get_active_rules_count(),
        }

        return Response(dashboard_data)

    def _get_daily_breakdown(self, logs, start_date):
        """Get daily breakdown of requests"""
        daily_data = {}
        for i in range(7):
            day = start_date + timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)

            day_logs = logs.filter(timestamp__gte=day_start, timestamp__lt=day_end)
            daily_data[day.strftime("%Y-%m-%d")] = {
                "total": day_logs.count(),
                "denied": day_logs.filter(action="denied").count(),
                "burst_protection": day_logs.filter(action="burst_protection").count(),
            }

        return daily_data

    def _get_top_blocked_ips(self, logs):
        """Get top blocked IP addresses"""
        blocked_ips = (
            logs.filter(action__in=["denied", "burst_protection"])
            .values("ip_address")
            .annotate(blocked_count=Count("id"))
            .order_by("-blocked_count")[:10]
        )

        return list(blocked_ips)

    def _get_active_rules_count(self):
        """Get count of active rate limiting rules"""
        from .models import RateLimitRule

        return {
            "total": RateLimitRule.objects.filter(is_active=True).count(),
            "by_user_type": {
                "anonymous": RateLimitRule.objects.filter(user_type="anonymous", is_active=True).count(),
                "authenticated": RateLimitRule.objects.filter(user_type="authenticated", is_active=True).count(),
                "premium": RateLimitRule.objects.filter(user_type="premium", is_active=True).count(),
                "admin": RateLimitRule.objects.filter(user_type="admin", is_active=True).count(),
            },
        }


class RateLimitLogsView(APIView):
    """
    View for accessing rate limiting logs
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        """Get rate limiting logs with filtering"""
        logs = RateLimitLog.objects.all()

        # Apply filters
        action = request.query_params.get("action")
        if action:
            logs = logs.filter(action=action)

        user_type = request.query_params.get("user_type")
        if user_type:
            logs = logs.filter(user_type=user_type)

        ip_address = request.query_params.get("ip_address")
        if ip_address:
            logs = logs.filter(ip_address=ip_address)

        endpoint = request.query_params.get("endpoint")
        if endpoint:
            logs = logs.filter(endpoint__icontains=endpoint)

        # Time range filtering
        hours = request.query_params.get("hours", 24)
        try:
            hours = int(hours)
            since = timezone.now() - timedelta(hours=hours)
            logs = logs.filter(timestamp__gte=since)
        except ValueError:
            pass

        # Pagination
        page_size = min(int(request.query_params.get("page_size", 100)), 1000)
        page = int(request.query_params.get("page", 1))
        start = (page - 1) * page_size
        end = start + page_size

        total_count = logs.count()
        logs = logs.order_by("-timestamp")[start:end]

        serializer = RateLimitLogSerializer(logs, many=True)

        return Response({"count": total_count, "page": page, "page_size": page_size, "results": serializer.data})


class IPWhitelistView(APIView):
    """
    Manage IP whitelist
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        """Get whitelisted IPs"""
        whitelist = IPWhitelist.objects.filter(is_active=True)
        serializer = IPWhitelistSerializer(whitelist, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Add IP to whitelist"""
        serializer = IPWhitelistSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class IPBlacklistView(APIView):
    """
    Manage IP blacklist
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        """Get blacklisted IPs"""
        blacklist = IPBlacklist.objects.filter(is_active=True)
        serializer = IPBlacklistSerializer(blacklist, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Add IP to blacklist"""
        serializer = IPBlacklistSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RateLimitStatsView(APIView):
    """
    View rate limiting statistics
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        """Get aggregated statistics"""
        days = int(request.query_params.get("days", 7))
        start_date = timezone.now().date() - timedelta(days=days)

        stats = RateLimitStats.objects.filter(date__gte=start_date).order_by("date", "hour")

        serializer = RateLimitStatsSerializer(stats, many=True)
        return Response(serializer.data)


class RateLimitTestView(APIView):
    """
    Test endpoint for rate limiting
    """

    def get(self, request):
        """Simple test endpoint"""
        return Response(
            {
                "message": "Rate limiting test successful",
                "timestamp": timezone.now().isoformat(),
                "user_type": "authenticated" if request.user.is_authenticated else "anonymous",
                "user": str(request.user) if request.user.is_authenticated else None,
            }
        )

    def post(self, request):
        """Test endpoint for POST requests"""
        return Response({"message": "POST request successful", "data": request.data, "timestamp": timezone.now().isoformat()})
