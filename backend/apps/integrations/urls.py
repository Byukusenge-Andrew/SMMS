from django.urls import path, include

from .views import (
    canva_integration,
    dropbox_integration,
    google_drive_integration,
    oauth_callback,
    slack_integration,
    zapier_integration,
)
from .views_oauth import OAuthCallbackView, OAuthLoginView
from .views_twitter import (
    verify_twitter_credentials,
    post_tweet,
    get_user_tweets,
    get_tweet_analytics,
    search_tweets,
    delete_tweet,
    get_my_twitter_posts,
    get_twitter_rate_limit,
    twitter_authorize,
    twitter_callback,
    twitter_bind_tokens,
)

urlpatterns = [
    # OAuth and general integrations
    path("slack/", slack_integration, name="slack-integration"),
    path("canva/", canva_integration, name="canva-integration"),
    path("google-drive/", google_drive_integration, name="google-drive"),
    path("dropbox/", dropbox_integration, name="dropbox"),
    path("zapier/", zapier_integration, name="zapier-integration"),
    path("oauth/login/<str:provider>/", OAuthLoginView.as_view(), name="oauth-login"),
    path("oauth/callback/<str:backend>/", OAuthCallbackView.as_view(), name="oauth-callback"),
    path("oauth/callback/", oauth_callback, name="oauth-callback"),

    # Twitter/X OAuth connect endpoints
    path("twitter/authorize/", twitter_authorize, name="twitter-authorize"),
    path("twitter/callback/", twitter_callback, name="twitter-callback"),
    path("twitter/bind-tokens/", twitter_bind_tokens, name="twitter-bind-tokens"),

    # Twitter/X API endpoints
    path("twitter/verify/", verify_twitter_credentials, name="twitter-verify-credentials"),
    path("twitter/post/", post_tweet, name="twitter-post-tweet"),
    path("twitter/tweets/", get_user_tweets, name="twitter-get-user-tweets"),
    path("twitter/analytics/<str:tweet_id>/", get_tweet_analytics, name="twitter-get-tweet-analytics"),
    path("twitter/search/", search_tweets, name="twitter-search-tweets"),
    path("twitter/delete/<str:tweet_id>/", delete_tweet, name="twitter-delete-tweet"),
    path("twitter/my-posts/", get_my_twitter_posts, name="twitter-get-my-posts"),
    path("twitter/rate-limit/", get_twitter_rate_limit, name="twitter-rate-limit"),
]
