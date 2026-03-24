import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Contact(models.Model):
    """A CRM contact representing a lead, customer, or partner."""

    STATUS_CHOICES = [
        ("lead", "Lead"),
        ("prospect", "Prospect"),
        ("customer", "Customer"),
        ("churned", "Churned"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="crm_app_contacts")

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    company = models.CharField(max_length=200, blank=True)
    job_title = models.CharField(max_length=200, blank=True)
    website = models.URLField(blank=True)
    avatar = models.URLField(blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="lead")
    tags = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)

    # Social media handles
    twitter_handle = models.CharField(max_length=100, blank=True)
    linkedin_url = models.URLField(blank=True)
    instagram_handle = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email


class Pipeline(models.Model):
    """A sales/outreach pipeline owned by a user."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="crm_pipelines")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Deal(models.Model):
    """A deal in the CRM pipeline."""

    STAGE_CHOICES = [
        ("new", "New"),
        ("contacted", "Contacted"),
        ("qualified", "Qualified"),
        ("proposal", "Proposal Sent"),
        ("negotiation", "Negotiation"),
        ("won", "Won"),
        ("lost", "Lost"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="crm_deals")
    pipeline = models.ForeignKey(Pipeline, on_delete=models.CASCADE, related_name="deals", null=True, blank=True)
    contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, blank=True, related_name="deals")

    title = models.CharField(max_length=255)
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES, default="new")
    value = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="USD")
    close_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Activity(models.Model):
    """An activity log entry linked to a contact or deal."""

    TYPE_CHOICES = [
        ("note", "Note"),
        ("call", "Call"),
        ("email", "Email"),
        ("meeting", "Meeting"),
        ("task", "Task"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="crm_activities")
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, null=True, blank=True, related_name="activities")
    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, null=True, blank=True, related_name="activities")

    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="note")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    completed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
