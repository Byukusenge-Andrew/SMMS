from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

from rest_framework import serializers

from .models import SocialMediaAccount, Team, TeamMember, UserProfile


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
    class Meta:
        model = UserProfile
        fields = [
            "id",
            "company_name",
            "role",
            "avatar",
            "subscription_type",
            "timezone",
            "time_format",
            "email_notifications",
            "slack_notifications",
        ]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    company_name = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "password_confirm", "first_name", "last_name", "company_name"]

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError("Passwords don't match")
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        company_name = validated_data.pop("company_name", "")

        password = validated_data.pop("password")
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            password=password,
        )

        # Create or get profile
        profile, created = UserProfile.objects.get_or_create(user=user, defaults={"company_name": company_name})

        if not created and company_name:
            profile.company_name = company_name
            profile.save()

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
    company_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    role = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "password",
            "password_confirm",
            "first_name",
            "last_name",
            "company_name",
            "role",
        )
        extra_kwargs = {
            "email": {"required": True},
            "first_name": {"required": False},
            "last_name": {"required": False},
            # Explicitly mark optional extras (already declared write_only above)
            "company_name": {"required": False},
            "role": {"required": False},
        }

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
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
        validated_data.pop("password_confirm", None)
        company_name = validated_data.pop("company_name", None)
        role = validated_data.pop("role", None)
        user = User.objects.create_user(**validated_data)

        # Create UserProfile
        profile, created = UserProfile.objects.get_or_create(user=user)
        if company_name:
            profile.company_name = company_name
        if role:
            profile.role = role
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
