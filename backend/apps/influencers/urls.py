from django.urls import path

from . import views

urlpatterns = [
    # Influencer profile management
    path("", views.InfluencerProfileView.as_view(), name="influencer-profile"),
    path("dashboard/", views.influencer_dashboard, name="influencer-dashboard"),
    path("analytics/", views.influencer_analytics, name="influencer-analytics"),
    path("sync-followers/", views.sync_followers_view, name="sync-followers"),
    
    # Influencer discovery and search
    path("discover/", views.InfluencerDiscoveryView.as_view(), name="discover"),
    
    # Campaign management
    path("campaigns/", views.CampaignListCreateView.as_view(), name="campaign-list-create"),
    path("campaigns/<uuid:pk>/", views.CampaignDetailView.as_view(), name="campaign-detail"),
    
    # Campaign applications
    path("applications/", views.CampaignApplicationListCreateView.as_view(), name="application-list-create"),
    path("applications/<uuid:application_id>/status/", views.update_application_status, name="update-application-status"),
    
    # Portfolio management
    path("portfolio/", views.InfluencerPortfolioViewSet.as_view(), name="portfolio"),
    
    # Collaboration management
    path("collaborations/", views.collaboration_list_view, name="collaborations"),
    
    # Import functionality (if needed)
    path("import/", views.import_influencers, name="import-influencers"),
]
