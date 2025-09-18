"""
Serializers for social media sets functionality
"""

from rest_framework import serializers
from django.db.models import Count, Sum

from .models import SocialMediaSet, SocialMediaSetMembership, SocialMediaAccount
from .serializers import SocialMediaAccountSerializer


class SocialMediaSetSerializer(serializers.ModelSerializer):
    """Serializer for SocialMediaSet model"""
    
    account_count = serializers.SerializerMethodField()
    platform_count = serializers.SerializerMethodField()
    total_followers = serializers.SerializerMethodField()
    accounts = serializers.SerializerMethodField()
    platforms_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = SocialMediaSet
        fields = [
            'id', 'name', 'description', 'color', 'icon',
            'is_global', 'is_active', 'is_default_for_posting',
            'auto_assign_new_accounts', 'auto_assign_platforms',
            'account_count', 'platform_count', 'total_followers',
            'accounts', 'platforms_summary', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_account_count(self, obj):
        """Get number of accounts in this set"""
        return obj.social_accounts.filter(is_active=True).count()
    
    def get_platform_count(self, obj):
        """Get number of unique platforms in this set"""
        return obj.social_accounts.filter(is_active=True).values('platform').distinct().count()
    
    def get_total_followers(self, obj):
        """Get total followers across all accounts in set"""
        return obj.social_accounts.filter(is_active=True).aggregate(
            total=Sum('followers_count')
        )['total'] or 0
    
    def get_accounts(self, obj):
        """Get serialized accounts in this set"""
        request = self.context.get('request')
        include_accounts = request and request.query_params.get('include_accounts', 'false').lower() == 'true'
        
        if include_accounts:
            accounts = obj.social_accounts.filter(is_active=True).order_by('platform', 'username')
            return SocialMediaAccountSerializer(accounts, many=True, context=self.context).data
        return []
    
    def get_platforms_summary(self, obj):
        """Get summary of platforms and account counts"""
        platforms = obj.social_accounts.filter(is_active=True).values('platform').annotate(
            count=Count('id'),
            total_followers=Sum('followers_count')
        ).order_by('platform')
        
        return list(platforms)
    
    def validate(self, attrs):
        """Validate set data"""
        user = self.context['request'].user
        
        # Check if trying to create multiple global sets
        if attrs.get('is_global', False):
            existing_global = SocialMediaSet.objects.filter(
                user=user,
                is_global=True
            )
            if self.instance:
                existing_global = existing_global.exclude(id=self.instance.id)
            
            if existing_global.exists():
                raise serializers.ValidationError({
                    'is_global': 'You can only have one global social media set'
                })
        
        # Validate color format
        color = attrs.get('color', '')
        if color:
            if not color.startswith('#'):
                attrs['color'] = f"#{color}"
            if len(attrs['color']) != 7:
                raise serializers.ValidationError({
                    'color': 'Color must be a valid hex color code (#RRGGBB)'
                })
        
        return attrs
    
    def create(self, validated_data):
        """Create social media set"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class SocialMediaSetMembershipSerializer(serializers.ModelSerializer):
    """Serializer for SocialMediaSetMembership model"""
    
    account_details = serializers.SerializerMethodField()
    set_details = serializers.SerializerMethodField()
    
    class Meta:
        model = SocialMediaSetMembership
        fields = [
            'id', 'social_set', 'social_account', 'added_at', 'added_by',
            'is_primary_set', 'custom_name', 'posting_enabled', 'post_order',
            'account_details', 'set_details'
        ]
        read_only_fields = ['id', 'added_at']
    
    def get_account_details(self, obj):
        """Get basic account details"""
        return {
            'id': str(obj.social_account.id),
            'platform': obj.social_account.platform,
            'username': obj.social_account.username,
            'display_name': obj.social_account.display_name,
            'followers_count': obj.social_account.followers_count,
            'is_active': obj.social_account.is_active,
        }
    
    def get_set_details(self, obj):
        """Get basic set details"""
        return {
            'id': str(obj.social_set.id),
            'name': obj.social_set.name,
            'color': obj.social_set.color,
            'icon': obj.social_set.icon,
            'is_global': obj.social_set.is_global,
        }
    
    def validate(self, attrs):
        """Validate membership data"""
        user = self.context['request'].user
        
        # Ensure set and account belong to the user
        if attrs['social_set'].user != user:
            raise serializers.ValidationError({
                'social_set': 'You can only add accounts to your own sets'
            })
        
        if attrs['social_account'].user != user:
            raise serializers.ValidationError({
                'social_account': 'You can only manage your own social accounts'
            })
        
        return attrs


class BulkSetMembershipSerializer(serializers.Serializer):
    """Serializer for bulk adding/removing accounts to/from sets"""
    
    account_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        help_text="List of social account IDs"
    )
    set_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        help_text="List of social set IDs"
    )
    action = serializers.ChoiceField(
        choices=['add', 'remove'],
        help_text="Action to perform: add or remove"
    )
    posting_enabled = serializers.BooleanField(
        default=True,
        help_text="Enable posting for added accounts"
    )
    
    def validate_account_ids(self, value):
        """Validate account IDs belong to user"""
        user = self.context['request'].user
        
        valid_accounts = SocialMediaAccount.objects.filter(
            id__in=value,
            user=user
        ).values_list('id', flat=True)
        
        invalid_ids = set(value) - set(valid_accounts)
        if invalid_ids:
            raise serializers.ValidationError(
                f"Invalid account IDs: {list(invalid_ids)}"
            )
        
        return value
    
    def validate_set_ids(self, value):
        """Validate set IDs belong to user"""
        user = self.context['request'].user
        
        valid_sets = SocialMediaSet.objects.filter(
            id__in=value,
            user=user
        ).values_list('id', flat=True)
        
        invalid_ids = set(value) - set(valid_sets)
        if invalid_ids:
            raise serializers.ValidationError(
                f"Invalid set IDs: {list(invalid_ids)}"
            )
        
        return value


class SetQuickCreateSerializer(serializers.Serializer):
    """Serializer for quickly creating a set with accounts"""
    
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(required=False, allow_blank=True)
    color = serializers.CharField(max_length=7, default='#3B82F6')
    icon = serializers.CharField(max_length=50, default='users')
    account_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text="Account IDs to add to the set"
    )
    is_default_for_posting = serializers.BooleanField(default=False)
    auto_assign_new_accounts = serializers.BooleanField(default=False)
    auto_assign_platforms = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True
    )
    
    def validate_account_ids(self, value):
        """Validate account IDs"""
        if value:
            user = self.context['request'].user
            valid_accounts = SocialMediaAccount.objects.filter(
                id__in=value,
                user=user
            ).values_list('id', flat=True)
            
            invalid_ids = set(value) - set(valid_accounts)
            if invalid_ids:
                raise serializers.ValidationError(
                    f"Invalid account IDs: {list(invalid_ids)}"
                )
        
        return value
    
    def validate_name(self, value):
        """Validate set name is unique for user"""
        user = self.context['request'].user
        
        if SocialMediaSet.objects.filter(user=user, name=value).exists():
            raise serializers.ValidationError(
                "You already have a set with this name"
            )
        
        return value
    
    def create(self, validated_data):
        """Create set with accounts"""
        account_ids = validated_data.pop('account_ids', [])
        user = self.context['request'].user
        
        # Create the set
        social_set = SocialMediaSet.objects.create(
            user=user,
            **validated_data
        )
        
        # Add accounts to the set
        if account_ids:
            accounts = SocialMediaAccount.objects.filter(
                id__in=account_ids,
                user=user
            )
            
            for account in accounts:
                account.add_to_set(social_set, added_by=user)
        
        return social_set


class SocialMediaSetStatsSerializer(serializers.Serializer):
    """Serializer for set statistics"""
    
    total_sets = serializers.IntegerField(read_only=True)
    global_set_id = serializers.UUIDField(read_only=True)
    default_set_id = serializers.UUIDField(read_only=True)
    total_accounts = serializers.IntegerField(read_only=True)
    accounts_without_sets = serializers.IntegerField(read_only=True)
    platform_distribution = serializers.DictField(read_only=True)
    set_summary = serializers.ListField(read_only=True)