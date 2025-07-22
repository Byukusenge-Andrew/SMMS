from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import UserProfile, SocialMediaAccount, TeamMember

class UserSerializer(serializers.ModelSerializer):
    profile_uuid = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'date_joined', 'profile_uuid']
        read_only_fields = ['id', 'date_joined', 'profile_uuid']
    
    def get_profile_uuid(self, obj):
        return str(obj.profile.id) if hasattr(obj, 'profile') else None

class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'user', 'company_name', 'avatar', 'subscription_type', 
            'time_format', 'email_notifications', 'slack_notifications',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    company_name = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 'first_name', 'last_name', 'company_name']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        company_name = validated_data.pop('company_name', '')
        
        password = validated_data.pop('password')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            password=password
        )
        
        # Create or get profile
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={'company_name': company_name}
        )
        
        if not created and company_name:
            profile.company_name = company_name
            profile.save()
            
        return user

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            if not user.is_active:
                raise serializers.ValidationError('Account is disabled')
            attrs['user'] = user
        else:
            raise serializers.ValidationError('Must include username and password')
        
        return attrs

class SocialMediaAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialMediaAccount
        fields = [
            'id', 'platform', 'username', 'is_active', 'created_at',
            'follower_count', 'following_count', 'platform_user_id'
        ]
        read_only_fields = ['id', 'created_at', 'follower_count', 'following_count']

class TeamMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = TeamMember
        fields = ['id', 'user', 'role', 'invited_at', 'accepted_at', 'is_active']
        read_only_fields = ['id', 'invited_at', 'accepted_at']

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password2', 'first_name', 'last_name')
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': False},
            'last_name': {'required': False},
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def create(self, validated_data):
        validated_data.pop('password2', None)
        user = User.objects.create_user(**validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            return attrs
        else:
            raise serializers.ValidationError('Must include "username" and "password".')
