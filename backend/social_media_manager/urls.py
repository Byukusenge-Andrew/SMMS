"""
URL configuration for social_media_manager project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.authentication.urls")),
    path("api/posts/", include("apps.posts.urls")),
    path("api/analytics/", include("apps.analytics.urls")),  # Enable analytics
    path("api/integrations/", include("apps.integrations.urls")),
    path("api/influencers/", include("apps.influencers.urls")),
    path("api/notifications/", include("apps.notifications.urls")),
    path("api/collaborators/", include("apps.collaborators.urls")),
    path("api/messaging/", include("apps.messaging.urls")),  # Enable messaging
    path("api/media/", include("apps.media.urls")),  # Media management
    path("api/core/", include("apps.core.urls")),  # Rate limiting management
    path("api/billing/", include("apps.billing.urls")),  # Billing system
    # API Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    # Health check
    path("health/", include("apps.health.urls")),
    # OAuth/SSO
    path("oauth/", include("social_django.urls", namespace="social")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
