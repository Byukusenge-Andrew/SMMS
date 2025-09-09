from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

from rest_framework import serializers

from .models import SocialMediaAccount, Team, TeamMember, UserProfile
from apps.core.models.payment_models import SubscriptionTier


class SubscriptionTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionTier
        fields = [
            "id",
            "name", 
            "display_name",
            "description",
            "price_monthly",
            "price_yearly",
            "max_social_accounts",
            "max_scheduled_posts",
            "max_team_members",
            "advanced_analytics",
            "priority_support",
            "custom_branding",
            "bulk_upload_scheduling",
            "hashtag_suggestions",
            "best_time_insights",
            "approval_workflows",
            "sso_support",
            "two_factor_auth",
            "custom_integrations",
            "phone_support",
            "dedicated_account_manager",
        ]


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ["id", "name", "owner", "created_at"]
        read_only_fields = ["id", "owner", "created_at"]


class UserSerializer(serializers.ModelSerializer):
    profile_uuid = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "date_joined", "profile_uuid"]
        read_only_fields = ["id", "date_joined", "profile_uuid"]

    def get_profile_uuid(self, obj):
        return str(obj.profile.id) if hasattr(obj, "profile") else None


class UserProfileSerializer(serializers.ModelSerializer):
    trial_days_left = serializers.SerializerMethodField()
    effective_subscription_tier = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = [
            "id",
            "company_name",
            "role",
            "avatar",
            "subscription_tier",
            "timezone",
            "time_format",
            "email_notifications",
            "slack_notifications",
            "is_trial_active",
            "trial_end_date",
            "trial_days_left",
            "effective_subscription_tier",
        ]
        read_only_fields = ["is_trial_active", "trial_end_date", "trial_days_left", "effective_subscription_tier"]
    
    def get_trial_days_left(self, obj):
        return obj.days_left_in_trial()
    
    def get_effective_subscription_tier(self, obj):
        effective_tier = obj.get_effective_subscription_tier()
        if effective_tier:
            return {
                "id": str(effective_tier.id),
                "name": effective_tier.name,
                "display_name": effective_tier.display_name,
                "price_monthly": effective_tier.price_monthly
            }
        return None


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    company_name = serializers.CharField(required=False, allow_blank=True)
    subscription_tier_id = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "password_confirm", "first_name", "last_name", "company_name", "subscription_tier_id"]

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError("Passwords don't match")
        
        # Validate subscription tier ID
        subscription_tier_id = attrs.get("subscription_tier_id")
        if subscription_tier_id:
            try:
                SubscriptionTier.objects.get(id=subscription_tier_id, is_active=True)
            except SubscriptionTier.DoesNotExist:
                raise serializers.ValidationError(f"Invalid subscription tier ID: {subscription_tier_id}")
        
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        company_name = validated_data.pop("company_name", "")
        subscription_tier_id = validated_data.pop("subscription_tier_id", None)

        password = validated_data.pop("password")
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            password=password,
        )

        # Get the subscription tier
        subscription_tier = None
        if subscription_tier_id:
            try:
                subscription_tier = SubscriptionTier.objects.get(id=subscription_tier_id, is_active=True)
            except SubscriptionTier.DoesNotExist:
                # Fallback to free tier if provided ID is invalid
                subscription_tier = SubscriptionTier.objects.filter(name="free", is_active=True).first()
        else:
            # Default to free tier if no tier specified
            subscription_tier = SubscriptionTier.objects.filter(name="free", is_active=True).first()

        # Create or get profile with subscription tier
        profile, created = UserProfile.objects.get_or_create(
            user=user, 
            defaults={
                "company_name": company_name,
                "subscription_tier": subscription_tier
            }
        )

        if not created:
            if company_name:
                profile.company_name = company_name
            if subscription_tier:
                profile.subscription_tier = subscription_tier
            profile.save()

        # Start trial if it's a paid tier
        if subscription_tier and subscription_tier.price_monthly > 0:
            profile.start_trial(trial_days=14)

        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, attrs):
        username = attrs.get("username")
        password = attrs.get("password")

        print(f"LoginSerializer: Attempting to authenticate with username/email: {username}")

        if username and password:
            # The custom backend will handle whether 'username' is an email or a username
            user = authenticate(request=self.context.get('request'), username=username, password=password)
            
            print(f"LoginSerializer: authenticate() returned: {user}")

            if not user:
                print("LoginSerializer: Authentication failed. User is None.")
                raise serializers.ValidationError("Invalid credentials. Please check your username/email and password.")
            
            if not user.is_active:
                print(f"LoginSerializer: User '{username}' is not active.")
                raise serializers.ValidationError("Account is disabled or email not verified.")
        else:
            raise serializers.ValidationError("Must include 'username' and 'password'.")

        attrs["user"] = user
        return attrs


class SocialMediaAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialMediaAccount
        fields = [
            "id",
            "platform",
            "username",
            "is_active",
            "created_at",
            "follower_count",
            "following_count",
            "platform_user_id",
        ]
        read_only_fields = ["id", "created_at", "follower_count", "following_count", "platform_user_id"]

    def validate(self, attrs):
        """Validate that the user doesn't already have this social media account"""
        platform = attrs.get("platform")
        username = attrs.get("username")

        # Only validate during creation (not during updates)
        if not self.instance and self.context.get("request"):
            user = self.context["request"].user
            existing = SocialMediaAccount.objects.filter(user=user, platform=platform, username=username)

            if existing.exists():
                raise serializers.ValidationError(
                    {"non_field_errors": [f'You already have a {platform} account with username "{username}" connected.']}
                )

        return attrs


class TeamMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    team = TeamSerializer(read_only=True)
    team_id = serializers.UUIDField(write_only=True, required=False, help_text="UUID of the team to invite to")

    class Meta:
        model = TeamMember
        fields = ["id", "team", "team_id", "user", "role", "invited_email", "is_active", "invited_at", "joined_at"]
        read_only_fields = ["id", "invited_at", "joined_at", "team", "user"]


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    role = serializers.CharField(write_only=True, required=False, allow_blank=True)
    company_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    subscription_tier_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "password",
            "password_confirm",
            "first_name",
            "last_name",
            "role",
            "company_name",
            "subscription_tier_id",
        )
        extra_kwargs = {
            "email": {"required": True},
            "first_name": {"required": False},
            "last_name": {"required": False},
            # Explicitly mark optional extras (already declared write_only above)
            "role": {"required": False},
            "company_name": {"required": False},
            "subscription_tier_id": {"required": False},
        }

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        
        # Validate subscription tier ID if provided
        subscription_tier_id = attrs.get("subscription_tier_id")
        if subscription_tier_id:
            try:
                SubscriptionTier.objects.get(id=subscription_tier_id, is_active=True)
            except SubscriptionTier.DoesNotExist:
                raise serializers.ValidationError({"subscription_tier_id": "Invalid subscription tier ID provided."})
        
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
        from datetime import timedelta
        from django.utils import timezone
        from apps.core.models.payment_models import UserSubscription
        
        validated_data.pop("password_confirm", None)
        role = validated_data.pop("role", None)
        company_name = validated_data.pop("company_name", None)
        subscription_tier_id = validated_data.pop("subscription_tier_id", None)
        
        user = User.objects.create_user(**validated_data)

        # Get the subscription tier
        subscription_tier = None
        if subscription_tier_id:
            try:
                subscription_tier = SubscriptionTier.objects.get(id=subscription_tier_id, is_active=True)
            except SubscriptionTier.DoesNotExist:
                # Fallback to free tier if provided ID is invalid
                subscription_tier = SubscriptionTier.objects.filter(name="free", is_active=True).first()
        else:
            # Default to free tier if no tier specified
            subscription_tier = SubscriptionTier.objects.filter(name="free", is_active=True).first()

        # Create UserProfile with subscription tier
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                "role": role,
                "company_name": company_name,
                "subscription_tier": subscription_tier
            }
        )
        
        if not created:
            if role:
                profile.role = role
            if company_name:
                profile.company_name = company_name
            if subscription_tier:
                profile.subscription_tier = subscription_tier
            profile.save()

        # Create UserSubscription record
        if subscription_tier:
            now = timezone.now()
            is_paid_tier = subscription_tier.price_monthly > 0
            
            # Set up trial for paid tiers, active status for free tier
            if is_paid_tier:
                status = 'trialing'
                trial_end = now + timedelta(days=14)  # 14-day trial
                start_trial = True
            else:
                status = 'active'
                trial_end = None
                start_trial = False
            
            user_subscription = UserSubscription.objects.create(
                user=user,
                tier=subscription_tier,
                status=status,
                billing_period='monthly',
                start_date=now,
                trial_end_date=trial_end,
            )
            
            # Update profile with trial information for paid tiers
            if start_trial:
                profile.trial_start_date = now
                profile.trial_end_date = trial_end
                profile.is_trial_active = True
                profile.save()

        return user


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get("username")
        password = attrs.get("password")

        if username and password:
            return attrs
        else:
            raise serializers.ValidationError('Must include "username" and "password".')
