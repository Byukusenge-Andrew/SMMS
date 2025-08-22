"""
URL configuration for payment and CRM functionality
"""

from django.urls import path
from .views.payment_views import (
    # Payment views
    get_subscription_tiers,
    get_user_subscription,
    create_subscription,
    update_subscription,
    cancel_subscription,
    get_payment_history,
    create_stripe_customer,
    stripe_webhook,
    # Admin tier management
    create_subscription_tier,
    update_subscription_tier,
    delete_subscription_tier,
)
from .views.gohighlevel_views import (
    setup_gohighlevel_integration,
    get_gohighlevel_integration,
    delete_gohighlevel_integration,
    sync_gohighlevel_contacts,
    get_crm_contacts,
    create_gohighlevel_contact,
    gohighlevel_webhook,
    # CRM contact management
    create_crm_contact,
    update_crm_contact,
    delete_crm_contact,
    get_crm_contact,
)

app_name = 'core'

urlpatterns = [
    # Payment and subscription routes
    path('subscriptions/tiers/', get_subscription_tiers, name='subscription_tiers'),
    path('subscriptions/tiers/create/', create_subscription_tier, name='create_subscription_tier'),
    path('subscriptions/tiers/<uuid:tier_id>/update/', update_subscription_tier, name='update_subscription_tier'),
    path('subscriptions/tiers/<uuid:tier_id>/delete/', delete_subscription_tier, name='delete_subscription_tier'),
    path('subscriptions/user/', get_user_subscription, name='user_subscription'),
    path('subscriptions/create/', create_subscription, name='create_subscription'),
    path('subscriptions/update/', update_subscription, name='update_subscription'),
    path('subscriptions/cancel/', cancel_subscription, name='cancel_subscription'),
    path('payments/history/', get_payment_history, name='payment_history'),
    path('stripe/customer/', create_stripe_customer, name='create_stripe_customer'),
    path('stripe/webhook/', stripe_webhook, name='stripe_webhook'),
    
    # GoHighLevel CRM routes
    path('ghl/setup/', setup_gohighlevel_integration, name='ghl_setup'),
    path('ghl/integration/', get_gohighlevel_integration, name='ghl_integration'),
    path('ghl/integration/delete/', delete_gohighlevel_integration, name='ghl_delete'),
    path('ghl/sync-contacts/', sync_gohighlevel_contacts, name='ghl_sync_contacts'),
    path('ghl/contacts/', get_crm_contacts, name='ghl_contacts'),
    path('ghl/contacts/create/', create_gohighlevel_contact, name='ghl_create_contact'),
    path('ghl/webhook/', gohighlevel_webhook, name='ghl_webhook'),
    
    # CRM contact management
    path('contacts/', get_crm_contacts, name='get_contacts'),
    path('contacts/create/', create_crm_contact, name='create_contact'),
    path('contacts/<uuid:contact_id>/', get_crm_contact, name='get_contact'),
    path('contacts/<uuid:contact_id>/update/', update_crm_contact, name='update_contact'),
    path('contacts/<uuid:contact_id>/delete/', delete_crm_contact, name='delete_contact'),
]
