from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Campaign, CampaignApplication, Influencer

# You may need to create serializers for these models


class InfluencerProfileView(generics.RetrieveUpdateAPIView):
    """View for managing influencer profile"""

    permission_classes = [IsAuthenticated]
    # serializer_class = InfluencerSerializer

    def get_object(self):
        # Get or create influencer profile for the current user
        influencer, created = Influencer.objects.get_or_create(user=self.request.user)
        return influencer


class CampaignListCreateView(generics.ListCreateAPIView):
    """View for listing and creating campaigns"""

    permission_classes = [IsAuthenticated]
    # serializer_class = CampaignSerializer

    def get_queryset(self):
        # If user is an influencer, show available campaigns
        if hasattr(self.request.user, "influencer_profile"):
            # Filter campaigns by influencer criteria
            self.request.user.influencer_profile.niche
            return Campaign.objects.filter(status="active")
        else:
            # Show campaigns created by this user
            return Campaign.objects.filter(creator=self.request.user)

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)


class CampaignDetailView(generics.RetrieveUpdateDestroyAPIView):
    """View for retrieving, updating and deleting campaigns"""

    permission_classes = [IsAuthenticated]
    # serializer_class = CampaignSerializer

    def get_queryset(self):
        # Only allow access to campaigns created by this user
        return Campaign.objects.filter(creator=self.request.user)


class CampaignApplicationListCreateView(generics.ListCreateAPIView):
    """View for listing and creating campaign applications"""

    permission_classes = [IsAuthenticated]
    # serializer_class = CampaignApplicationSerializer

    def get_queryset(self):
        # For influencers, show their applications
        if hasattr(self.request.user, "influencer_profile"):
            return CampaignApplication.objects.filter(influencer=self.request.user.influencer_profile)
        else:
            # For campaign creators, show applications to their campaigns
            campaigns = Campaign.objects.filter(creator=self.request.user)
            return CampaignApplication.objects.filter(campaign__in=campaigns)

    def perform_create(self, serializer):
        influencer = self.request.user.influencer_profile
        serializer.save(influencer=influencer)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def influencer_dashboard(request):
    """Dashboard view for influencers with statistics and available campaigns"""
    try:
        influencer = request.user.influencer_profile

        # Get pending and approved applications
        pending_applications = CampaignApplication.objects.filter(influencer=influencer, status="pending").count()

        approved_applications = CampaignApplication.objects.filter(influencer=influencer, status="approved").count()

        # Get available campaigns matching influencer criteria
        available_campaigns = Campaign.objects.filter(status="active").count()

        return Response(
            {
                "pending_applications": pending_applications,
                "approved_applications": approved_applications,
                "available_campaigns": available_campaigns,
                "profile_completion": calculate_profile_completion(influencer),
            }
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


def calculate_profile_completion(influencer):
    """Calculate profile completion percentage"""
    fields = ["bio", "niche", "website", "post_rate"]
    completed = sum(1 for field in fields if getattr(influencer, field))
    return (completed / len(fields)) * 100
