from django.shortcuts import get_object_or_404

from rest_framework import generics
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from apps.posts.models import Post

from .models import Comment, PostCollaboration, Review, Workspace, WorkspaceMember

# You'll need to create serializers for these models


class WorkspaceListCreateView(generics.ListCreateAPIView):
    """API view to list and create workspaces"""

    permission_classes = [IsAuthenticated]
    # serializer_class = WorkspaceSerializer

    def get_queryset(self):
        """Return workspaces where the user is a member"""
        return Workspace.objects.filter(members=self.request.user)

    def perform_create(self, serializer):
        """Set the current user as the owner when creating a workspace"""
        workspace = serializer.save(owner=self.request.user)

        # Add the owner as a member with appropriate permissions
        WorkspaceMember.objects.create(
            workspace=workspace,
            user=self.request.user,
            role="owner",
            can_create_posts=True,
            can_edit_posts=True,
            can_delete_posts=True,
            can_publish_posts=True,
            can_view_analytics=True,
            can_manage_members=True,
        )


class WorkspaceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """API view to retrieve, update and delete workspaces"""

    permission_classes = [IsAuthenticated]
    # serializer_class = WorkspaceSerializer

    def get_queryset(self):
        """Return workspaces where the user is a member"""
        return Workspace.objects.filter(members=self.request.user)

    def perform_update(self, serializer):
        """Ensure only owners or admins can update workspaces"""
        workspace = self.get_object()
        membership = WorkspaceMember.objects.get(workspace=workspace, user=self.request.user)

        if membership.role not in ["owner", "admin"]:
            raise PermissionDenied("You don't have permission to update this workspace")

        serializer.save()

    def perform_destroy(self, instance):
        """Ensure only owners can delete workspaces"""
        membership = WorkspaceMember.objects.get(workspace=instance, user=self.request.user)

        if membership.role != "owner":
            raise PermissionDenied("Only workspace owners can delete workspaces")

        instance.delete()


class WorkspaceMemberListView(generics.ListCreateAPIView):
    """API view to list and add members to a workspace"""

    permission_classes = [IsAuthenticated]
    # serializer_class = WorkspaceMemberSerializer

    def get_queryset(self):
        """Return members of a specific workspace"""
        workspace_id = self.kwargs.get("workspace_id")
        workspace = get_object_or_404(Workspace, id=workspace_id)

        # Check if user has access to this workspace
        if not workspace.members.filter(id=self.request.user.id).exists():
            raise PermissionDenied("You don't have access to this workspace")

        return WorkspaceMember.objects.filter(workspace=workspace)

    def perform_create(self, serializer):
        """Add a member to a workspace"""
        workspace_id = self.kwargs.get("workspace_id")
        workspace = get_object_or_404(Workspace, id=workspace_id)

        # Check if user can manage members
        membership = WorkspaceMember.objects.get(workspace=workspace, user=self.request.user)
        if not membership.can_manage_members:
            raise PermissionDenied("You don't have permission to add members")

        serializer.save(workspace=workspace)


class PostCollaborationView(generics.RetrieveUpdateAPIView):
    """API view to manage collaboration for a post"""

    permission_classes = [IsAuthenticated]
    # serializer_class = PostCollaborationSerializer

    def get_object(self):
        """Get or create collaboration for a post"""
        post_id = self.kwargs.get("post_id")
        post = get_object_or_404(Post, id=post_id)

        # Check if user has access to the post
        if post.user != self.request.user:
            workspace_ids = WorkspaceMember.objects.filter(user=self.request.user).values_list("workspace_id", flat=True)

            collaborations = PostCollaboration.objects.filter(post=post, workspace_id__in=workspace_ids)

            if not collaborations.exists():
                raise PermissionDenied("You don't have access to this post")

        # Get or create collaboration
        collaboration, created = PostCollaboration.objects.get_or_create(
            post=post, defaults={"workspace": WorkspaceMember.objects.filter(user=self.request.user).first().workspace}
        )

        return collaboration


class ReviewListCreateView(generics.ListCreateAPIView):
    """API view to list and create reviews for a collaboration"""

    permission_classes = [IsAuthenticated]
    # serializer_class = ReviewSerializer

    def get_queryset(self):
        """Return reviews for a collaboration"""
        collaboration_id = self.kwargs.get("collaboration_id")
        collaboration = get_object_or_404(PostCollaboration, id=collaboration_id)

        # Check if user has access
        if (
            collaboration.post.user != self.request.user
            and not collaboration.reviewers.filter(id=self.request.user.id).exists()
        ):
            raise PermissionDenied("You don't have permission to view these reviews")

        return Review.objects.filter(collaboration=collaboration)

    def perform_create(self, serializer):
        """Create a review for a collaboration"""
        collaboration_id = self.kwargs.get("collaboration_id")
        collaboration = get_object_or_404(PostCollaboration, id=collaboration_id)

        # Check if user is a reviewer
        if not collaboration.reviewers.filter(id=self.request.user.id).exists():
            raise PermissionDenied("You are not assigned as a reviewer for this post")

        serializer.save(collaboration=collaboration, reviewer=self.request.user)


class CommentListCreateView(generics.ListCreateAPIView):
    """API view to list and create comments on a post"""

    permission_classes = [IsAuthenticated]
    # serializer_class = CommentSerializer

    def get_queryset(self):
        """Return comments for a post"""
        post_id = self.kwargs.get("post_id")
        post = get_object_or_404(Post, id=post_id)

        # Check if user has access to the post
        if post.user != self.request.user:
            workspace_ids = WorkspaceMember.objects.filter(user=self.request.user).values_list("workspace_id", flat=True)

            collaborations = PostCollaboration.objects.filter(post=post, workspace_id__in=workspace_ids)

            if not collaborations.exists():
                raise PermissionDenied("You don't have access to this post's comments")

        return Comment.objects.filter(post=post, parent=None)

    def perform_create(self, serializer):
        """Create a comment on a post"""
        post_id = self.kwargs.get("post_id")
        post = get_object_or_404(Post, id=post_id)

        # Check if user has access to the post for commenting
        if post.user != self.request.user:
            workspace_ids = WorkspaceMember.objects.filter(user=self.request.user).values_list("workspace_id", flat=True)

            collaborations = PostCollaboration.objects.filter(post=post, workspace_id__in=workspace_ids)

            if not collaborations.exists():
                raise PermissionDenied("You don't have permission to comment on this post")

        serializer.save(post=post, user=self.request.user)
