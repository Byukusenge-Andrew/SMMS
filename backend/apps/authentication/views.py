import logging

from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.utils.html import strip_tags
from django.views.decorators.csrf import csrf_exempt

from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import generics, permissions, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateAPIView
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import EmailVerificationToken, PasswordResetToken, SocialMediaAccount, Team, TeamMember, UserProfile
from .serializers import (
    ForgotPasswordSerializer,
    LoginSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    SocialMediaAccountSerializer,
    SubscriptionTierSerializer,
    TeamMemberSerializer,
    TeamSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)
from .tasks import send_team_invitation_email
from apps.core.models.payment_models import SubscriptionTier

# Set up logger
logger = logging.getLogger(__name__)


@extend_schema(
    responses={
        200: SubscriptionTierSerializer(many=True),
    },
    summary="Get available subscription tiers",
    description="Get list of available subscription tiers for registration",
)
@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def subscription_tiers_view(request):
    """Get available subscription tiers"""
    tiers = SubscriptionTier.objects.filter(is_active=True).order_by('price_monthly')
    serializer = SubscriptionTierSerializer(tiers, many=True)
    return Response(serializer.data)


@extend_schema(
    responses={
        200: OpenApiResponse(description="Trial status retrieved successfully"),
        404: OpenApiResponse(description="User profile not found"),
    },
    summary="Get user trial status",
    description="Get current trial status including days left and effective subscription tier",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def trial_status_view(request):
    """Get user trial status"""
    try:
        profile = request.user.profile
        
        return Response({
            "is_trial_active": profile.is_trial_active,
            "trial_days_left": profile.days_left_in_trial(),
            "trial_expired": profile.is_trial_expired(),
            "has_paid_subscription": profile.has_paid_subscription(),
            "effective_tier": {
                "id": str(profile.get_effective_subscription_tier().id),
                "name": profile.get_effective_subscription_tier().name,
                "display_name": profile.get_effective_subscription_tier().display_name,
            } if profile.get_effective_subscription_tier() else None,
            "selected_tier": {
                "id": str(profile.subscription_tier.id),
                "name": profile.subscription_tier.name,
                "display_name": profile.subscription_tier.display_name,
            } if profile.subscription_tier else None
        })
        
    except Exception as e:
        logger.error(f"Error getting trial status: {str(e)}")
        return Response(
            {"error": "Failed to get trial status"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "subscription_tier_id": {"type": "string", "format": "uuid"}
            },
            "required": ["subscription_tier_id"]
        }
    },
    responses={
        200: OpenApiResponse(description="Trial started successfully"),
        400: OpenApiResponse(description="Invalid subscription tier or trial already active"),
    },
    summary="Start trial for a subscription tier",
    description="Start a 14-day trial for a paid subscription tier",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def start_trial_view(request):
    """Start trial for a subscription tier"""
    try:
        from apps.core.models.payment_models import SubscriptionTier
        
        subscription_tier_id = request.data.get("subscription_tier_id")
        if not subscription_tier_id:
            return Response(
                {"error": "subscription_tier_id is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            tier = SubscriptionTier.objects.get(id=subscription_tier_id, is_active=True)
        except SubscriptionTier.DoesNotExist:
            return Response(
                {"error": "Invalid subscription tier"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        profile = request.user.profile
        
        # Check if already on trial
        if profile.is_trial_active and not profile.is_trial_expired():
            return Response(
                {"error": "Trial already active"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if tier is paid
        if tier.price_monthly <= 0:
            return Response(
                {"error": "Cannot start trial for free tier"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update subscription tier and start trial
        profile.subscription_tier = tier
        profile.start_trial(trial_days=14)
        
        return Response({
            "message": "Trial started successfully",
            "trial_days_left": profile.days_left_in_trial(),
            "trial_end_date": profile.trial_end_date
        })
        
    except Exception as e:
        logger.error(f"Error starting trial: {str(e)}")
        return Response(
            {"error": "Failed to start trial"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    request=RegisterSerializer,
    responses={
        201: OpenApiResponse(description="User registered successfully. Email verification required."),
        400: OpenApiResponse(description="Validation error"),
    },
    summary="Register a new user",
    examples=[
        OpenApiExample(
            "User Registration with Subscription",
            description="Example registration with subscription tier selection",
            value={
                "username": "john_doe",
                "email": "john@example.com",
                "password": "SecurePass123!",
                "password_confirm": "SecurePass123!",
                "first_name": "John",
                "last_name": "Doe",
                "company_name": "My Company",
                "subscription_tier_id": "uuid-of-professional-tier"
            },
        )
    ],
)
@method_decorator(csrf_exempt, name="dispatch")
class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)
            return Response(
                {"user": UserSerializer(user).data, "token": token.key, "message": "User created successfully"},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@extend_schema(
    request=LoginSerializer,
    responses={
        200: OpenApiResponse(description="Login successful"),
        400: OpenApiResponse(description="Validation error"),
        401: OpenApiResponse(description="Invalid credentials or email not verified"),
    },
    summary="Login user",
)
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
@authentication_classes([])  # Explicitly disable authentication for this view
def login_view(request):
    """Function-based login view"""
    # FIRST THING - print that we reached this function
    print("LOGIN VIEW FUNCTION REACHED!")
    
    import logging
    logger = logging.getLogger(__name__)
    
    # Print to both console and logs (no emojis to avoid Unicode issues)
    print("=" * 50)
    print("LOGIN ENDPOINT CALLED")
    print("=" * 50)
    logger.info("LOGIN ENDPOINT CALLED")
    
    print(f"Request method: {request.method}")
    print(f"Request path: {request.path}")
    print(f"Request data: {request.data}")
    # Remove request.body access to avoid RawPostDataException
    print(f"Content-Type: {request.META.get('CONTENT_TYPE', 'Not provided')}")
    print(f"Request POST: {request.POST}")
    print(f"Request GET: {request.GET}")
    
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request data: {request.data}")
    logger.info(f"Content-Type: {request.META.get('CONTENT_TYPE', 'Not provided')}")
    
    # Check data keys
    if hasattr(request, 'data') and request.data:
        print(f"Data keys: {list(request.data.keys())}")
        print(f"Username: {request.data.get('username')}")
        print(f"Password provided: {'password' in request.data}")
        logger.info(f"Data keys: {list(request.data.keys())}")
        logger.info(f"Username: {request.data.get('username')}")
        logger.info(f"Password provided: {'password' in request.data}")
    else:
        print("No request.data found or empty")
        logger.error("No request.data found or empty")
    
    serializer = LoginSerializer(data=request.data)
    print(f"Serializer created with data: {serializer.initial_data}")
    logger.info(f"Serializer created with data: {serializer.initial_data}")
    
    if serializer.is_valid():
        print("Login serializer is valid")
        logger.info("Login serializer is valid")
        user = serializer.validated_data["user"]
        token, created = Token.objects.get_or_create(user=user)
        login(request, user)
        
        # Safely get or create user profile
        try:
            profile = user.profile
            profile_data = UserProfileSerializer(profile).data
        except Exception as e:
            print(f"Profile access error: {e}")
            logger.warning(f"Profile access error: {e}")
            # Create profile if it doesn't exist
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile_data = UserProfileSerializer(profile).data
            print(f"Profile {'created' if created else 'retrieved'}: {profile}")
            logger.info(f"Profile {'created' if created else 'retrieved'}: {profile}")
        
        print("Login successful, returning response")
        logger.info("Login successful, returning response")
        return Response(
            {
                "user": UserSerializer(user).data,
                "token": token.key,
                "profile": profile_data,
                "message": "Login successful",
            },
            status=status.HTTP_200_OK,
        )
    
    print(f"Login serializer validation failed: {serializer.errors}")
    print(f"Detailed login errors: {dict(serializer.errors)}")
    print("=" * 50)
    
    logger.error(f"Login serializer validation failed: {serializer.errors}")
    logger.error(f"Detailed login errors: {dict(serializer.errors)}")
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            request.user.auth_token.delete()
            logout(request)
            return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)
        except:
            return Response({"error": "Error logging out"}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    operation_id="update_profile",
    request=UserProfileSerializer,
    responses={200: UserProfileSerializer},
    summary="Update user profile",
    description="Update user profile including avatar upload",
    examples=[
        OpenApiExample(
            "Profile Update with Avatar",
            description="Example profile update with file upload",
            value={
                "company_name": "Keative",
                "subscription_tier": "premium",
                "time_format": "12h",
                "timezone": "UTC",
                "email_notifications": True,
                "slack_notifications": True,
            },
        )
    ],
)
class ProfileView(RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # Add this line

    def get_object(self):
        logger.info(f"ProfileView.get_object called for user: {self.request.user}")
        logger.info(f"User authenticated: {self.request.user.is_authenticated}")
        logger.info(f"User type: {type(self.request.user)}")

        if not self.request.user.is_authenticated:
            logger.error("User is not authenticated in get_object")
            raise Exception("User not authenticated")

        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        logger.info(f"Profile {'created' if created else 'retrieved'}: {profile}")
        return profile

    def get(self, request, *args, **kwargs):
        """Override get method to ensure proper authentication"""
        logger.info(f"ProfileView.get called")
        logger.info(f"Request user: {request.user}")
        logger.info(f"Request user authenticated: {request.user.is_authenticated}")
        logger.info(f"Auth header: {request.META.get('HTTP_AUTHORIZATION', 'Not provided')}")
        logger.info(f"Request META keys: {list(request.META.keys())}")

        # Manual authentication check
        auth = TokenAuthentication()
        try:
            user_auth_tuple = auth.authenticate(request)
            logger.info(f"Manual auth result: {user_auth_tuple}")
            if user_auth_tuple:
                user, token = user_auth_tuple
                logger.info(f"Manual auth successful: user={user.username}, token={token.key[:10]}...")
            else:
                logger.warning("Manual auth returned None")
        except Exception as e:
            logger.error(f"Manual auth error: {e}")

        try:
            profile = self.get_object()
            serializer = self.get_serializer(profile)
            logger.info(f"Profile serialized successfully: {serializer.data}")
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"ProfileView.get error: {e}")
            return Response({"error": f"Profile error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, *args, **kwargs):
        """Override put method for updates"""
        logger.info(f"ProfileView.put called for user: {request.user}")
        try:
            profile = self.get_object()
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                logger.info(f"Profile updated successfully: {serializer.data}")
                return Response(serializer.data)
            logger.warning(f"Profile update validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"ProfileView.put error: {e}")
            return Response({"error": f"Profile update error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SocialMediaAccountListView(ListCreateAPIView):
    serializer_class = SocialMediaAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return SocialMediaAccount.objects.none()
        return SocialMediaAccount.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        platform = serializer.validated_data.get("platform")
        username = serializer.validated_data.get("username")

        # Check if account already exists for this user
        existing_account = SocialMediaAccount.objects.filter(
            user=self.request.user, platform=platform, username=username
        ).first()

        if existing_account:
            from rest_framework import serializers as drf_serializers

            raise drf_serializers.ValidationError(
                {"non_field_errors": [f'You already have a {platform} account with username "{username}" connected.']}
            )

        serializer.save(user=self.request.user)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def remove_social_media_account(request, account_id):
    """Remove a connected social media account"""
    try:
        account = SocialMediaAccount.objects.get(id=account_id, user=request.user)
        platform = account.platform
        username = account.username
        
        # Also remove the corresponding SocialMediaAccount if it exists
        try:
            from apps.integrations.models import SocialMediaAccount, SocialMediaPlatform
            
            # Map platform names to the enum
            platform_mapping = {
                'twitter': SocialMediaPlatform.TWITTER,
                'Twitter/X': SocialMediaPlatform.TWITTER,
                'facebook': SocialMediaPlatform.FACEBOOK,
                'instagram': SocialMediaPlatform.INSTAGRAM,
                'linkedin': SocialMediaPlatform.LINKEDIN,
                'tiktok': SocialMediaPlatform.TIKTOK,
                'youtube': SocialMediaPlatform.YOUTUBE,
                'pinterest': SocialMediaPlatform.PINTEREST,
            }
            
            platform_enum = platform_mapping.get(platform.lower())
            if platform_enum:
                integrated_accounts = SocialMediaAccount.objects.filter(
                    user=request.user, 
                    platform=platform_enum,
                    username=username
                )
                deleted_count = integrated_accounts.count()
                integrated_accounts.delete()
                if deleted_count > 0:
                    logger.info(f"Also removed {deleted_count} SocialMediaAccount(s) for {platform} user {username}")
        except Exception as e:
            # Don't fail the whole operation if IntegratedAccount cleanup fails
            logger.warning(f"Failed to cleanup IntegratedAccount for {platform} user {username}: {e}")
        
        account.delete()

        return Response({"message": f"Successfully removed {platform} account '{username}'"}, status=status.HTTP_200_OK)

    except SocialMediaAccount.DoesNotExist:
        return Response(
            {"error": "Social media account not found or you don't have permission to delete it"},
            status=status.HTTP_404_NOT_FOUND,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def check_social_account_exists(request):
    """Check if a social media account already exists for the user"""
    platform = request.GET.get("platform")
    username = request.GET.get("username")

    if not platform or not username:
        return Response(
            {"error": "Both 'platform' and 'username' parameters are required"}, status=status.HTTP_400_BAD_REQUEST
        )

    existing_account = SocialMediaAccount.objects.filter(user=request.user, platform=platform, username=username).first()

    if existing_account:
        return Response(
            {
                "exists": True,
                "account_id": str(existing_account.id),
                "platform": existing_account.platform,
                "username": existing_account.username,
                "created_at": existing_account.created_at,
                "is_active": existing_account.is_active,
            }
        )
    else:
        return Response({"exists": False, "message": f"No {platform} account with username '{username}' found"})


class TeamMemberListView(ListCreateAPIView):
    serializer_class = TeamMemberSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TeamMember.objects.filter(team__owner=self.request.user)

    def perform_create(self, serializer):
        # Logic to invite team members
        email = self.request.data.get("email")
        team_id = self.request.data.get("team")

        # Get the team object
        try:
            team = Team.objects.get(id=team_id, owner=self.request.user)
        except Team.DoesNotExist:
            raise PermissionDenied("Team not found or you don't have permission.")

        try:
            user = User.objects.get(email=email)
            serializer.save(user=user, team=team)
        except User.DoesNotExist:
            # Send invitation email for non-existing users
            serializer.save(invited_email=email, team=team)
        except Exception as e:
            logger.error(f"Error in TeamMemberListView.perform_create: {e}")
            return Response({"error": "Error inviting team member"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def user_dashboard(request):
    """Dashboard data for authenticated user"""
    user = request.user
    profile = user.profile
    social_accounts = user.social_accounts.filter(is_active=True)
    team_members = user.team_memberships.filter(is_active=True)  # <-- FIXED LINE

    return Response(
        {
            "user": UserSerializer(user).data,
            "profile": UserProfileSerializer(profile).data,
            "social_accounts": SocialMediaAccountSerializer(social_accounts, many=True).data,
            "team_members_count": team_members.count(),
            "subscription": profile.subscription_tier.name if profile.subscription_tier else "free",
        }
    )


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def health_check(request):
    """Health check endpoint"""
    print("HEALTH CHECK ENDPOINT REACHED!")
    print(f"Request path: {request.path}")
    print(f"Request method: {request.method}")
    return Response({"status": "healthy", "message": "Social Media Manager API is running"})


@api_view(["GET", "POST"])
@permission_classes([permissions.AllowAny])
def ultra_simple_test(request):
    """Ultra simple test endpoint to verify Django is working"""
    print("ULTRA SIMPLE TEST ENDPOINT REACHED!")
    print(f"Request path: {request.path}")
    print(f"Request method: {request.method}")
    print(f"Request user: {request.user}")
    print(f"Request authenticated: {request.user.is_authenticated}")
    return Response({"message": "Ultra simple test working", "method": request.method, "authenticated": request.user.is_authenticated})


# @csrf_exempt
# @api_view(["POST"])
# @permission_classes([permissions.AllowAny])
# def register(request):
#     serializer = UserRegistrationSerializer(data=request.data)
#     if serializer.is_valid():
#         user = serializer.save()
#         user.is_active = False  # Deactivate until email verification
#         user.save()

#         # Create email verification token
#         verification_token = EmailVerificationToken.objects.create(user=user)

#         # Send verification email
#         send_verification_email(user, verification_token.token)

#     return Response(
#         {
#             "message": "Registration successful. Please check your email to verify your account.",
#             "user_id": user.id,
#             "username": user.username,
#             "profile_uuid": str(user.profile.id),
#         },
#         status=status.HTTP_201_CREATED,
#     )


@csrf_exempt
@extend_schema(
    request=UserRegistrationSerializer,
    responses={
        201: OpenApiResponse(description="Registration successful. Please check your email to verify your account."),
        400: OpenApiResponse(description="Validation error"),
    },
    summary="Register a new user (email verification)",
)
@csrf_exempt
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
@authentication_classes([])  # Explicitly disable authentication for this view
def register(request):
    # FIRST THING - print that we reached this function
    print("REGISTER VIEW FUNCTION REACHED!")
    
    import logging
    logger = logging.getLogger(__name__)
    
    # Print to both console and logs
    print("=" * 50)
    print("REGISTER ENDPOINT CALLED")
    print("=" * 50)
    logger.info("REGISTER ENDPOINT CALLED")
    
    print(f"Request method: {request.method}")
    print(f"Request path: {request.path}")
    print(f"Request data: {request.data}")
    
    # Avoid reading request.body after request.data
    # print(f"Request body: {request.body}") 
    
    print(f"Content-Type: {request.META.get('CONTENT_TYPE', 'Not provided')}")
    print(f"Request POST: {request.POST}")
    print(f"Request GET: {request.GET}")
    
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request data: {request.data}")
    logger.info(f"Content-Type: {request.META.get('CONTENT_TYPE', 'Not provided')}")
    
    # Check data keys
    if hasattr(request, 'data') and request.data:
        print(f"Data keys: {list(request.data.keys())}")
        print(f"Email: {request.data.get('email')}")
        print(f"Username: {request.data.get('username')}")
        print(f"Password provided: {'password' in request.data}")
        print(f"Password2 provided: {'password2' in request.data}")
        print(f"First name: {request.data.get('first_name')}")
        print(f"Last name: {request.data.get('last_name')}")
        print(f"Company name: {request.data.get('company_name')}")
        print(f"Role: {request.data.get('role')}")
        
        logger.info(f"Data keys: {list(request.data.keys())}")
        logger.info(f"Email: {request.data.get('email')}")
        logger.info(f"Username: {request.data.get('username')}")
        logger.info(f"Password provided: {'password' in request.data}")
        logger.info(f"Password2 provided: {'password2' in request.data}")
        logger.info(f"Company name: {request.data.get('company_name')}")
        logger.info(f"Role: {request.data.get('role')}")
    
    serializer = UserRegistrationSerializer(data=request.data)
    print(f"🎯 VIEWS.PY: Using serializer class: {type(serializer).__name__}")
    print(f"🎯 VIEWS.PY: Serializer module: {type(serializer).__module__}")
    print(f"Serializer created with data: {serializer.initial_data}")
    logger.info(f"Serializer created with data: {serializer.initial_data}")
    
    if serializer.is_valid():
        print("Serializer is valid, creating user...")
        logger.info("Serializer is valid, creating user...")
        user = serializer.save()
        user.is_active = False  # Deactivate until email verification
        user.save()
        # Create email verification token
        verification_token = EmailVerificationToken.objects.create(user=user)
        # Send verification email
        send_verification_email(user, verification_token.token)
        
        # Safely get or create user profile
        try:
            profile = user.profile
            profile_uuid = str(profile.id)
            
            # Get subscription information
            subscription_info = {}
            if hasattr(user, 'subscription') and user.subscription:
                subscription_info = {
                    'subscription_id': str(user.subscription.id),
                    'tier_name': user.subscription.tier.display_name,
                    'status': user.subscription.status,
                    'is_trial': user.subscription.status == 'trialing',
                    'trial_end_date': user.subscription.trial_end_date.isoformat() if user.subscription.trial_end_date else None,
                }
            
        except Exception as e:
            print(f"Profile access error during registration: {e}")
            logger.warning(f"Profile access error during registration: {e}")
            # Create profile if it doesn't exist
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile_uuid = str(profile.id)
            subscription_info = {}
            print(f"Profile {'created' if created else 'retrieved'} during registration: {profile}")
            logger.info(f"Profile {'created' if created else 'retrieved'} during registration: {profile}")
        
        print("Registration successful, returning response")
        logger.info("Registration successful, returning response")
        
        response_data = {
            "message": "Registration successful. Please check your email to verify your account.",
            "user_id": user.id,
            "username": user.username,
            "profile_uuid": profile_uuid,
        }
        
        # Add subscription info if available
        if subscription_info:
            response_data["subscription"] = subscription_info
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    print(f"Serializer validation failed: {serializer.errors}")
    print(f"Detailed errors: {dict(serializer.errors)}")
    print(f"Serializer field errors: {serializer.errors}")
    print("=" * 50)
    
    logger.error(f"Serializer validation failed: {serializer.errors}")
    logger.error(f"Detailed errors: {dict(serializer.errors)}")
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
@authentication_classes([])  # Disable auth to avoid 401s on email verification link
def verify_email(request, token):
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"Email verification attempt for token: {token}")
    
    try:
        verification_token = EmailVerificationToken.objects.get(token=token)
        logger.info(f"Token found for user: {verification_token.user.username}")
        logger.info(f"Token is_used: {verification_token.is_used}")
        logger.info(f"User is_active: {verification_token.user.is_active}")

        if verification_token.is_used:
            # Check if user is already active (successful previous verification)
            if verification_token.user.is_active:
                logger.info("Token already used but user is active - returning success")
                return Response(
                    {
                        "message": "Email already verified. You can log in now.",
                        "username": verification_token.user.username,
                        "already_verified": True
                    }, 
                    status=status.HTTP_200_OK
                )
            else:
                logger.warning("Token already used but user not active")
                return Response(
                    {"error": "This verification link has already been used"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

        if verification_token.is_expired():
            logger.warning("Token has expired")
            return Response(
                {"error": "This verification link has expired"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Activate user
        user = verification_token.user
        user.is_active = True
        user.save()

        # Mark token as used
        verification_token.is_used = True
        verification_token.save()

        logger.info(f"Email verification successful for user: {user.username}")
        return Response(
            {
                "message": "Email verified successfully. You can now log in.", 
                "username": user.username,
                "verified": True
            },
            status=status.HTTP_200_OK
        )

    except EmailVerificationToken.DoesNotExist:
        logger.error(f"Invalid verification token: {token}")
        return Response(
            {"error": "Invalid verification token"}, 
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def resend_verification_email(request):
    email = request.data.get("email")

    if not email:
        return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email=email)

        if user.is_active:
            return Response({"error": "Email is already verified"}, status=status.HTTP_400_BAD_REQUEST)

        # Delete old unused tokens
        EmailVerificationToken.objects.filter(user=user, is_used=False).delete()

        # Create new verification token
        verification_token = EmailVerificationToken.objects.create(user=user)

        # Send verification email
        send_verification_email(user, verification_token.token)

        return Response({"message": "Verification email sent successfully"})

    except User.DoesNotExist:
        return Response({"error": "User with this email does not exist"}, status=status.HTTP_404_NOT_FOUND)


def send_verification_email(user, token):
    subject = "Verify your email address - Social Media Manager"
    verification_url = f"{settings.FRONTEND_URL}/verify-email/{token}"

    html_message = render_to_string(
        "emails/email_verification.html",
        {
            "user": user,
            "verification_url": verification_url,
        },
    )
    plain_message = strip_tags(html_message)

    send_mail(
        subject,
        plain_message,
        settings.EMAIL_HOST_USER,
        [user.email],
        html_message=html_message,
    )


@api_view(["GET"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def debug_auth(request):
    """Debug endpoint to check authentication"""
    logger.info(f"debug_auth called")
    logger.info(f"Request user: {request.user}")
    logger.info(f"User authenticated: {request.user.is_authenticated}")
    logger.info(f"Auth header: {request.META.get('HTTP_AUTHORIZATION', 'Not provided')}")

    return Response(
        {
            "authenticated": request.user.is_authenticated,
            "user": request.user.username if request.user.is_authenticated else None,
            "user_id": request.user.id if request.user.is_authenticated else None,
            "auth_header": request.META.get("HTTP_AUTHORIZATION", "Not provided"),
            "user_active": request.user.is_active if request.user.is_authenticated else None,
        }
    )


@api_view(["GET", "POST"])
@permission_classes([permissions.AllowAny])
def simple_test(request):
    """Simple test endpoint"""
    print(f"🟢 SIMPLE TEST ENDPOINT CALLED! Method: {request.method}")
    print(f"🟢 Request data: {request.data}")
    return Response({"message": "Test endpoint working", "method": request.method})


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def debug_auth_open(request):
    """Open debug endpoint to check what's happening with auth"""
    print("🔍 DEBUG_AUTH_OPEN endpoint called!")
    auth_header = request.META.get("HTTP_AUTHORIZATION", "Not provided")

    # Try to manually authenticate
    from rest_framework.authentication import TokenAuthentication

    auth = TokenAuthentication()
    try:
        user_auth_tuple = auth.authenticate(request)
        if user_auth_tuple:
            user, token = user_auth_tuple
            auth_result = f"Manual auth successful: {user.username}"
        else:
            auth_result = "Manual auth returned None"
    except Exception as e:
        auth_result = f"Manual auth error: {str(e)}"

    return Response(
        {
            "auth_header": auth_header,
            "request_user": str(request.user),
            "request_user_authenticated": request.user.is_authenticated,
            "manual_auth_result": auth_result,
            "settings_auth_classes": settings.REST_FRAMEWORK.get("DEFAULT_AUTHENTICATION_CLASSES", "Not found"),
        }
    )


class TeamMemberInviteView(generics.CreateAPIView):
    serializer_class = TeamMemberSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        invited_email = self.request.data.get("invited_email")
        team_id = self.request.data.get("team_id") or self.request.data.get("team")

        # Validate required fields
        if not team_id:
            raise DRFValidationError({"team": "Team ID is required."})
        if not invited_email:
            raise DRFValidationError({"invited_email": "Invited email is required."})

        # Get team with proper error handling
        team = get_object_or_404(Team, id=team_id)

        # Check if user has permission to invite (owner or admin)
        member = TeamMember.objects.filter(team=team, user=self.request.user).first()
        if not member or member.role not in ["owner", "admin"]:
            raise PermissionDenied("Only team owner or admin can invite members.")

        # Check if user is already a member or invited
        existing_member = TeamMember.objects.filter(team=team, invited_email=invited_email).first()
        if existing_member:
            if existing_member.is_active:
                raise DRFValidationError({"invited_email": "This email is already an active member of the team."})
            else:
                raise DRFValidationError({"invited_email": "This email has already been invited to the team."})

        serializer.save(team=team, invited_email=invited_email, is_active=False)

        # Send invitation email
        send_team_invitation_email.delay(
            team_id=str(team.id),
            invited_email=invited_email,
            inviter_name=self.request.user.get_full_name() or self.request.user.username,
        )


class TeamListCreateView(generics.ListCreateAPIView):
    serializer_class = TeamSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Return teams where user is a member
        return Team.objects.filter(members__user=self.request.user)

    def perform_create(self, serializer):
        # Create team and add creator as owner
        team = serializer.save(owner=self.request.user)
        TeamMember.objects.create(team=team, user=self.request.user, role="owner", is_active=True)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def teams_for_invitation(request):
    """Get teams where user can invite members (owner or admin role)"""
    user_teams = Team.objects.filter(
        members__user=request.user, members__role__in=["owner", "admin"], members__is_active=True
    ).distinct()

    teams_data = []
    for team in user_teams:
        member = TeamMember.objects.filter(team=team, user=request.user).first()
        teams_data.append(
            {"id": team.id, "name": team.name, "your_role": member.role if member else None, "created_at": team.created_at}
        )

    return Response({"teams": teams_data, "message": f"Found {len(teams_data)} teams where you can invite members"})


@api_view(["POST", "GET"])
@permission_classes([IsAuthenticated])
def user_time_format_setting(request):
    """Manage user time format preference"""
    try:
        # Get or create user profile
        profile, created = UserProfile.objects.get_or_create(user=request.user)

        if request.method == "GET":
            return Response(
                {"time_format": getattr(profile, "time_format", "12h"), "timezone": getattr(profile, "timezone", "UTC")}
            )

        elif request.method == "POST":
            time_format = request.data.get("time_format", "12h")  # '12h' or '24h'
            timezone_pref = request.data.get("timezone", "UTC")

            if time_format not in ["12h", "24h"]:
                return Response({"error": "Invalid time format. Use '12h' or '24h'"}, status=status.HTTP_400_BAD_REQUEST)

            profile.time_format = time_format
            profile.timezone = timezone_pref
            profile.save()

            return Response(
                {"message": "Time format updated successfully", "time_format": time_format, "timezone": timezone_pref}
            )

    except Exception as e:
        logger.error(f"Error managing time format setting: {str(e)}")
        return Response({"error": "Failed to manage time format setting"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def oauth_callback(request):
    """Handle OAuth callbacks from social media platforms like X/Twitter"""
    try:
        code = request.GET.get("code")
        state = request.GET.get("state")
        error = request.GET.get("error")
        
        if error:
            logger.error(f"OAuth error: {error}")
            return Response({"error": f"OAuth error: {error}"}, status=status.HTTP_400_BAD_REQUEST)
        
        if not code:
            return Response({"error": "Missing authorization code"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Here you would handle the OAuth flow for X/Twitter
        # For now, return a success response
        logger.info(f"X/Twitter OAuth callback received with code: {code}")
        
        return Response({
            "message": "X/Twitter OAuth callback received successfully",
            "code": code,
            "state": state
        })
        
    except Exception as e:
        logger.error(f"Error handling OAuth callback: {str(e)}")
        return Response({"error": "Failed to handle OAuth callback"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request):
    """Change user password"""
    try:
        user = request.user
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        
        if not current_password or not new_password:
            return Response(
                {"error": "Both current_password and new_password are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check current password
        if not user.check_password(current_password):
            return Response(
                {"error": "Current password is incorrect"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate new password
        from django.contrib.auth.password_validation import validate_password
        try:
            validate_password(new_password, user)
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Set new password
        user.set_password(new_password)
        user.save()
        
        logger.info(f"Password changed successfully for user: {user.username}")
        return Response({"message": "Password changed successfully"})
        
    except Exception as e:
        logger.error(f"Error changing password: {str(e)}")
        return Response(
            {"error": "Failed to change password"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_stats(request):
    """Get user statistics for navbar display"""
    try:
        user = request.user
        
        # Get post counts by status
        from apps.posts.models import Post
        active_posts = Post.objects.filter(user=user, status='published').count()
        scheduled_posts = Post.objects.filter(user=user, status='scheduled').count()
        
        # Get notification count
        from apps.notifications.models import Notification
        unread_notifications = Notification.objects.filter(user=user, is_read=False).count()
        
        return Response({
            "active_posts": active_posts,
            "scheduled_posts": scheduled_posts,
            "unread_notifications": unread_notifications
        })
        
    except Exception as e:
        logger.error(f"Error getting user stats: {str(e)}")
        return Response(
            {"error": "Failed to get user stats"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_notification_settings(request):
    """Update user notification preferences"""
    try:
        user = request.user
        profile = user.profile
        
        email_notifications = request.data.get('email_notifications')
        slack_notifications = request.data.get('slack_notifications')
        
        if email_notifications is not None:
            profile.email_notifications = email_notifications
        
        if slack_notifications is not None:
            profile.slack_notifications = slack_notifications
        
        profile.save()
        
        return Response({
            "message": "Notification settings updated successfully",
            "email_notifications": profile.email_notifications,
            "slack_notifications": profile.slack_notifications
        })
        
    except Exception as e:
        logger.error(f"Error updating notification settings: {str(e)}")
        return Response(
            {"error": "Failed to update notification settings"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_account_overview(request):
    """Get account overview data for settings page"""
    try:
        user = request.user
        profile = user.profile
        
        # Get social account counts
        social_accounts_count = user.social_accounts.count()
        
        # Get post counts
        from apps.posts.models import Post
        total_posts = Post.objects.filter(user=user).count()
        
        # Get team membership
        team_memberships = user.team_memberships.count()
        
        return Response({
            "account_created": user.date_joined,
            "last_login": user.last_login,
            "subscription_type": profile.subscription_tier.name if profile.subscription_tier else "free",
            "social_accounts_count": social_accounts_count,
            "total_posts": total_posts,
            "team_memberships": team_memberships,
            "storage_used": "1.2 GB",  # Placeholder - implement actual storage calculation
            "api_calls_this_month": 1250  # Placeholder - implement actual API usage tracking
        })
        
    except Exception as e:
        logger.error(f"Error getting account overview: {str(e)}")
        return Response(
            {"error": "Failed to get account overview"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Plan Selection Views for First-Time Users

@extend_schema(
    summary="Get available subscription tiers for plan selection",
    description="Returns all available subscription tiers for first-time users to choose from"
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def plan_selection_tiers(request):
    """Get available subscription tiers for first-time users"""
    from apps.core.models.payment_models import SubscriptionTier
    from apps.core.serializers import SubscriptionTierSerializer
    
    try:
        tiers = SubscriptionTier.objects.filter(is_active=True).order_by('price_monthly')
        serializer = SubscriptionTierSerializer(tiers, many=True)
        
        return Response({
            'tiers': serializer.data,
            'current_user': request.user.username,
            'is_first_login': not request.session.get('setup_completed', False)
        })
        
    except Exception as e:
        logger.error(f"Error getting subscription tiers: {str(e)}")
        return Response(
            {"error": "Failed to get subscription tiers"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="Complete first-time user setup",
    description="Handle user choice to upgrade to a paid plan or skip and continue with free tier",
    request={
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["upgrade", "skip"]},
            "tier_id": {"type": "string", "description": "Required if action is 'upgrade'"}
        }
    }
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def complete_setup(request):
    """Complete first-time user setup - upgrade or skip"""
    from apps.core.models.payment_models import SubscriptionTier, UserSubscription
    
    try:
        action = request.data.get('action')
        
        if action == 'skip':
            # Mark setup as completed, keep free tier
            request.session['setup_completed'] = True
            
            # Update user profile if exists
            if hasattr(request.user, 'profile'):
                request.user.profile.setup_completed = True
                request.user.profile.save()
            
            return Response({
                'message': 'Setup completed with free plan',
                'redirect_url': '/dashboard'
            })
            
        elif action == 'upgrade':
            tier_id = request.data.get('tier_id')
            
            if not tier_id:
                return Response(
                    {"error": "tier_id is required for upgrade action"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                selected_tier = SubscriptionTier.objects.get(id=tier_id, is_active=True)
                
                # Update user's subscription to selected tier
                user_subscription, created = UserSubscription.objects.get_or_create(
                    user=request.user,
                    defaults={
                        'tier': selected_tier,
                        'status': 'pending',  # Will be activated after payment
                        'billing_period': 'monthly'
                    }
                )
                
                if not created:
                    user_subscription.tier = selected_tier
                    user_subscription.status = 'pending'
                    user_subscription.save()
                
                # Mark setup as completed
                request.session['setup_completed'] = True
                
                if hasattr(request.user, 'profile'):
                    request.user.profile.setup_completed = True
                    request.user.profile.save()
                
                return Response({
                    'message': f'Plan selected: {selected_tier.display_name}',
                    'tier': selected_tier.display_name,
                    'redirect_url': '/dashboard/billing',
                    'requires_payment': selected_tier.price_monthly > 0
                })
                
            except SubscriptionTier.DoesNotExist:
                return Response(
                    {"error": "Invalid subscription tier"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            return Response(
                {"error": "Invalid action. Must be 'upgrade' or 'skip'"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except Exception as e:
        logger.error(f"Error completing setup: {str(e)}")
        return Response(
            {"error": "Failed to complete setup"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Password Reset Views
@extend_schema(
    request=ForgotPasswordSerializer,
    responses={
        200: OpenApiResponse(description="Password reset email sent if account exists"),
        400: OpenApiResponse(description="Invalid email format"),
    },
    summary="Request password reset email",
    description="Send a password reset email to the provided email address if the account exists"
)
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def forgot_password(request):
    """Request password reset email"""
    serializer = ForgotPasswordSerializer(data=request.data)
    
    if serializer.is_valid():
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email=email)
            
            # Only send reset email if user is active
            if user.is_active:
                # Delete any existing unused password reset tokens for this user
                PasswordResetToken.objects.filter(user=user, is_used=False).delete()
                
                # Create new password reset token
                reset_token = PasswordResetToken.objects.create(user=user)
                
                # Send password reset email
                send_password_reset_email(user, reset_token.token)
                
                logger.info(f"Password reset email sent to {email}")
            else:
                logger.warning(f"Password reset requested for inactive user: {email}")
        
        except User.DoesNotExist:
            # Log but don't reveal that user doesn't exist
            logger.warning(f"Password reset requested for non-existent email: {email}")
        
        # Always return success to prevent email enumeration
        return Response({
            "message": "If an account with this email exists, you will receive a password reset email shortly."
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    request=ResetPasswordSerializer,
    responses={
        200: OpenApiResponse(description="Password reset successful"),
        400: OpenApiResponse(description="Invalid token or validation error"),
    },
    summary="Reset password with token",
    description="Reset password using the token received via email"
)
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def reset_password(request):
    """Reset password with token"""
    serializer = ResetPasswordSerializer(data=request.data)
    
    if serializer.is_valid():
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']
        
        try:
            reset_token = PasswordResetToken.objects.get(token=token)
            
            if reset_token.is_used:
                return Response(
                    {"error": "This password reset link has already been used"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if reset_token.is_expired():
                return Response(
                    {"error": "This password reset link has expired"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Reset the password
            user = reset_token.user
            user.set_password(new_password)
            user.save()
            
            # Mark token as used
            reset_token.is_used = True
            reset_token.save()
            
            logger.info(f"Password reset successful for user: {user.username}")
            
            return Response({
                "message": "Password has been reset successfully. You can now log in with your new password."
            })
        
        except PasswordResetToken.DoesNotExist:
            return Response(
                {"error": "Invalid password reset token"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    responses={
        200: OpenApiResponse(description="Token is valid"),
        400: OpenApiResponse(description="Token is invalid or expired"),
    },
    summary="Validate password reset token",
    description="Check if a password reset token is valid and not expired"
)
@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def validate_reset_token(request, token):
    """Validate password reset token"""
    try:
        reset_token = PasswordResetToken.objects.get(token=token)
        
        if reset_token.is_used:
            return Response(
                {"error": "This password reset link has already been used"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if reset_token.is_expired():
            return Response(
                {"error": "This password reset link has expired"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({
            "message": "Token is valid",
            "email": reset_token.user.email,
            "username": reset_token.user.username
        })
    
    except PasswordResetToken.DoesNotExist:
        return Response(
            {"error": "Invalid password reset token"}, 
            status=status.HTTP_400_BAD_REQUEST
        )


def send_password_reset_email(user, token):
    """Send password reset email"""
    subject = "Reset your password - Social Media Manager"
    reset_url = f"{settings.FRONTEND_URL}/reset-password/{token}"
    
    context = {
        "user": user,
        "reset_url": reset_url,
        "user_name": user.get_full_name() or user.username,
    }
    
    try:
        html_message = render_to_string("emails/password_reset.html", context)
    except:
        html_message = None
    
    plain_message = f"""
Hi {context['user_name']},

You requested to reset your password for your Social Media Manager account.

Click the link below to reset your password:
{reset_url}

This link will expire in 1 hour.

If you didn't request this password reset, please ignore this email.

Best regards,
The Social Media Manager Team
    """.strip()
    
    send_mail(
        subject,
        plain_message,
        settings.EMAIL_HOST_USER,
        [user.email],
        html_message=html_message,
    )
