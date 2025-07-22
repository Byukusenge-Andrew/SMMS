from rest_framework import serializers
from .models import Post, PostTemplate, Holiday, PostSuggestion, SocialSet

class SocialSetSerializer(serializers.ModelSerializer):
    accounts_count = serializers.SerializerMethodField()
    
    class Meta:
        model = SocialSet
        fields = ['id', 'name', 'description', 'accounts', 'accounts_count', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_accounts_count(self, obj):
        return obj.accounts.count()

class PostSerializer(serializers.ModelSerializer):
    hashtags_list = serializers.SerializerMethodField()
    tagged_users_list = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    
    class Meta:
        model = Post
        fields = [
            'id', 'social_account', 'social_set', 'content', 'caption', 'hashtags', 
            'hashtags_list', 'image', 'video', 'media_url', 'scheduled_time', 
            'timezone', 'post_type', 'status', 'platform', 'location', 'latitude', 
            'longitude', 'tagged_users', 'tagged_users_list', 'is_locked', 
            'is_template', 'external_post_id', 'published_at', 'error_message', 
            'can_edit', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'external_post_id', 'published_at', 'error_message', 'created_at', 'updated_at']
    
    def get_hashtags_list(self, obj):
        return obj.get_hashtags_list()
    
    def get_tagged_users_list(self, obj):
        return obj.get_tagged_users_list()
    
    def get_can_edit(self, obj):
        return obj.can_edit()
    
    def validate_scheduled_time(self, value):
        from django.utils import timezone
        if value <= timezone.now():
            raise serializers.ValidationError("Scheduled time must be in the future")
        return value

class PostCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating posts with multiple platforms"""
    platforms = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Post
        fields = [
            'social_account', 'social_set', 'content', 'caption', 'hashtags',
            'image', 'video', 'media_url', 'scheduled_time', 'timezone',
            'post_type', 'platform', 'platforms', 'location', 'latitude',
            'longitude', 'tagged_users', 'is_locked', 'is_template'
        ]
    
    def create(self, validated_data):
        platforms = validated_data.pop('platforms', [])
        user = self.context['request'].user
        
        if platforms:
            # Create multiple posts for different platforms
            posts = []
            for platform in platforms:
                post_data = validated_data.copy()
                post_data['platform'] = platform
                post_data['user'] = user
                posts.append(Post.objects.create(**post_data))
            return posts[0]  # Return first post
        else:
            # Single platform post
            validated_data['user'] = user
            return Post.objects.create(**validated_data)

class PostTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostTemplate
        fields = [
            'id', 'name', 'content', 'caption', 'hashtags', 'post_type',
            'platforms', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ['id', 'name', 'date', 'country', 'category', 'description']
        read_only_fields = ['id']

class PostSuggestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostSuggestion
        fields = [
            'id', 'suggestion_type', 'platform', 'content', 'confidence_score',
            'is_used', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class BulkPostSerializer(serializers.Serializer):
    """Serializer for bulk post operations"""
    post_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1
    )
    action = serializers.ChoiceField(choices=['publish', 'cancel', 'reschedule', 'delete'])
    scheduled_time = serializers.DateTimeField(required=False)
    
    def validate(self, attrs):
        if attrs['action'] == 'reschedule' and not attrs.get('scheduled_time'):
            raise serializers.ValidationError("scheduled_time is required for reschedule action")
        return attrs
