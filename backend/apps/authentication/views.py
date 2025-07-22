from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.html import strip_tags
from django.views.decorators.csrf import csrf_exempt

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import EmailVerificationToken, SocialMediaAccount, TeamMember, UserProfile
from .serializers import (
    LoginSerializer,
    RegisterSerializer,
    SocialMediaAccountSerializer,
    TeamMemberSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)


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


@extend_schema(
    request=LoginSerializer,
    responses={
        200: OpenApiResponse(description="Login successful"),
        400: OpenApiResponse(description="Validation error"),
        401: OpenApiResponse(description="Invalid credentials or email not verified"),
    },
    summary="Login user",
)
@method_decorator(csrf_exempt, name="dispatch")
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
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


class ProfileView(RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer

    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile


class SocialMediaAccountListView(ListCreateAPIView):
    serializer_class = SocialMediaAccountSerializer

    def get_queryset(self):
        return SocialMediaAccount.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TeamMemberListView(ListCreateAPIView):
    serializer_class = TeamMemberSerializer

    def get_queryset(self):
        return TeamMember.objects.filter(team_owner=self.request.user)

    def perform_create(self, serializer):
        # Logic to invite team members
        email = self.request.data.get("email")
        try:
            user = User.objects.get(email=email)
            serializer.save(user=user, team_owner=self.request.user)
        except User.DoesNotExist:
            # Send invitation email
            pass


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def user_dashboard(request):
    """Dashboard data for authenticated user"""
    user = request.user
    profile = user.profile
    social_accounts = user.social_accounts.filter(is_active=True)
    team_members = user.team_members.filter(is_active=True)

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


@csrf_exempt
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def login_user(request):
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
