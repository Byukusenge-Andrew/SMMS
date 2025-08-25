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
    path('stripe/webhook/', views.stripe_webhook, name='stripe_webhook'),
]
