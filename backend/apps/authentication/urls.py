from django.urls import path
from .views import (
    RegisterView, LoginView, LogoutView, ProfileView,
    SocialMediaAccountListView, TeamMemberListView,
    user_dashboard, health_check, register, login,
    verify_email, resend_verification_email
)

urlpatterns = [
    path('register/', register, name='register'),
    path('login/', login, name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('social-accounts/', SocialMediaAccountListView.as_view(), name='social-accounts'),
    path('team-members/', TeamMemberListView.as_view(), name='team-members'),
    path('dashboard/', user_dashboard, name='dashboard'),
    path('health/', health_check, name='health'),
    path('verify-email/<str:token>/', verify_email, name='verify_email'),
    path('resend-verification/', resend_verification_email, name='resend_verification'),
]
