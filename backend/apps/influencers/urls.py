from django.urls import path
from .views import (
    InfluencerProfileView,
    CampaignListCreateView,
    CampaignDetailView,
    CampaignApplicationListCreateView,
    influencer_dashboard,
)

urlpatterns = [
    path("profile/", InfluencerProfileView.as_view(), name="influencer-profile"),
    path("campaigns/", CampaignListCreateView.as_view(), name="campaign-list-create"),
    path("campaigns/<int:pk>/", CampaignDetailView.as_view(), name="campaign-detail"),
    path("applications/", CampaignApplicationListCreateView.as_view(), name="application-list-create"),
    path("dashboard/", influencer_dashboard, name="influencer-dashboard"),
]
