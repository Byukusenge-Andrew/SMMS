from django.urls import path
from .views import (
    analytics_dashboard, collect_analytics, comment_sentiment_analysis,
    performance_reports, best_performing_posts, platform_averages
)

urlpatterns = [
    path('dashboard/', analytics_dashboard, name='analytics-dashboard'),
    path('collect/', collect_analytics, name='collect-analytics'),
    path('sentiment/', comment_sentiment_analysis, name='comment-sentiment'),
    path('reports/', performance_reports, name='performance-reports'),
    path('best-posts/', best_performing_posts, name='best-posts'),
    path('averages/', platform_averages, name='platform-averages'),
]
