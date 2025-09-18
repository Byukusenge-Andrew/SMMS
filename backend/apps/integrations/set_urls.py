"""
URL patterns for social media sets functionality
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .set_views import (
    SocialMediaSetViewSet,
    SocialMediaSetMembershipViewSet,
    BulkSetMembershipView,
    SetQuickCreateView,
    AccountSetsView
)

# Create router for viewsets
router = DefaultRouter()
router.register(r'social-sets', SocialMediaSetViewSet, basename='social-sets')
router.register(r'set-memberships', SocialMediaSetMembershipViewSet, basename='set-memberships')

# URL patterns for sets functionality
urlpatterns = [
    # Router URLs
    path('', include(router.urls)),
    
    # Additional set management URLs
    path('sets/quick-create/', SetQuickCreateView.as_view(), name='set-quick-create'),
    path('sets/bulk-membership/', BulkSetMembershipView.as_view(), name='bulk-set-membership'),
    path('accounts/<uuid:account_id>/sets/', AccountSetsView.as_view(), name='account-sets'),
]