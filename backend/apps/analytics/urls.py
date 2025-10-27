"""
URL configuration for analytics app
"""

from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    # Basic Analytics
    path("dashboard/", views.analytics_dashboard, name="analytics-dashboard"),
    path("overview/", views.analytics_overview, name="analytics-overview"),
    path("collect/", views.collect_analytics, name="collect-analytics"),
    path("platform-insights/", views.platform_insights, name="platform-insights"),
    # Reports and Performance
    path("reports/", views.performance_reports, name="performance-reports"),
    path("reports/weekly/", views.weekly_report, name="weekly-report"),
    path("reports/monthly/", views.monthly_report, name="monthly-report"),
    path("reports/yearly/", views.yearly_report, name="yearly-report"),
    # Analytics Data
    path("best-posts/", views.best_performing_posts, name="best-posts"),
    path("platform-averages/", views.platform_averages, name="platform-averages"),
    path("location-heatmap/", views.location_heatmap, name="location-heatmap"),
    path("reels/", views.reels_analytics, name="reels-analytics"),
    # AI-Powered Analytics
    path("ai/insights/", views.ai_insights, name="ai-insights"),
    path("ai/recommendations/", views.ai_recommendations, name="ai-recommendations"),
    path("ai/competitor-analysis/", views.analyze_competitor, name="competitor-analysis"),
    path("ai/predict-performance/", views.predict_performance, name="predict-performance"),
]
