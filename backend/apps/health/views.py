from django.http import JsonResponse
from django.db import connections
from django.db.utils import OperationalError
from django.conf import settings
import redis
import socket
import platform
import time
import datetime
import psutil


def health_check(request):
    """Basic health check endpoint that returns system status"""
    try:
        # Check database connection
        db_conn = connections["default"]
        db_conn.cursor()
        db_status = True
    except OperationalError:
        db_status = False

    # Check Redis connection
    redis_status = False
    try:
        r = redis.from_url(settings.REDIS_URL)
        if r.ping():
            redis_status = True
    except:
        redis_status = False

    # Overall status
    status = "healthy" if db_status and redis_status else "unhealthy"

    return JsonResponse(
        {
            "status": status,
            "timestamp": datetime.datetime.now().isoformat(),
            "services": {
                "database": "up" if db_status else "down",
                "redis": "up" if redis_status else "down",
            },
        }
    )


def system_status(request):
    """Detailed system status endpoint"""
    # Basic system info
    system_info = {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "time": datetime.datetime.now().isoformat(),
        "uptime": time.time() - psutil.boot_time(),
    }

    # CPU and memory
    system_resources = {
        "cpu_usage": psutil.cpu_percent(interval=1),
        "memory": {
            "total": round(psutil.virtual_memory().total / (1024.0**3), 2),  # GB
            "available": round(psutil.virtual_memory().available / (1024.0**3), 2),  # GB
            "used_percent": psutil.virtual_memory().percent,
        },
        "disk": {
            "total": round(psutil.disk_usage("/").total / (1024.0**3), 2),  # GB
            "free": round(psutil.disk_usage("/").free / (1024.0**3), 2),  # GB
            "used_percent": psutil.disk_usage("/").percent,
        },
    }

    # Database connection
    try:
        db_conn = connections["default"]
        db_conn.cursor()
        db_status = "connected"

        # Get some basic DB stats
        cursor = db_conn.cursor()
        cursor.execute("SELECT pg_database_size(%s)", [settings.DATABASES["default"]["NAME"]])
        db_size = cursor.fetchone()[0]

        db_info = {
            "status": db_status,
            "name": settings.DATABASES["default"]["NAME"],
            "host": settings.DATABASES["default"]["HOST"],
            "size_mb": round(db_size / (1024.0 * 1024), 2),
        }
    except Exception as e:
        db_info = {
            "status": "error",
            "error": str(e),
        }

    # Redis connection
    try:
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        redis_info = r.info()

        redis_status = {
            "status": "connected",
            "version": redis_info.get("redis_version", "unknown"),
            "memory_used_mb": round(redis_info.get("used_memory", 0) / (1024.0 * 1024), 2),
            "clients_connected": redis_info.get("connected_clients", 0),
        }
    except Exception as e:
        redis_status = {
            "status": "error",
            "error": str(e),
        }

    # Return all information
    return JsonResponse(
        {
            "system": system_info,
            "resources": system_resources,
            "services": {
                "database": db_info,
                "redis": redis_status,
            },
        }
    )
