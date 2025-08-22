"""
Core views for SMMS
"""
# Import rate limiting views from the dedicated rate limiting views file
from ..rate_limit_views import (
    RateLimitDashboardView,
    RateLimitLogsView, 
    RateLimitStatsView,
    RateLimitTestView,
    IPBlacklistView,
    IPWhitelistView,
)

from .payment_views import (
    get_subscription_tiers,
    get_user_subscription,
    create_subscription,
    update_subscription,
    cancel_subscription,
    get_payment_history,
    create_stripe_customer,
    stripe_webhook,
)

from .gohighlevel_views import (
    setup_gohighlevel_integration,
    get_gohighlevel_integration,
    delete_gohighlevel_integration,
    sync_gohighlevel_contacts,
    get_crm_contacts,
    create_gohighlevel_contact,
    gohighlevel_webhook,
)

__all__ = [
    # Rate limiting views
    'RateLimitDashboardView',
    'RateLimitLogsView',
    'RateLimitStatsView', 
    'RateLimitTestView',
    'IPBlacklistView',
    'IPWhitelistView',
    # Payment views
    'get_subscription_tiers',
    'get_user_subscription',
    'create_subscription',
    'update_subscription',
    'cancel_subscription',
    'get_payment_history',
    'create_stripe_customer',
    'stripe_webhook',
    # GoHighLevel views
    'setup_gohighlevel_integration',
    'get_gohighlevel_integration',
    'delete_gohighlevel_integration',
    'sync_gohighlevel_contacts',
    'get_crm_contacts',
    'create_gohighlevel_contact',
    'gohighlevel_webhook',
]
