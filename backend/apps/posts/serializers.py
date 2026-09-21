from rest_framework import serializers

from .models import Holiday, Post, PostSuggestion, PostTemplate, SocialSet, PostingScheduleSlot


class SocialSetSerializer(serializers.ModelSerializer):
    accounts_count = serializers.SerializerMethodField()

    class Meta:
        model = SocialSet
        fields = ["id", "name", "description", "accounts", "accounts_count", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_accounts_count(self, obj):
        return obj.accounts.count()


class PostSerializer(serializers.ModelSerializer):
    # Allow missing scheduled_time for immediate/draft posts; we'll default it to now in create()
    scheduled_time = serializers.DateTimeField(required=False)
    hashtags_list = serializers.SerializerMethodField()
    tagged_users_list = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    approval_reviewer_name = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "social_account",
            "social_set",
            "content",
            "caption",
            "hashtags",
            "hashtags_list",
            "image",
            "video",
            "media_url",
            "scheduled_time",
            "timezone",
            "post_type",
            "status",
            "platform",
            "location",
            "latitude",
            "longitude",
            "tagged_users",
            "tagged_users_list",
            "is_locked",
            "is_template",
            "is_evergreen",
            "recycle_interval_days",
            "recycle_count",
            "max_recycle_count",
            "last_recycled_at",
            "original_post",
            "approval_reviewer",
            "approval_reviewer_name",
            "approval_feedback",
            "submitted_for_approval_at",
            "reviewed_at",
            "external_post_id",
            "published_at",
            "error_message",
            "can_edit",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", "external_post_id", "published_at", "error_message", 
            "recycle_count", "last_recycled_at", "original_post",
            "approval_reviewer", "submitted_for_approval_at", "reviewed_at", 
            "created_at", "updated_at"
        ]

    def get_hashtags_list(self, obj):
        return obj.get_hashtags_list()

    def get_tagged_users_list(self, obj):
        return obj.get_tagged_users_list()

    def get_can_edit(self, obj):
        return obj.can_edit()

    def get_approval_reviewer_name(self, obj):
        if obj.approval_reviewer:
            return obj.approval_reviewer.get_full_name() or obj.approval_reviewer.username
        return None


class PostingScheduleSlotSerializer(serializers.ModelSerializer):
    day_name = serializers.SerializerMethodField()

    class Meta:
        model = PostingScheduleSlot
        fields = [
            "id",
            "platform",
            "day_of_week",
            "day_name",
            "time",
            "timezone",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_day_name(self, obj):
        return dict(PostingScheduleSlot.DAY_OF_WEEK_CHOICES).get(obj.day_of_week, str(obj.day_of_week))


class BulkPostingScheduleSlotSerializer(serializers.Serializer):
    days_of_week = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=6),
        help_text="List of day integers (0=Monday, 6=Sunday)"
    )
    times = serializers.ListField(
        child=serializers.TimeField(),
        help_text="List of time strings (e.g. ['10:00:00', '15:00:00'])"
    )
    platform = serializers.CharField(required=False, allow_blank=True, default="")
    timezone = serializers.CharField(required=False, default="UTC")


class QueueNextSlotRequestSerializer(serializers.Serializer):
    platform = serializers.CharField(required=False, allow_blank=True, default="")
    after_time = serializers.DateTimeField(required=False, allow_null=True)


class PostApprovalActionSerializer(serializers.Serializer):
    feedback = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_scheduled_time(self, value):
        # Only enforce future time when explicitly scheduling
        from django.utils import timezone
        status_val = None
        try:
            status_val = (self.initial_data or {}).get("status")
        except Exception:
            status_val = None

        if status_val == "scheduled":
            if not value or value <= timezone.now():
                raise serializers.ValidationError("Scheduled time must be in the future")
        # For drafts/published-now we accept current or missing value; missing is handled in create()
        return value

    def create(self, validated_data):
        # Default scheduled_time to now when not provided (e.g., immediate/draft posts)
        from django.utils import timezone
        if not validated_data.get("scheduled_time"):
            validated_data["scheduled_time"] = timezone.now()
        return super().create(validated_data)


class PostCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating posts with multiple platforms"""

    platforms = serializers.ListField(child=serializers.CharField(), write_only=True, required=False)

    class Meta:
        model = Post
        fields = [
            "social_account",
            "social_set",
            "content",
            "caption",
            "hashtags",
            "image",
            "video",
            "media_url",
            "scheduled_time",
            "timezone",
            "post_type",
            "platform",
            "platforms",
            "location",
            "latitude",
            "longitude",
            "tagged_users",
            "is_locked",
            "is_template",
        ]

    def create(self, validated_data):
        platforms = validated_data.pop("platforms", [])
        user = self.context["request"].user

        if platforms:
            # Create multiple posts for different platforms
            posts = []
            for platform in platforms:
                post_data = validated_data.copy()
                post_data["platform"] = platform
                post_data["user"] = user
                posts.append(Post.objects.create(**post_data))
            return posts[0]  # Return first post
        else:
            # Single platform post
            validated_data["user"] = user
            return Post.objects.create(**validated_data)


class PostTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostTemplate
        fields = ["id", "name", "content", "caption", "hashtags", "post_type", "platforms", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ["id", "name", "date", "country", "category", "description"]
        read_only_fields = ["id"]


class PostSuggestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostSuggestion
        fields = ["id", "suggestion_type", "platform", "content", "confidence_score", "is_used", "created_at"]
        read_only_fields = ["id", "created_at"]


class BulkPostSerializer(serializers.Serializer):
    """Serializer for bulk post operations"""

    post_ids = serializers.ListField(child=serializers.IntegerField(), min_length=1)
    action = serializers.ChoiceField(choices=["publish", "cancel", "reschedule", "delete"])
    scheduled_time = serializers.DateTimeField(required=False)

    def validate(self, attrs):
        if attrs["action"] == "reschedule" and not attrs.get("scheduled_time"):
            raise serializers.ValidationError("scheduled_time is required for reschedule action")
        return attrs
