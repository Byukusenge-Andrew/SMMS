from django.urls import path
from . import views

urlpatterns = [
    # Working endpoints
    path("dashboard/", views.analytics_dashboard, name="analytics-dashboard"),
    path("collect/", views.collect_analytics, name="collect-analytics"),
    path("sentiment/", views.comment_sentiment_analysis, name="sentiment-analysis"),
    
    # Enable these working endpoints
    path("reports/", views.performance_reports, name="performance-reports"),
    path("best-posts/", views.best_performing_posts, name="best-posts"),
    path("platform-averages/", views.platform_averages, name="platform-averages"),
    path("location-heatmap/", views.location_heatmap, name="location-heatmap"),
    path("reels/", views.reels_analytics, name="reels-analytics"),
    path("reports/weekly/", views.weekly_report, name="weekly-report"),
    path("reports/monthly/", views.monthly_report, name="monthly-report"),
    path("reports/yearly/", views.yearly_report, name="yearly-report"),
]
