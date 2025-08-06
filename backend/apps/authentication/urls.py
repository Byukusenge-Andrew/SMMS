from django.urls import path

from .views import ProfileView  # Add these imports
from .views import TeamMemberInviteView  # Add this
from .views import debug_auth_open  # Add this
from .views import login_view  # Import the function instead
from .views import simple_test  # Add this import
from .views import teams_for_invitation  # Add this import
from .views import user_time_format_setting  # Add this import
from .views import (
    LogoutView,
    SocialMediaAccountListView,
    TeamListCreateView,
    TeamMemberListView,
    check_social_account_exists,
    debug_auth,
    health_check,
    register,
    remove_social_media_account,
    resend_verification_email,
    user_dashboard,
    verify_email,
)

urlpatterns = [
    path("register/", register, name="register"),
    path("login/", login_view, name="login"),  # Use function directly, no .as_view()
    path("logout/", LogoutView.as_view(), name="logout"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("debug-auth/", debug_auth, name="debug-auth"),
    path("debug-auth-open/", debug_auth_open, name="debug-auth-open"),
    path("test-endpoint/", debug_auth_open, name="test-endpoint"),  # Simple test endpoint
    path("simple-test/", simple_test, name="simple-test"),  # Even simpler test
    path("social-accounts/", SocialMediaAccountListView.as_view(), name="social-accounts"),
    path("social-accounts/check/", check_social_account_exists, name="check-social-account"),
    path("social-accounts/<uuid:account_id>/remove/", remove_social_media_account, name="remove-social-account"),
    path("team-members/", TeamMemberListView.as_view(), name="team-members"),
    path("dashboard/", user_dashboard, name="dashboard"),
    path("health/", health_check, name="health"),
    path("verify-email/<str:token>/", verify_email, name="verify_email"),
    path("resend-verification/", resend_verification_email, name="resend_verification"),
    # Settings endpoints
    path("settings/time-format/", user_time_format_setting, name="time-format-setting"),
]

urlpatterns += [
    path("team/invite/", TeamMemberInviteView.as_view(), name="team-invite"),
    path("teams/", TeamListCreateView.as_view(), name="teams"),
    path("teams/for-invitation/", teams_for_invitation, name="teams-for-invitation"),
]
