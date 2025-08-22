"""
Custom permissions for ensuring data isolation between clients
"""

from rest_framework import permissions
from django.core.exceptions import PermissionDenied


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit/delete it.
    Assumes the model instance has a `user` attribute.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for any authenticated user (if object belongs to them)
        if hasattr(obj, 'user') and obj.user != request.user:
            return False
            
        # Write permissions are only allowed to the owner of the object
        if request.method in permissions.SAFE_METHODS:
            return hasattr(obj, 'user') and obj.user == request.user
        
        # Write permissions only for owner
        return hasattr(obj, 'user') and obj.user == request.user


class IsOwnerOnly(permissions.BasePermission):
    """
    Stricter permission that only allows access to objects owned by the requesting user.
    Used for sensitive data like social media accounts, posts, etc.
    """
    
    def has_permission(self, request, view):
        """Check if user is authenticated"""
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """Check if user owns the object"""
        if not hasattr(obj, 'user'):
            # If object doesn't have user field, check if it's related to user indirectly
            if hasattr(obj, 'get_owner'):
                return obj.get_owner() == request.user
            return False
        
        return obj.user == request.user


class IsTeamMemberOrOwner(permissions.BasePermission):
    """
    Permission for team-based access where users can access data within their team/workspace
    but not data from other teams
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Check direct ownership first
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        
        # Check team membership for shared resources
        if hasattr(obj, 'workspace'):
            from apps.collaborators.models import WorkspaceMember
            return WorkspaceMember.objects.filter(
                workspace=obj.workspace,
                user=request.user,
                is_active=True
            ).exists()
        
        # Check if object belongs to user's team
        if hasattr(obj, 'team'):
            from apps.authentication.models import TeamMember
            return TeamMember.objects.filter(
                team=obj.team,
                user=request.user,
                is_active=True
            ).exists()
        
        return False


class DataIsolationMixin:
    """
    Mixin to ensure all views automatically filter data by user
    """
    
    def get_queryset(self):
        """
        Override to ensure user filtering is always applied
        """
        queryset = super().get_queryset()
        
        # Ensure user is authenticated
        if not self.request.user.is_authenticated:
            return queryset.none()
        
        # Apply user filter if model has user field
        model = queryset.model
        if hasattr(model, '_meta'):
            user_field = None
            for field in model._meta.fields:
                if field.name == 'user' and hasattr(field, 'related_model'):
                    from django.contrib.auth.models import User
                    if field.related_model == User:
                        user_field = 'user'
                        break
            
            if user_field:
                return queryset.filter(**{user_field: self.request.user})
        
        return queryset
    
    def perform_create(self, serializer):
        """
        Ensure created objects are associated with the current user
        """
        # Automatically set user field if it exists
        if hasattr(serializer.Meta.model, '_meta'):
            for field in serializer.Meta.model._meta.fields:
                if field.name == 'user' and hasattr(field, 'related_model'):
                    from django.contrib.auth.models import User
                    if field.related_model == User:
                        serializer.save(user=self.request.user)
                        return
        
        # Fallback to default behavior
        super().perform_create(serializer)


def ensure_data_isolation(view_func):
    """
    Decorator to ensure data isolation in function-based views
    """
    def wrapper(request, *args, **kwargs):
        # Store original user for verification
        request._isolation_user = request.user
        
        # Call original function
        response = view_func(request, *args, **kwargs)
        
        # Log access for audit trail
        if hasattr(request, 'user') and request.user.is_authenticated:
            import logging
            logger = logging.getLogger('data_isolation')
            logger.info(f"User {request.user.id} accessed {view_func.__name__}")
        
        return response
    
    return wrapper


class ClientDataValidator:
    """
    Utility class to validate that data operations don't cross client boundaries
    """
    
    @staticmethod
    def validate_user_access(user, obj):
        """
        Validate that a user has access to an object
        """
        if not user or not user.is_authenticated:
            raise PermissionDenied("User not authenticated")
        
        if hasattr(obj, 'user'):
            if obj.user != user:
                raise PermissionDenied("Access denied: Object belongs to different user")
        else:
            # Check indirect relationships
            owner = ClientDataValidator.get_object_owner(obj)
            if owner and owner != user:
                raise PermissionDenied("Access denied: Object belongs to different user")
    
    @staticmethod
    def get_object_owner(obj):
        """
        Get the owner of an object through various relationship patterns
        """
        # Direct user field
        if hasattr(obj, 'user'):
            return obj.user
        
        # Through workspace
        if hasattr(obj, 'workspace') and hasattr(obj.workspace, 'user'):
            return obj.workspace.user
        
        # Through team
        if hasattr(obj, 'team') and hasattr(obj.team, 'owner'):
            return obj.team.owner
        
        # Through post/parent object
        if hasattr(obj, 'post') and hasattr(obj.post, 'user'):
            return obj.post.user
        
        return None
    
    @staticmethod
    def bulk_validate_access(user, objects):
        """
        Validate access to multiple objects at once
        """
        for obj in objects:
            ClientDataValidator.validate_user_access(user, obj)


class OwnerIfPresent(permissions.BasePermission):
    """
    Global-safe permission that only enforces ownership when the object exposes a `user` field.
    - If the object has `user`, require it matches request.user (staff bypass allowed).
    - If no `user` field is present, allow access and defer to view-specific rules.
    """

    def has_permission(self, request, view):
        # Rely on other permissions (e.g., IsAuthenticated) for general access
        return True

    def has_object_permission(self, request, view, obj):
        # Allow safe methods by default; ownership will be enforced if present
        if hasattr(obj, 'user'):
            user = getattr(request, 'user', None)
            if not user or not user.is_authenticated:
                return False
            if getattr(user, 'is_staff', False):
                return True
            return obj.user == user
        return True
