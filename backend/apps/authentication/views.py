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

from .models import EmailVerificationToken, SocialMediaAccount, Team, TeamMember, UserProfile
from .serializers import (
    LoginSerializer,
    RegisterSerializer,
    SocialMediaAccountSerializer,
    TeamMemberSerializer,
    TeamSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)
from .tasks import send_team_invitation_email

# Set up logger
logger = logging.getLogger(__name__)


@extend_schema(
    request=RegisterSerializer,
    responses={
        201: OpenApiResponse(description="User registered successfully. Email verification required."),
        400: OpenApiResponse(description="Validation error"),
    },
    summary="Register a new user",
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
def login_view(request):
    """Function-based login view"""
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data["user"]
        token, created = Token.objects.get_or_create(user=user)
        login(request, user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "token": token.key,
                "profile": UserProfileSerializer(user.profile).data,
                "message": "Login successful",
            },
            status=status.HTTP_200_OK,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
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
                "subscription_type": "premium",
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

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return SocialMediaAccount.objects.none()
        return SocialMediaAccount.objects.filter(user=self.request.user)

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
            "subscription": profile.subscription_type,
        }
    )


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def health_check(request):
    """Health check endpoint"""
    return Response({"status": "healthy", "message": "Social Media Manager API is running"})


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
def register(request):
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        user.is_active = False  # Deactivate until email verification
        user.save()
        # Create email verification token
        verification_token = EmailVerificationToken.objects.create(user=user)
        # Send verification email
        send_verification_email(user, verification_token.token)
        return Response(
            {
                "message": "Registration successful. Please check your email to verify your account.",
                "user_id": user.id,
                "username": user.username,
                "profile_uuid": str(user.profile.id),
            },
            status=status.HTTP_201_CREATED,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def verify_email(request, token):
    try:
        verification_token = EmailVerificationToken.objects.get(token=token)

        if verification_token.is_used:
            return Response({"error": "This verification link has already been used"}, status=status.HTTP_400_BAD_REQUEST)

        if verification_token.is_expired():
            return Response({"error": "This verification link has expired"}, status=status.HTTP_400_BAD_REQUEST)

        # Activate user
        user = verification_token.user
        user.is_active = True
        user.save()

        # Mark token as used
        verification_token.is_used = True
        verification_token.save()

        return Response({"message": "Email verified successfully. You can now log in.", "username": user.username})

    except EmailVerificationToken.DoesNotExist:
        return Response({"error": "Invalid verification token"}, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
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


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def debug_auth_open(request):
    """Open debug endpoint to check what's happening with auth"""
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
