"""
URL configuration for collaborators app
"""

from django.urls import path

from .views import (CommentListCreateView, PostCollaborationView,
                    ReviewListCreateView, WorkspaceDetailView,
                    WorkspaceListCreateView, WorkspaceMemberListView,
                    assign_post_for_review, invite_to_workspace,
                    remove_workspace_member, workspace_stats)

app_name = "collaborators"

urlpatterns = [
    # Workspaces
    path("workspaces/", WorkspaceListCreateView.as_view(), name="workspace-list-create"),
    path("workspaces/<int:pk>/", WorkspaceDetailView.as_view(), name="workspace-detail"),
    path("workspaces/<int:workspace_id>/stats/", workspace_stats, name="workspace-stats"),
    # Workspace Members
    path("workspaces/<int:workspace_id>/members/", WorkspaceMemberListView.as_view(), name="workspace-members"),
    path("workspaces/<int:workspace_id>/invite/", invite_to_workspace, name="workspace-invite"),
    path("workspaces/<int:workspace_id>/members/<int:member_id>/remove/", remove_workspace_member, name="remove-member"),
    # Post Collaboration
    path("posts/<int:post_id>/collaboration/", PostCollaborationView.as_view(), name="post-collaboration"),
    path("posts/<int:post_id>/assign-review/", assign_post_for_review, name="assign-post-review"),
    path("posts/<int:post_id>/comments/", CommentListCreateView.as_view(), name="comment-list-create"),
    # Reviews
    path("collaborations/<int:collaboration_id>/reviews/", ReviewListCreateView.as_view(), name="review-list-create"),
]
