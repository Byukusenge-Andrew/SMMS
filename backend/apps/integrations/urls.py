from django.urls import path, include

from .views import (
    canva_integration,
    dropbox_integration,
    dropbox_files,
    dropbox_import,
    google_drive_integration,
    google_drive_files,
    google_drive_import,
    oauth_callback,
    slack_integration,
    slack_conversations,
    slack_history,
    slack_auth_status,
    slack_send_message,
    zapier_integration,
    hashtag_suggestions,
    optimal_posting_times,
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
    twitter_disconnect,
)
from .views_linkedin import (
    linkedin_authorize,
    linkedin_callback,
    linkedin_bind_tokens,
    verify_linkedin_credentials,
    post_linkedin_share,
    linkedin_disconnect,
)
from .views_facebook import (
    facebook_authorize,
    facebook_callback,
    verify_facebook_credentials,
    post_facebook_share,
    facebook_disconnect,
)
from .test_views import facebook_test_page
from .tiktok_views import (
    tiktok_auth_url,
    tiktok_oauth_callback,
    tiktok_oauth_callback_get,
    tiktok_accounts,
    tiktok_disconnect,
    tiktok_create_post,
    tiktok_posts,
    tiktok_post_detail,
    tiktok_delete_post,
    tiktok_video_analytics,
)
from .views_canva import (
    canva_authorize,
    canva_callback,
    canva_bind_tokens,
    canva_disconnect,
)

urlpatterns = [
    # OAuth and general integrations
    path("slack/", slack_integration, name="slack-integration"),
    path("slack/conversations/", slack_conversations, name="slack-conversations"),
    path("slack/history/", slack_history, name="slack-history"),
    path("slack/auth-status/", slack_auth_status, name="slack-auth-status"),
    path("slack/send/", slack_send_message, name="slack-send-message"),
    path("canva/", canva_integration, name="canva-integration"),
    # Canva OAuth endpoints
    path("canva/authorize/", canva_authorize, name="canva-authorize"),
    path("canva/callback/", canva_callback, name="canva-callback"),
    path("canva/bind-tokens/", canva_bind_tokens, name="canva-bind-tokens"),
    path("canva/disconnect/", canva_disconnect, name="canva-disconnect"),
    path("google-drive/", google_drive_integration, name="google-drive"),
    path("google-drive/files/", google_drive_files, name="google-drive-files"),
    path("google-drive/import/", google_drive_import, name="google-drive-import"),
    path("dropbox/", dropbox_integration, name="dropbox"),
    path("dropbox/files/", dropbox_files, name="dropbox-files"),
    path("dropbox/import/", dropbox_import, name="dropbox-import"),
    path("zapier/", zapier_integration, name="zapier-integration"),
    path("hashtags/suggest/", hashtag_suggestions, name="hashtag-suggestions"),
    path("posting/optimal-times/", optimal_posting_times, name="optimal-posting-times"),
    path("oauth/login/<str:provider>/", OAuthLoginView.as_view(), name="oauth-login"),
    path("oauth/callback/<str:backend>/", OAuthCallbackView.as_view(), name="oauth-callback"),
    path("oauth/callback/", oauth_callback, name="oauth-callback"),

    # Twitter/X OAuth connect endpoints
    path("twitter/authorize/", twitter_authorize, name="twitter-authorize"),
    path("twitter/callback/", twitter_callback, name="twitter-callback"),
    path("twitter/bind-tokens/", twitter_bind_tokens, name="twitter-bind-tokens"),
    path("twitter/disconnect/", twitter_disconnect, name="twitter-disconnect"),

    # Twitter/X API endpoints
    path("twitter/verify/", verify_twitter_credentials, name="twitter-verify-credentials"),
    path("twitter/post/", post_tweet, name="twitter-post-tweet"),
    path("twitter/tweets/", get_user_tweets, name="twitter-get-user-tweets"),
    path("twitter/analytics/<str:tweet_id>/", get_tweet_analytics, name="twitter-get-tweet-analytics"),
    path("twitter/search/", search_tweets, name="twitter-search-tweets"),
    path("twitter/delete/<str:tweet_id>/", delete_tweet, name="twitter-delete-tweet"),
    path("twitter/my-posts/", get_my_twitter_posts, name="twitter-get-my-posts"),
    path("twitter/rate-limit/", get_twitter_rate_limit, name="twitter-rate-limit"),

    # LinkedIn OAuth connect endpoints
    path("linkedin/authorize/", linkedin_authorize, name="linkedin-authorize"),
    path("linkedin/callback/", linkedin_callback, name="linkedin-callback"),
    path("linkedin/bind-tokens/", linkedin_bind_tokens, name="linkedin-bind-tokens"),
    path("linkedin/disconnect/", linkedin_disconnect, name="linkedin-disconnect"),

    # LinkedIn API endpoints
    path("linkedin/verify/", verify_linkedin_credentials, name="linkedin-verify-credentials"),
    path("linkedin/post/", post_linkedin_share, name="linkedin-post-share"),

    # Facebook OAuth connect endpoints
    path("facebook/authorize/", facebook_authorize, name="facebook-authorize"),
    path("facebook/callback/", facebook_callback, name="facebook-callback"),
    path("facebook/disconnect/", facebook_disconnect, name="facebook-disconnect"),

    # Facebook API endpoints
    path("facebook/verify/", verify_facebook_credentials, name="facebook-verify-credentials"),
    path("facebook/post/", post_facebook_share, name="facebook-post-share"),

    # TikTok OAuth connect endpoints
    path("tiktok/auth-url/", tiktok_auth_url, name="tiktok-auth-url"),
    path("tiktok/callback/", tiktok_oauth_callback, name="tiktok-oauth-callback"),
    path("tiktok/callback-get/", tiktok_oauth_callback_get, name="tiktok-oauth-callback-get"),
    path("tiktok/accounts/", tiktok_accounts, name="tiktok-accounts"),
    path("tiktok/disconnect/<str:account_id>/", tiktok_disconnect, name="tiktok-disconnect"),

    # TikTok API endpoints
    path("tiktok/create-post/", tiktok_create_post, name="tiktok-create-post"),
    path("tiktok/posts/", tiktok_posts, name="tiktok-posts"),
    path("tiktok/posts/<str:post_id>/", tiktok_post_detail, name="tiktok-post-detail"),
    path("tiktok/posts/<str:post_id>/delete/", tiktok_delete_post, name="tiktok-delete-post"),
    path("tiktok/analytics/", tiktok_video_analytics, name="tiktok-video-analytics"),

    # Test pages
    path("facebook/test/", facebook_test_page, name="facebook-test"),
]
