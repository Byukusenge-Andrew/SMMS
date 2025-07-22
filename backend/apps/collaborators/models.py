from django.db import models
from django.contrib.auth.models import User
from apps.posts.models import Post


class Workspace(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="owned_workspaces")
    members = models.ManyToManyField(User, through="WorkspaceMember", related_name="workspaces")

    # Settings
    is_active = models.BooleanField(default=True)
    allow_guest_access = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workspaces"

    def __str__(self):
        return f"{self.name} - {self.owner.username}"


class WorkspaceMember(models.Model):
    ROLE_CHOICES = [
        ("owner", "Owner"),
        ("admin", "Admin"),
        ("editor", "Editor"),
        ("viewer", "Viewer"),
        ("guest", "Guest"),
    ]

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="workspace_memberships")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    # Permissions
    can_create_posts = models.BooleanField(default=False)
    can_edit_posts = models.BooleanField(default=False)
    can_delete_posts = models.BooleanField(default=False)
    can_publish_posts = models.BooleanField(default=False)
    can_view_analytics = models.BooleanField(default=False)
    can_manage_members = models.BooleanField(default=False)

    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "workspace_members"
        unique_together = ["workspace", "user"]

    def __str__(self):
        return f"{self.workspace.name} - {self.user.username} ({self.role})"


class PostCollaboration(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("review", "Under Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("published", "Published"),
    ]

    post = models.OneToOneField(Post, on_delete=models.CASCADE, related_name="collaboration")
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="post_collaborations")
    assignee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="assigned_posts", null=True, blank=True)
    reviewers = models.ManyToManyField(User, related_name="posts_to_review", blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    due_date = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "post_collaborations"

    def __str__(self):
        return f"Collaboration for Post {self.post.id}"


class Review(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("changes_requested", "Changes Requested"),
    ]

    collaboration = models.ForeignKey(PostCollaboration, on_delete=models.CASCADE, related_name="reviews")
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="given_reviews")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    comment = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reviews"
        unique_together = ["collaboration", "reviewer"]

    def __str__(self):
        return f"Review by {self.reviewer.username} - {self.status}"


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="collaboration_comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="post_comments")
    content = models.TextField()
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "collaboration_comments"
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.user.username} on Post {self.post.id}"
