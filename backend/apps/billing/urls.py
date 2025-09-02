from django.urls import path
from . import views

urlpatterns = [
    # Billing dashboard
    path('dashboard/', views.billing_dashboard, name='billing_dashboard'),
    
    # Subscription tiers
    path('tiers/', views.subscription_tiers, name='subscription_tiers'),
    
    # Current subscription
    path('subscription/', views.current_subscription, name='current_subscription'),
    path('subscription/create/', views.create_subscription, name='create_subscription'),
    path('subscription/cancel/', views.cancel_subscription, name='cancel_subscription'),
    
    # Payment history
    path('payments/', views.payment_history, name='payment_history'),
    
    # Invoices
    path('invoices/', views.invoices, name='invoices'),
    
    # Payment methods
    path('payment-methods/', views.payment_methods, name='payment_methods'),
    path('payment-methods/<uuid:method_id>/', views.delete_payment_method, name='delete_payment_method'),
    
    # Stripe integration
    path('stripe/customer/', views.create_stripe_customer, name='create_stripe_customer'),
    path('stripe/checkout/', views.create_checkout_session, name='create_checkout_session'),
    path('stripe/customer-portal/', views.create_customer_portal_session, name='customer_portal'),
    path('stripe/webhook/', views.stripe_webhook, name='stripe_webhook'),
    path('stripe/payment-success/', views.handle_payment_success, name='handle_payment_success'),
    
    # Subscription API endpoints
    path('api/subscription-tiers/', views.subscription_tiers_list, name='subscription_tiers_list'),
    path('api/subscription-status/', views.current_subscription_status, name='subscription_status'),
    
    # Trial conversion
    path('trial/convert/', views.convert_trial_to_paid, name='convert_trial_to_paid'),
]
