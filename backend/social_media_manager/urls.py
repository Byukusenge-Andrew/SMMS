"""
URL configuration for social_media_manager project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.authentication.urls')),
    path('api/posts/', include('apps.posts.urls')),
    path('api/analytics/', include('apps.analytics.urls')),
    path('api/integrations/', include('apps.integrations.urls')),
    path('api/influencers/', include('apps.influencers.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
    path('api/collaborators/', include('apps.collaborators.urls')),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Health check
    path('health/', include('apps.health.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
