from django.urls import path

from .views import (
    CommentListCreateView,
    PostCollaborationView,
    ReviewListCreateView,
    WorkspaceDetailView,
    WorkspaceListCreateView,
    WorkspaceMemberListView,
)

urlpatterns = [
    path("workspaces/", WorkspaceListCreateView.as_view(), name="workspace-list-create"),
    path("workspaces/<int:pk>/", WorkspaceDetailView.as_view(), name="workspace-detail"),
    path("workspaces/<int:workspace_id>/members/", WorkspaceMemberListView.as_view(), name="workspace-members"),
    path("posts/<int:post_id>/collaboration/", PostCollaborationView.as_view(), name="post-collaboration"),
    path("collaborations/<int:collaboration_id>/reviews/", ReviewListCreateView.as_view(), name="review-list-create"),
    path("posts/<int:post_id>/comments/", CommentListCreateView.as_view(), name="comment-list-create"),
]
