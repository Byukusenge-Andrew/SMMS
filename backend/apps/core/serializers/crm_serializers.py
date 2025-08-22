"""
Serializers for CRM integration
"""

from rest_framework import serializers
from ..models.crm_models import GoHighLevelIntegration, CRMContact


class GoHighLevelIntegrationSerializer(serializers.ModelSerializer):
    """Serializer for GoHighLevel integration"""
    
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = GoHighLevelIntegration
        fields = [
            'id',
            'user',
            'user_username',
            'api_key',
            'location_id',
            'sync_contacts',
            'sync_opportunities',
            'sync_campaigns',
            'webhook_url',
            'webhook_secret',
            'is_active',
            'last_sync_date',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
        extra_kwargs = {
            'api_key': {'write_only': True},
            'webhook_secret': {'write_only': True},
        }


class CRMContactSerializer(serializers.ModelSerializer):
    """Serializer for CRM contacts"""
    
    full_name = serializers.ReadOnlyField()
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = CRMContact
        fields = [
            'id',
            'user',
            'user_username',
            'ghl_contact_id',
            'first_name',
            'last_name',
            'full_name',
            'email',
            'phone',
            'company',
            'status',
            'tags',
            'custom_fields',
            'social_media_profiles',
            'last_contacted',
            'ghl_created_at',
            'ghl_updated_at',
            'last_synced_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'user', 'ghl_contact_id', 'ghl_created_at',
            'ghl_updated_at', 'last_synced_at', 'created_at', 'updated_at'
        ]


class CRMContactCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating CRM contacts"""
    
    class Meta:
        model = CRMContact
        fields = [
            'first_name',
            'last_name',
            'email',
            'phone',
            'company',
            'status',
            'tags',
            'custom_fields',
            'social_media_profiles',
        ]
    
    def validate_email(self, value):
        """Validate email address"""
        if value:
            # Check if email already exists for this user
            user = self.context['request'].user
            queryset = CRMContact.objects.filter(user=user, email=value)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError("A contact with this email already exists")
        return value
    
    def validate_tags(self, value):
        """Validate tags list"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Tags must be a list")
        
        # Remove duplicates and empty tags
        cleaned_tags = []
        for tag in value:
            if isinstance(tag, str) and tag.strip():
                tag_clean = tag.strip()
                if tag_clean not in cleaned_tags:
                    cleaned_tags.append(tag_clean)
        
        return cleaned_tags
    
    def validate_social_media_profiles(self, value):
        """Validate social media profiles"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Social media profiles must be an object")
        
        allowed_platforms = ['linkedin', 'twitter', 'facebook', 'instagram']
        cleaned_profiles = {}
        
        for platform, url in value.items():
            if platform in allowed_platforms and isinstance(url, str) and url.strip():
                cleaned_profiles[platform] = url.strip()
        
        return cleaned_profiles
