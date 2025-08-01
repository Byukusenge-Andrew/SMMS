"""
Celery tasks for rate limiting maintenance and statistics
"""

import logging
from datetime import timedelta

from django.db.models import Avg, Count
from django.utils import timezone

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def cleanup_rate_limit_logs(days_to_keep=30):
    """
    Clean up old rate limiting logs
    Runs daily at 2 AM
    """
    from .models import RateLimitLog

    cutoff_date = timezone.now() - timedelta(days=days_to_keep)
    deleted_count = RateLimitLog.objects.filter(timestamp__lt=cutoff_date).delete()[0]

    logger.info(f"Cleaned up {deleted_count} rate limiting logs older than {days_to_keep} days")
    return {"deleted_count": deleted_count, "cutoff_date": cutoff_date.isoformat()}


@shared_task
def generate_hourly_stats():
    """
    Generate hourly statistics for rate limiting
    Runs every hour at 5 minutes past
    """
    from .models import RateLimitLog, RateLimitStats

    # Get the previous hour
    now = timezone.now()
    hour_start = (now - timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    hour_end = hour_start + timedelta(hours=1)

    # Get logs for the hour
    hour_logs = RateLimitLog.objects.filter(timestamp__gte=hour_start, timestamp__lt=hour_end)

    if not hour_logs.exists():
        return {"message": f'No logs for hour {hour_start.strftime("%Y-%m-%d %H:00")}'}

    # Calculate statistics
    total_requests = hour_logs.count()
    allowed_requests = hour_logs.filter(action="allowed").count()
    denied_requests = hour_logs.filter(action="denied").count()
    burst_protections = hour_logs.filter(action="burst_protection").count()

    # By user type
    anonymous_requests = hour_logs.filter(user_type="anonymous").count()
    authenticated_requests = hour_logs.filter(user_type="authenticated").count()
    premium_requests = hour_logs.filter(user_type="premium").count()
    admin_requests = hour_logs.filter(user_type="admin").count()

    # Performance metrics
    avg_tokens = hour_logs.aggregate(avg=Avg("tokens_remaining"))["avg"] or 0.0
    avg_requests = hour_logs.aggregate(avg=Avg("requests_remaining"))["avg"] or 0.0

    # Calculate peak requests per minute
    peak_requests = 0
    for minute in range(60):
        minute_start = hour_start + timedelta(minutes=minute)
        minute_end = minute_start + timedelta(minutes=1)
        minute_count = hour_logs.filter(timestamp__gte=minute_start, timestamp__lt=minute_end).count()
        peak_requests = max(peak_requests, minute_count)

    # Create or update stats record
    stats, created = RateLimitStats.objects.get_or_create(
        date=hour_start.date(),
        hour=hour_start.hour,
        defaults={
            "total_requests": total_requests,
            "allowed_requests": allowed_requests,
            "denied_requests": denied_requests,
            "burst_protections": burst_protections,
            "anonymous_requests": anonymous_requests,
            "authenticated_requests": authenticated_requests,
            "premium_requests": premium_requests,
            "admin_requests": admin_requests,
            "average_tokens_remaining": avg_tokens,
            "average_requests_remaining": avg_requests,
            "peak_requests_per_minute": peak_requests,
        },
    )

    if not created:
        # Update existing record
        stats.total_requests = total_requests
        stats.allowed_requests = allowed_requests
        stats.denied_requests = denied_requests
        stats.burst_protections = burst_protections
        stats.anonymous_requests = anonymous_requests
        stats.authenticated_requests = authenticated_requests
        stats.premium_requests = premium_requests
        stats.admin_requests = admin_requests
        stats.average_tokens_remaining = avg_tokens
        stats.average_requests_remaining = avg_requests
        stats.peak_requests_per_minute = peak_requests
        stats.save()

    action = "Created" if created else "Updated"
    logger.info(
        f'{action} rate limit stats for {hour_start.strftime("%Y-%m-%d %H:00")}: '
        f"{total_requests} requests, {denied_requests} denied"
    )

    return {
        "action": action,
        "hour": hour_start.strftime("%Y-%m-%d %H:00"),
        "total_requests": total_requests,
        "denied_requests": denied_requests,
        "denial_rate": round((denied_requests / total_requests) * 100, 2) if total_requests > 0 else 0,
    }


@shared_task
def check_expired_blacklist_entries():
    """
    Check for expired blacklist entries and deactivate them
    Runs every hour
    """
    from .models import IPBlacklist

    now = timezone.now()
    expired_entries = IPBlacklist.objects.filter(is_active=True, expires_at__lte=now)

    count = expired_entries.count()
    if count > 0:
        expired_entries.update(is_active=False)
        logger.info(f"Deactivated {count} expired blacklist entries")

    return {"deactivated_count": count}


@shared_task
def generate_rate_limit_report():
    """
    Generate daily rate limiting report
    Runs daily at 8 AM
    """
    from django.conf import settings
    from django.core.mail import send_mail

    from .models import RateLimitLog, RateLimitStats

    # Get yesterday's data
    yesterday = timezone.now().date() - timedelta(days=1)

    # Get logs for yesterday
    yesterday_logs = RateLimitLog.objects.filter(timestamp__date=yesterday)

    # Get stats for yesterday
    yesterday_stats = RateLimitStats.objects.filter(date=yesterday)

    if not yesterday_logs.exists():
        return {"message": "No rate limiting activity yesterday"}

    # Generate report data
    total_requests = yesterday_logs.count()
    denied_requests = yesterday_logs.filter(action="denied").count()
    burst_protections = yesterday_logs.filter(action="burst_protection").count()
    unique_ips = yesterday_logs.values("ip_address").distinct().count()

    denial_rate = (denied_requests / total_requests) * 100 if total_requests > 0 else 0

    # Top blocked IPs
    top_blocked = (
        yesterday_logs.filter(action__in=["denied", "burst_protection"])
        .values("ip_address")
        .annotate(count=Count("id"))
        .order_by("-count")[:5]
    )

    # Hourly breakdown
    hourly_stats = yesterday_stats.aggregate(
        avg_requests_per_hour=Avg("total_requests"),
        peak_hour_requests=Count("total_requests"),
        avg_denial_rate=Avg("denied_requests"),
    )

    # Create report
    report = f"""
    Rate Limiting Daily Report - {yesterday.strftime('%Y-%m-%d')}
    
    Summary:
    - Total Requests: {total_requests:,}
    - Denied Requests: {denied_requests:,} ({denial_rate:.2f}%)
    - Burst Protections: {burst_protections:,}
    - Unique IP Addresses: {unique_ips:,}
    
    Top Blocked IPs:
    """

    for ip_data in top_blocked:
        report += f"- {ip_data['ip_address']}: {ip_data['count']} blocks\n"

    # Send email report (if configured)
    if hasattr(settings, "RATE_LIMIT_REPORT_EMAIL") and settings.RATE_LIMIT_REPORT_EMAIL:
        try:
            send_mail(
                subject=f"Rate Limiting Report - {yesterday}",
                message=report,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.RATE_LIMIT_REPORT_EMAIL],
                fail_silently=True,
            )
            logger.info(f"Sent rate limiting report for {yesterday}")
        except Exception as e:
            logger.error(f"Failed to send rate limiting report: {e}")

    return {
        "date": yesterday.isoformat(),
        "total_requests": total_requests,
        "denied_requests": denied_requests,
        "denial_rate": denial_rate,
        "unique_ips": unique_ips,
    }


@shared_task
def detect_rate_limit_anomalies():
    """
    Detect unusual rate limiting patterns
    Runs every 15 minutes
    """
    from .models import RateLimitLog

    # Check last 15 minutes
    cutoff_time = timezone.now() - timedelta(minutes=15)
    recent_logs = RateLimitLog.objects.filter(timestamp__gte=cutoff_time)

    anomalies = []

    # Check for high denial rate
    total_requests = recent_logs.count()
    denied_requests = recent_logs.filter(action="denied").count()

    if total_requests > 100 and denied_requests / total_requests > 0.5:
        anomalies.append(f"High denial rate: {denied_requests}/{total_requests} ({(denied_requests/total_requests)*100:.1f}%)")

    # Check for repeated attacks from single IP
    ip_counts = recent_logs.filter(action="denied").values("ip_address").annotate(count=Count("id")).filter(count__gte=20)

    for ip_data in ip_counts:
        anomalies.append(f"Repeated attacks from {ip_data['ip_address']}: {ip_data['count']} denied requests")

    # Check for burst protection spikes
    burst_count = recent_logs.filter(action="burst_protection").count()
    if burst_count > 50:
        anomalies.append(f"High burst protection activity: {burst_count} triggers")

    if anomalies:
        logger.warning(f"Rate limiting anomalies detected: {'; '.join(anomalies)}")

        # Could send alerts here (email, Slack, etc.)
        return {"anomalies": anomalies}

    return {"message": "No anomalies detected"}
