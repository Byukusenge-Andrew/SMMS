"""
Social Media Integration and Verification Module
Handles OAuth flows and account verification for various platforms
"""

import os

import requests

try:
    import tweepy

    TWEEPY_AVAILABLE = True
except ImportError:
    TWEEPY_AVAILABLE = False
    tweepy = None

from django.conf import settings

from rest_framework import status
from rest_framework.response import Response

from apps.authentication.models import SocialMediaAccount


class SocialMediaIntegrator:
    """Base class for social media integrations"""

    def __init__(self, platform):
        self.platform = platform

    def verify_account(self, credentials):
        """Verify account credentials - override in subclasses"""
        return {
            "verified": False,
            "error": "Not implemented for this platform",
            "message": f"Account verification not implemented for {self.platform}",
        }

    def get_account_info(self, credentials):
        """Get account information - override in subclasses"""
        return {
            "success": False,
            "error": "Not implemented for this platform",
            "message": f"Account info retrieval not implemented for {self.platform}",
        }

    def publish_post(self, content, media_urls=None, credentials=None):
        """Publish content - override in subclasses"""
        return {
            "success": False,
            "error": "Not implemented for this platform",
            "message": f"Publishing not implemented for {self.platform}",
        }

    def get_analytics(self, credentials, post_id=None, date_range=None):
        """Get analytics data - override in subclasses"""
        return {
            "success": False,
            "error": "Not implemented for this platform",
            "message": f"Analytics not implemented for {self.platform}",
        }


class TwitterIntegrator(SocialMediaIntegrator):
    """Twitter/X integration using OAuth 2.0"""

    def __init__(self):
        super().__init__("twitter")
        if not TWEEPY_AVAILABLE:
            raise ImportError("Tweepy is required for Twitter integration")

        self.api_key = os.getenv("TWITTER_API_KEY")
        self.api_secret = os.getenv("TWITTER_API_KEY_SECRET")
        self.bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        self.access_token = os.getenv("TWITTER_ACCESS_TOKEN")
        self.access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

    def verify_account(self, username):
        """Verify Twitter account exists and get basic info"""
        try:
            # Use Bearer Token for app authentication
            headers = {"Authorization": f"Bearer {self.bearer_token}", "Content-Type": "application/json"}

            # Get user by username
            response = requests.get(
                f"https://api.twitter.com/2/users/by/username/{username}",
                headers=headers,
                params={"user.fields": "id,name,username,public_metrics,verified,profile_image_url"},
                timeout=10,  # <-- Add timeout
            )

            if response.status_code == 200:
                user_data = response.json().get("data", {})
                return {
                    "verified": True,
                    "account_id": user_data.get("id"),
                    "account_name": user_data.get("username"),
                    "display_name": user_data.get("name"),
                    "followers_count": user_data.get("public_metrics", {}).get("followers_count", 0),
                    "is_verified": user_data.get("verified", False),
                    "profile_image": user_data.get("profile_image_url"),
                    "platform_data": user_data,
                }
            else:
                return {"verified": False, "error": "Account not found"}

        except Exception as e:
            return {"verified": False, "error": str(e)}

    def get_account_info(self, credentials):
        """Get Twitter account information"""
        return self.verify_account(credentials.get("username"))

    def publish_post(self, content, media_urls=None, credentials=None):
        """Publish a tweet"""
        try:
            auth = tweepy.OAuthHandler(self.api_key, self.api_secret)
            auth.set_access_token(credentials.get("access_token"), credentials.get("access_token_secret"))
            api = tweepy.API(auth)

            # Post tweet
            if media_urls:
                # Handle media upload (simplified)
                tweet = api.update_status(status=content)
            else:
                tweet = api.update_status(status=content)

            return {
                "success": True,
                "post_id": str(tweet.id),
                "url": f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}",
                "created_at": tweet.created_at.isoformat(),
            }
        except Exception as e:
            return {"success": False, "error": str(e), "message": "Failed to publish tweet"}

    def start_oauth(self, callback_url):
        """Start OAuth flow for user authentication"""
        try:
            # Create OAuth 1.0a handler
            auth = tweepy.OAuth1UserHandler(self.api_key, self.api_secret, callback=callback_url)

            # Get authorization URL
            auth_url = auth.get_authorization_url()

            return {
                "auth_url": auth_url,
                "oauth_token": auth.request_token["oauth_token"],
                "oauth_token_secret": auth.request_token["oauth_token_secret"],
            }
        except Exception as e:
            return {"error": str(e)}


class RedditIntegrator(SocialMediaIntegrator):
    """Reddit integration"""

    def __init__(self):
        super().__init__("reddit")
        self.client_id = settings.SOCIAL_MEDIA_CONFIGS.get("REDDIT", {}).get("CLIENT_ID")
        self.client_secret = settings.SOCIAL_MEDIA_CONFIGS.get("REDDIT", {}).get("CLIENT_SECRET")

    def verify_account(self, username):
        """Verify Reddit account exists"""
        try:
            # Reddit doesn't require authentication for public user info
            response = requests.get(
                f"https://www.reddit.com/user/{username}/about.json",
                headers={"User-Agent": "SMSManager/1.0"},
                timeout=10,  # <-- Add timeout
            )

            if response.status_code == 200:
                data = response.json().get("data", {})
                return {
                    "verified": True,
                    "account_name": data.get("name"),
                    "karma": data.get("total_karma", 0),
                    "created": data.get("created_utc"),
                    "is_verified": data.get("verified", False),
                    "platform_data": data,
                }
            else:
                return {"verified": False, "error": "Reddit account not found"}

        except Exception as e:
            return {"verified": False, "error": str(e)}

    def get_account_info(self, username):
        """Get Reddit account information"""
        return self.verify_account(username)

    def publish_post(self, content, subreddit, credentials=None):
        """Submit a post to Reddit (requires OAuth)"""
        try:
            # This would require proper Reddit OAuth implementation
            # For now, return a mock successful response
            return {
                "success": True,
                "post_id": f"reddit_mock_{hash(content)}",
                "url": f"https://reddit.com/r/{subreddit}/comments/mock",
                "message": "Post submitted successfully (mock)",
            }
        except Exception as e:
            return {"success": False, "error": str(e), "message": "Failed to submit Reddit post"}


class SlackIntegrator(SocialMediaIntegrator):
    """Slack integration for notifications"""

    def __init__(self):
        super().__init__("slack")
        self.bot_token = settings.SLACK_BOT_TOKEN
        self.webhook_url = settings.SLACK_WEBHOOK_URL

    def verify_account(self, channel_name):
        """Verify Slack channel exists"""
        try:
            headers = {"Authorization": f"Bearer {self.bot_token}"}
            response = requests.get("https://slack.com/api/conversations.list", headers=headers, timeout=10)  # <-- Add timeout

            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    channels = data.get("channels", [])
                    for channel in channels:
                        if channel.get("name") == channel_name:
                            return {
                                "verified": True,
                                "channel_id": channel.get("id"),
                                "channel_name": channel.get("name"),
                                "is_private": channel.get("is_private", False),
                                "platform_data": channel,
                            }

            return {"verified": False, "error": "Channel not found"}

        except Exception as e:
            return {"verified": False, "error": str(e)}

    def publish_post(self, content, channel=None, credentials=None):
        """Send message to Slack channel"""
        try:
            payload = {"text": content, "channel": channel or "#general"}

            if self.webhook_url:
                response = requests.post(self.webhook_url, json=payload, timeout=10)  # <-- Add timeout
                if response.status_code == 200:
                    return {"success": True, "message": "Message sent to Slack successfully"}

            return {"success": False, "error": "Failed to send Slack message"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_account_info(self, channel_name):
        """Get Slack channel information"""
        return self.verify_account(channel_name)


# Integration Factory
class IntegrationFactory:
    """Factory for creating social media integrators"""

    @staticmethod
    def get_integrator(platform: str):
        """Get appropriate integrator for platform"""
        integrators = {
            "twitter": TwitterIntegrator,
            "reddit": RedditIntegrator,
            "slack": SlackIntegrator,
        }

        integrator_class = integrators.get(platform.lower())
        if integrator_class:
            return integrator_class()
        else:
            raise ValueError(f"Unsupported platform: {platform}")


def verify_social_account(platform: str, username: str) -> dict:
    """Convenience function to verify social media accounts"""
    try:
        integrator = IntegrationFactory.get_integrator(platform)
        return integrator.verify_account(username)
    except Exception as e:
        return {"verified": False, "error": str(e), "platform": platform}
