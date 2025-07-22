from django.urls import path

from .views import debug_auth_open  # Add this
from .views import (
    LogoutView,
    ProfileView,
    SocialMediaAccountListView,
    TeamMemberListView,
    TeamMemberInviteView,  # Add this
    debug_auth,
    health_check,
    login_user,
    register,
    resend_verification_email,
    user_dashboard,
    verify_email,
)

urlpatterns = [
    path("register/", register, name="register"),
    path("login/", login_user, name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("debug-auth/", debug_auth, name="debug-auth"),
    path("debug-auth-open/", debug_auth_open, name="debug-auth-open"),  # Add this
    path("social-accounts/", SocialMediaAccountListView.as_view(), name="social-accounts"),
    path("team-members/", TeamMemberListView.as_view(), name="team-members"),
    path("dashboard/", user_dashboard, name="dashboard"),
    path("health/", health_check, name="health"),
    path("verify-email/<str:token>/", verify_email, name="verify_email"),
    path("resend-verification/", resend_verification_email, name="resend_verification"),
]

urlpatterns += [
    path("team/invite/", TeamMemberInviteView.as_view(), name="team-invite"),  # Add this
]
