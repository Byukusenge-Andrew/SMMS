from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path("dashboard/", views.crm_dashboard, name="crm-dashboard"),

    # Contacts
    path("contacts/", views.ContactListCreateView.as_view(), name="crm-contact-list"),
    path("contacts/<uuid:pk>/", views.ContactDetailView.as_view(), name="crm-contact-detail"),

    # Pipelines
    path("pipelines/", views.PipelineListCreateView.as_view(), name="crm-pipeline-list"),
    path("pipelines/<uuid:pk>/", views.PipelineDetailView.as_view(), name="crm-pipeline-detail"),

    # Deals
    path("deals/", views.DealListCreateView.as_view(), name="crm-deal-list"),
    path("deals/<uuid:pk>/", views.DealDetailView.as_view(), name="crm-deal-detail"),

    # Activities
    path("activities/", views.ActivityListCreateView.as_view(), name="crm-activity-list"),
    path("activities/<uuid:pk>/", views.ActivityDetailView.as_view(), name="crm-activity-detail"),
]
