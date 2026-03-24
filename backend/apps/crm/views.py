from django.db.models import Sum, Count
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Activity, Contact, Deal, Pipeline
from .serializers import (
    ActivitySerializer,
    ContactSerializer,
    DealSerializer,
    PipelineSerializer,
)


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------

class ContactListCreateView(generics.ListCreateAPIView):
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Contact.objects.filter(owner=self.request.user)
        status_filter = self.request.query_params.get("status")
        search = self.request.query_params.get("search")
        if status_filter:
            qs = qs.filter(status=status_filter)
        if search:
            qs = qs.filter(
                first_name__icontains=search
            ) | qs.filter(
                last_name__icontains=search
            ) | qs.filter(
                email__icontains=search
            ) | qs.filter(
                company__icontains=search
            )
        return qs

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ContactDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Contact.objects.filter(owner=self.request.user)


# ---------------------------------------------------------------------------
# Pipelines
# ---------------------------------------------------------------------------

class PipelineListCreateView(generics.ListCreateAPIView):
    serializer_class = PipelineSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Pipeline.objects.filter(owner=self.request.user).prefetch_related("deals")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class PipelineDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PipelineSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Pipeline.objects.filter(owner=self.request.user)


# ---------------------------------------------------------------------------
# Deals
# ---------------------------------------------------------------------------

class DealListCreateView(generics.ListCreateAPIView):
    serializer_class = DealSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Deal.objects.filter(owner=self.request.user).select_related("contact", "pipeline")
        stage = self.request.query_params.get("stage")
        pipeline_id = self.request.query_params.get("pipeline")
        if stage:
            qs = qs.filter(stage=stage)
        if pipeline_id:
            qs = qs.filter(pipeline_id=pipeline_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class DealDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DealSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Deal.objects.filter(owner=self.request.user)


# ---------------------------------------------------------------------------
# Activities
# ---------------------------------------------------------------------------

class ActivityListCreateView(generics.ListCreateAPIView):
    serializer_class = ActivitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Activity.objects.filter(owner=self.request.user)
        contact_id = self.request.query_params.get("contact")
        deal_id = self.request.query_params.get("deal")
        if contact_id:
            qs = qs.filter(contact_id=contact_id)
        if deal_id:
            qs = qs.filter(deal_id=deal_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ActivityDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ActivitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Activity.objects.filter(owner=self.request.user)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def crm_dashboard(request):
    user = request.user

    contacts = Contact.objects.filter(owner=user)
    deals = Deal.objects.filter(owner=user)
    activities = Activity.objects.filter(owner=user)

    contact_by_status = {
        s: contacts.filter(status=s).count()
        for s, _ in Contact.STATUS_CHOICES
    }

    deal_by_stage = {
        s: deals.filter(stage=s).count()
        for s, _ in Deal.STAGE_CHOICES
    }

    total_won_value = deals.filter(stage="won").aggregate(total=Sum("value"))["total"] or 0
    total_pipeline_value = deals.exclude(stage__in=["won", "lost"]).aggregate(
        total=Sum("value")
    )["total"] or 0

    recent_contacts = ContactSerializer(contacts.order_by("-created_at")[:5], many=True).data
    recent_deals = DealSerializer(
        deals.order_by("-created_at")[:5].select_related("contact", "pipeline"), many=True
    ).data
    upcoming_activities = ActivitySerializer(
        activities.filter(completed=False).order_by("due_date")[:5], many=True
    ).data

    return Response({
        "summary": {
            "total_contacts": contacts.count(),
            "total_deals": deals.count(),
            "total_won_value": float(total_won_value),
            "total_pipeline_value": float(total_pipeline_value),
            "open_activities": activities.filter(completed=False).count(),
        },
        "contacts_by_status": contact_by_status,
        "deals_by_stage": deal_by_stage,
        "recent_contacts": recent_contacts,
        "recent_deals": recent_deals,
        "upcoming_activities": upcoming_activities,
    })
