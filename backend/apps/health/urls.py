from django.urls import path

from .views import health_check, system_status

urlpatterns = [
    path("", health_check, name="health-check"),
    path("status/", system_status, name="system-status"),
]
