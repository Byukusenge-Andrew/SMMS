from django.urls import path

from .views import ProfileView, UserView
from .views import TeamMemberInviteView
from .views import login_view
from .views import teams_for_invitation
from .views import user_time_format_setting
from .views import oauth_callback
from .views import subscription_tiers_view
from .views import trial_status_view, start_trial_view
from .views import change_password, get_user_stats, update_notification_settings, get_account_overview, plan_selection_tiers, complete_setup
from .views import forgot_password, reset_password, validate_reset_token
from .views import (
    LogoutView,
    SocialMediaAccountListView,
    TeamListCreateView,
    TeamMemberListView,
    check_social_account_exists,
    health_check,
    register,
    remove_social_media_account,
    resend_verification_email,
    user_dashboard,
    verify_email,
)

urlpatterns = [
    path("subscription-tiers/", subscription_tiers_view, name="subscription-tiers"),
    path("register/", register, name="register"),
    path("login/", login_view, name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("user/", UserView.as_view(), name="user"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("social-accounts/", SocialMediaAccountListView.as_view(), name="social-accounts"),
    path("social-accounts/check/", check_social_account_exists, name="check-social-account"),
    path("social-accounts/<uuid:account_id>/remove/", remove_social_media_account, name="remove-social-account"),
    path("team-members/", TeamMemberListView.as_view(), name="team-members"),
    path("dashboard/", user_dashboard, name="dashboard"),
    path("health/", health_check, name="health"),
    path("verify-email/<str:token>/", verify_email, name="verify_email"),
    path("resend-verification/", resend_verification_email, name="resend_verification"),
    # Password reset endpoints
    path("forgot-password/", forgot_password, name="forgot_password"),
    path("reset-password/", reset_password, name="reset_password"),
    path("validate-reset-token/<str:token>/", validate_reset_token, name="validate_reset_token"),
    # Settings endpoints
    path("settings/time-format/", user_time_format_setting, name="time-format-setting"),
    path("settings/password/", change_password, name="change-password"),
    path("settings/notifications/", update_notification_settings, name="update-notifications"),
    path("settings/overview/", get_account_overview, name="account-overview"),
    path("stats/", get_user_stats, name="user-stats"),
    # OAuth callbacks
    path("x/login/callback/", oauth_callback, name="x-oauth-callback"),
    
    # First-time user plan selection
    path("setup/plan-selection/", plan_selection_tiers, name="plan_selection"),
    path("setup/complete/", complete_setup, name="complete_setup"),
    
    # Trial management
    path("trial/status/", trial_status_view, name="trial-status"),
    path("trial/start/", start_trial_view, name="start-trial"),
]

urlpatterns += [
    path("team/invite/", TeamMemberInviteView.as_view(), name="team-invite"),
    path("teams/", TeamListCreateView.as_view(), name="teams"),
    path("teams/for-invitation/", teams_for_invitation, name="teams-for-invitation"),
]
