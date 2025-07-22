from rest_framework import serializers
from .models import (
    AnalyticsData, CommentAnalytics, PerformanceReport, 
    BestPerformingPost, PlatformAverage, AnalyticsInsight
)

class AnalyticsDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsData
        fields = [
            'id', 'metric_type', 'value', 'date', 'platform',
            'country', 'city', 'latitude', 'longitude',
            'age_group', 'gender', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class CommentAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommentAnalytics
        fields = [
            'id', 'comment_id', 'comment_text', 'author_username',
            'sentiment', 'sentiment_score', 'confidence_score',
            'likes_count', 'replies_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class PerformanceReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerformanceReport
        fields = [
            'id', 'report_type', 'title', 'start_date', 'end_date',
            'data', 'pdf_file', 'csv_file', 'is_generated',
            'generated_at', 'sent_via_email', 'sent_via_slack',
            'created_at'
        ]
        read_only_fields = ['id', 'generated_at', 'created_at']

class BestPerformingPostSerializer(serializers.ModelSerializer):
    post_content = serializers.CharField(source='post.content', read_only=True)
    post_image = serializers.ImageField(source='post.image', read_only=True)
    
    class Meta:
        model = BestPerformingPost
        fields = [
            'id', 'platform', 'metric_type', 'metric_value',
            'period_start', 'period_end', 'period_type', 'rank',
            'post_content', 'post_image', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class PlatformAverageSerializer(serializers.ModelSerializer):
    platform_display = serializers.SerializerMethodField()
    
    class Meta:
        model = PlatformAverage
        fields = [
            'id', 'platform', 'platform_display', 'avg_impressions',
            'avg_reach', 'avg_engagement_rate', 'avg_likes',
            'avg_shares', 'avg_comments', 'avg_saves',
            'avg_follower_growth', 'total_followers',
            'period_start', 'period_end', 'period_type', 'calculated_at'
        ]
        read_only_fields = ['id', 'calculated_at']
    
    def get_platform_display(self, obj):
        return obj.platform or 'Overall'

class AnalyticsInsightSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsInsight
        fields = [
            'id', 'insight_type', 'title', 'description',
            'platform', 'metric_type', 'confidence_score',
            'action_items', 'is_read', 'priority',
            'created_at', 'expires_at'
        ]
        read_only_fields = ['id', 'created_at']

class AnalyticsDashboardSerializer(serializers.Serializer):
    """Serializer for analytics dashboard data"""
    overview = serializers.DictField()
    recent_performance = serializers.ListField()
    platform_breakdown = serializers.DictField()
    best_posts = serializers.ListField()
    insights = serializers.ListField()
    location_data = serializers.ListField()

class MetricsComparisonSerializer(serializers.Serializer):
    """Serializer for metrics comparison"""
    current_period = serializers.DictField()
    previous_period = serializers.DictField()
    growth_percentage = serializers.DictField()
    trend = serializers.CharField()

class LocationAnalyticsSerializer(serializers.Serializer):
    """Serializer for location-based analytics"""
    country = serializers.CharField()
    city = serializers.CharField(required=False)
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False)
    total_impressions = serializers.IntegerField()
    total_reach = serializers.IntegerField()
    total_engagement = serializers.IntegerField()
    percentage_of_total = serializers.FloatField()

class SentimentAnalysisSerializer(serializers.Serializer):
    """Serializer for sentiment analysis summary"""
    positive_count = serializers.IntegerField()
    negative_count = serializers.IntegerField()
    neutral_count = serializers.IntegerField()
    positive_percentage = serializers.FloatField()
    negative_percentage = serializers.FloatField()
    neutral_percentage = serializers.FloatField()
    average_sentiment_score = serializers.FloatField()
    most_positive_comment = serializers.CharField()
    most_negative_comment = serializers.CharField()

class EngagementTrendSerializer(serializers.Serializer):
    """Serializer for engagement trends"""
    date = serializers.DateField()
    platform = serializers.CharField()
    likes = serializers.IntegerField()
    shares = serializers.IntegerField()
    comments = serializers.IntegerField()
    engagement_rate = serializers.FloatField()

class ReportGenerationSerializer(serializers.Serializer):
    """Serializer for report generation requests"""
    report_type = serializers.ChoiceField(choices=[
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
        ('custom', 'Custom')
    ])
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    platforms = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    include_pdf = serializers.BooleanField(default=True)
    include_csv = serializers.BooleanField(default=False)
    send_email = serializers.BooleanField(default=False)
    send_slack = serializers.BooleanField(default=False)
    
    def validate(self, attrs):
        if attrs['report_type'] == 'custom':
            if not attrs.get('start_date') or not attrs.get('end_date'):
                raise serializers.ValidationError(
                    "start_date and end_date are required for custom reports"
                )
        return attrs
