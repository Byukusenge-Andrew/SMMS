from rest_framework.permissions import BasePermission


class IsTeamAdminOrOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        member = obj.members.filter(user=request.user).first()
        return member and member.role in ["owner", "admin"]
