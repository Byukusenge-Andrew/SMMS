"""
Serializers for the collaborators app
"""

from rest_framework import serializers

from apps.authentication.serializers import UserSerializer
from apps.posts.serializers import PostSerializer

from .models import Comment, PostCollaboration, Review, Workspace, WorkspaceMember


class WorkspaceSerializer(serializers.ModelSerializer):
    """Serializer for Workspace model"""

    owner = UserSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = [
            "id",
            "name",
            "description",
            "owner",
            "is_active",
            "allow_guest_access",
            "member_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "owner", "created_at", "updated_at"]

    def get_member_count(self, obj):
        """Get the number of members in the workspace"""
        return obj.members.count()


class WorkspaceMemberSerializer(serializers.ModelSerializer):
    """Serializer for WorkspaceMember model"""

    user = UserSerializer(read_only=True)
    workspace_name = serializers.CharField(source="workspace.name", read_only=True)

    class Meta:
        model = WorkspaceMember
        fields = [
            "id",
            "workspace",
            "workspace_name",
            "user",
            "role",
            "can_create_posts",
            "can_edit_posts",
            "can_delete_posts",
            "can_publish_posts",
            "can_view_analytics",
            "can_manage_members",
            "joined_at",
        ]
        read_only_fields = ["id", "workspace_name", "user", "joined_at"]


class CommentSerializer(serializers.ModelSerializer):
    """Serializer for Comment model"""

    user = UserSerializer(read_only=True)
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ["id", "post", "user", "content", "parent", "replies", "created_at", "updated_at"]
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def get_replies(self, obj):
        """Get replies to this comment"""
        if obj.replies.exists():
            return CommentSerializer(obj.replies.all(), many=True).data
        return []


class PostCollaborationSerializer(serializers.ModelSerializer):
    """Serializer for PostCollaboration model"""

    post = PostSerializer(read_only=True)
    assignee = UserSerializer(read_only=True)
    workspace = WorkspaceSerializer(read_only=True)

    class Meta:
        model = PostCollaboration
        fields = ["id", "post", "workspace", "assignee", "status", "due_date", "created_at", "updated_at"]
        read_only_fields = ["id", "post", "workspace", "assignee", "created_at", "updated_at"]


class ReviewSerializer(serializers.ModelSerializer):
    """Serializer for Review model"""

    reviewer = UserSerializer(read_only=True)
    collaboration = PostCollaborationSerializer(read_only=True)

    class Meta:
        model = Review
        fields = ["id", "collaboration", "reviewer", "status", "comment", "created_at", "updated_at"]
        read_only_fields = ["id", "collaboration", "reviewer", "created_at", "updated_at"]


class WorkspaceInviteSerializer(serializers.Serializer):
    """Serializer for workspace invitation"""

    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=WorkspaceMember.ROLE_CHOICES)
    can_create_posts = serializers.BooleanField(default=False)
    can_edit_posts = serializers.BooleanField(default=False)
    can_delete_posts = serializers.BooleanField(default=False)
    can_publish_posts = serializers.BooleanField(default=False)
    can_view_analytics = serializers.BooleanField(default=True)
    can_manage_members = serializers.BooleanField(default=False)

    def validate_email(self, value):
        """Validate email format"""
        return value.lower()


class WorkspaceStatsSerializer(serializers.Serializer):
    """Serializer for workspace statistics"""

    total_posts = serializers.IntegerField()
    total_members = serializers.IntegerField()
    posts_this_month = serializers.IntegerField()
    pending_reviews = serializers.IntegerField()
    published_posts = serializers.IntegerField()
    draft_posts = serializers.IntegerField()
