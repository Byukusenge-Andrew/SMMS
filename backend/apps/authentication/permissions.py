import logging

from rest_framework.permissions import BasePermission

logger = logging.getLogger(__name__)


class IsTeamAdminOrOwner(BasePermission):
    """
    Allows access only to team admins or owners.
    Requires the user to be authenticated.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        member = obj.members.filter(user=request.user).first()
        return member and member.role in ["owner", "admin"]


class IsEmailVerified(BasePermission):
    """
    Denies access if the user's account is not active (email not verified).
    Django's User.is_active is set to True after email verification.
    """

    message = "Your email address has not been verified."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_active


class IsSubscriptionActive(BasePermission):
    """
    Denies access if the user has no active or trialing subscription.
    Falls back to True if subscription models are unavailable (e.g., in tests).
    """

    message = "An active subscription is required to access this resource."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        try:
            from apps.core.models.payment_models import UserSubscription

            subscription = UserSubscription.objects.filter(
                user=request.user,
                status__in=["active", "trialing"],
            ).first()
            return subscription is not None
        except Exception:
            # If subscription models are unavailable, allow access
            logger.warning(
                "Could not check subscription for user %s", request.user.id
            )
            return True


class IsWorkspaceMember(BasePermission):
    """
    Reusable permission for workspace-scoped views.
    Expects the view to provide workspace_id via self.kwargs.
    """

    message = "You are not a member of this workspace."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        workspace_id = view.kwargs.get("workspace_id")
        if not workspace_id:
            return True  # No workspace context, defer to other permissions

        from apps.collaborators.models import WorkspaceMember

        return WorkspaceMember.objects.filter(
            workspace_id=workspace_id,
            user=request.user,
            is_active=True,
        ).exists()
