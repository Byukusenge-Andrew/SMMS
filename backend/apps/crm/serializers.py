from rest_framework import serializers
from .models import Contact, Pipeline, Deal, Activity


class ContactSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Contact
        fields = [
            "id", "first_name", "last_name", "full_name", "email", "phone",
            "company", "job_title", "website", "avatar", "status", "tags",
            "notes", "twitter_handle", "linkedin_url", "instagram_handle",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.email


class PipelineSerializer(serializers.ModelSerializer):
    deal_count = serializers.SerializerMethodField()
    total_value = serializers.SerializerMethodField()

    class Meta:
        model = Pipeline
        fields = ["id", "name", "description", "deal_count", "total_value", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_deal_count(self, obj):
        return obj.deals.count()

    def get_total_value(self, obj):
        return sum(d.value for d in obj.deals.all())


class DealSerializer(serializers.ModelSerializer):
    contact_name = serializers.SerializerMethodField()
    pipeline_name = serializers.SerializerMethodField()

    class Meta:
        model = Deal
        fields = [
            "id", "title", "stage", "value", "currency", "close_date",
            "notes", "contact", "contact_name", "pipeline", "pipeline_name",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_contact_name(self, obj):
        if obj.contact:
            return str(obj.contact)
        return None

    def get_pipeline_name(self, obj):
        if obj.pipeline:
            return obj.pipeline.name
        return None


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = [
            "id", "type", "title", "description", "due_date", "completed",
            "contact", "deal", "created_at",
        ]
        read_only_fields = ["id", "created_at"]
