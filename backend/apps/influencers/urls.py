from django.urls import path
from . import views

urlpatterns = [
    path("", views.InfluencerProfileView.as_view(), name="influencer-profile"),
    path("campaigns/", views.CampaignListCreateView.as_view(), name="campaign-list-create"),
    path("campaigns/<uuid:pk>/", views.CampaignDetailView.as_view(), name="campaign-detail"),
    path("applications/", views.CampaignApplicationListCreateView.as_view(), name="application-list-create"),
    path("dashboard/", views.influencer_dashboard, name="influencer-dashboard"),
    path("import/", views.import_influencers, name="import-influencers"),
    path("analytics/", views.influencer_analytics, name="influencer-analytics"),
]
