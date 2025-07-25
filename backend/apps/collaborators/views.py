from datetime import timedelta

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.posts.models import Post

from .models import (Comment, PostCollaboration, Review, Workspace,
                     WorkspaceMember)
from .serializers import (CommentSerializer, PostCollaborationSerializer,
                          ReviewSerializer, WorkspaceInviteSerializer,
                          WorkspaceMemberSerializer, WorkspaceSerializer,
                          WorkspaceStatsSerializer)


class WorkspaceListCreateView(generics.ListCreateAPIView):
    """API view to list and create workspaces"""

    permission_classes = [IsAuthenticated]
    serializer_class = WorkspaceSerializer

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
    serializer_class = WorkspaceSerializer

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
    serializer_class = WorkspaceMemberSerializer

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
    serializer_class = PostCollaborationSerializer

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
    serializer_class = ReviewSerializer

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
    serializer_class = CommentSerializer

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


# Additional API endpoints for collaboration features


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def invite_to_workspace(request, workspace_id):
    """Invite a user to a workspace via email"""
    workspace = get_object_or_404(Workspace, id=workspace_id)

    # Check permissions
    membership = WorkspaceMember.objects.filter(workspace=workspace, user=request.user).first()
    if not membership or not membership.can_manage_members:
        raise PermissionDenied("You don't have permission to invite members")

    serializer = WorkspaceInviteSerializer(data=request.data)
    if serializer.is_valid():
        # TODO: Implement email invitation system
        # For now, just return success
        return Response(
            {
                "message": "Invitation sent successfully",
                "email": serializer.validated_data["email"],
                "workspace": workspace.name,
            }
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def workspace_stats(request, workspace_id):
    """Get workspace statistics"""
    workspace = get_object_or_404(Workspace, id=workspace_id)

    # Check access
    if not workspace.members.filter(id=request.user.id).exists():
        raise PermissionDenied("You don't have access to this workspace")

    # Calculate stats
    collaborations = PostCollaboration.objects.filter(workspace=workspace)
    current_month = timezone.now().replace(day=1)

    stats = {
        "total_posts": collaborations.count(),
        "total_members": workspace.members.count(),
        "posts_this_month": collaborations.filter(created_at__gte=current_month).count(),
        "pending_reviews": Review.objects.filter(collaboration__workspace=workspace, status="pending").count(),
        "published_posts": collaborations.filter(status="published").count(),
        "draft_posts": collaborations.filter(status="draft").count(),
    }

    serializer = WorkspaceStatsSerializer(stats)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def assign_post_for_review(request, post_id):
    """Assign a post to reviewers"""
    post = get_object_or_404(Post, id=post_id)

    # Check if user owns the post or has permission
    if post.user != request.user:
        raise PermissionDenied("You don't have permission to assign this post")

    reviewer_ids = request.data.get("reviewer_ids", [])
    due_date = request.data.get("due_date")

    # Get or create collaboration
    collaboration, created = PostCollaboration.objects.get_or_create(
        post=post, defaults={"status": "review", "due_date": due_date}
    )

    # Add reviewers
    from django.contrib.auth.models import User

    reviewers = User.objects.filter(id__in=reviewer_ids)
    collaboration.reviewers.set(reviewers)

    return Response(
        {
            "message": "Post assigned for review",
            "collaboration_id": collaboration.id,
            "reviewers": [r.username for r in reviewers],
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def remove_workspace_member(request, workspace_id, member_id):
    """Remove a member from workspace"""
    workspace = get_object_or_404(Workspace, id=workspace_id)

    # Check permissions
    membership = WorkspaceMember.objects.filter(workspace=workspace, user=request.user).first()
    if not membership or not membership.can_manage_members:
        raise PermissionDenied("You don't have permission to remove members")

    # Remove member
    member_to_remove = get_object_or_404(WorkspaceMember, workspace=workspace, id=member_id)

    # Don't allow removing the owner
    if member_to_remove.role == "owner":
        return Response({"error": "Cannot remove workspace owner"}, status=status.HTTP_400_BAD_REQUEST)

    member_to_remove.delete()

    return Response({"message": "Member removed successfully"})
