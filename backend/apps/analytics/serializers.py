from rest_framework import serializers

from .models import (AnalyticsData, BestPerformingPost, PerformanceReport,
                     PlatformAverage)


class AnalyticsDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsData
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class BestPerformingPostSerializer(serializers.ModelSerializer):
    post_content = serializers.CharField(source="post.content", read_only=True)

    class Meta:
        model = BestPerformingPost
        fields = [
            "id",
            "post",
            "post_content",
            "platform",
            "metric_type",
            "metric_value",
            "period_start",
            "period_end",
            "rank",
            "created_at",
        ]


class PerformanceReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerformanceReport
        fields = "__all__"
        read_only_fields = ["id", "user", "created_at", "updated_at"]


class PlatformAverageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformAverage
        fields = "__all__"
        read_only_fields = ["id", "user", "calculated_at"]
