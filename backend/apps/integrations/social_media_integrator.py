"""
Social Media Integration and Verification Module
Handles OAuth flows and account verification for various platforms
"""

import os
import base64
import hashlib
import secrets
import logging

import requests

logger = logging.getLogger(__name__)

try:
    import tweepy

    TWEEPY_AVAILABLE = True
except ImportError:
    TWEEPY_AVAILABLE = False
    tweepy = None

from django.conf import settings
from decouple import config

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
                timeout=10,  # <-- Added timeout
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
                timeout=10,  # <-- Added timeout
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
            response = requests.get(
                "https://slack.com/api/conversations.list",
                headers=headers,
                timeout=10,  # <-- Added timeout
            )

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
                response = requests.post(
                    self.webhook_url,
                    json=payload,
                    timeout=10,  # <-- Added timeout
                )
                if response.status_code == 200:
                    return {"success": True, "message": "Message sent to Slack successfully"}

            return {"success": False, "error": "Failed to send Slack message"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_account_info(self, channel_name):
        """Get Slack channel information"""
        return self.verify_account(channel_name)


class LinkedInIntegrator(SocialMediaIntegrator):
    """LinkedIn integration using OAuth 2.0"""

    def __init__(self):
        super().__init__("linkedin")
        # Use decouple.config() to read from .env file (same as Django settings)
        self.client_id = config("LINKEDIN_CLIENT_ID", default=None)
        self.client_secret = config("LINKEDIN_CLIENT_SECRET", default=None)
        self.redirect_uri = config("LINKEDIN_REDIRECT_URI", default="http://127.0.0.1:8000/api/integrations/linkedin/callback/")
        
        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"LinkedIn Integrator initialized - client_id: {self.client_id[:10] if self.client_id else 'None'}...")
        logger.info(f"LinkedIn Integrator initialized - client_secret: {'***set***' if self.client_secret else 'None'}")
        logger.info(f"LinkedIn Integrator initialized - redirect_uri: {self.redirect_uri}")
        
        # Updated scopes - using the scopes that are actually available in your LinkedIn app
        self.scopes = "openid profile email w_member_social"

    @staticmethod
    def _b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    def generate_pkce_pair(self) -> tuple[str, str]:
        """Generate a PKCE code_verifier and S256 code_challenge."""
        # 64 random urlsafe chars -> >43 as required by RFC 7636
        verifier = secrets.token_urlsafe(64)
        challenge = self._b64url(hashlib.sha256(verifier.encode("utf-8")).digest())
        return verifier, challenge

    def start_oauth(self, callback_url=None, state: str | None = None, code_challenge: str | None = None):
        """Start OAuth flow for LinkedIn authentication (supports PKCE)."""
        try:
            redirect_uri = callback_url or self.redirect_uri
            state_param = state or secrets.token_urlsafe(16)

            base = (
                "https://www.linkedin.com/oauth/v2/authorization"
                f"?response_type=code"
                f"&client_id={self.client_id}"
                f"&redirect_uri={redirect_uri}"
                f"&scope={self.scopes}"
                f"&state={state_param}"
            )
            if code_challenge:
                base += f"&code_challenge={code_challenge}&code_challenge_method=S256"

            auth_url = base

            return {
                "auth_url": auth_url,
                "client_id": self.client_id,
                "redirect_uri": redirect_uri,
                "state": state_param,
                "code_challenge_used": bool(code_challenge),
            }
        except Exception as e:
            return {"error": str(e)}

    def exchange_code_for_tokens(self, code, redirect_uri=None, code_verifier: str | None = None):
        """Exchange authorization code for access token"""
        # Setup logging at the beginning
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            token_url = "https://www.linkedin.com/oauth/v2/accessToken"
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "SMMS/1.0",
            }
            
            redirect_uri_to_use = redirect_uri or self.redirect_uri
            
            data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri_to_use,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }
            # Only add code_verifier if it exists and is not empty/False
            if code_verifier and isinstance(code_verifier, str) and len(code_verifier.strip()) > 0:
                data["code_verifier"] = code_verifier
                logger.info(f"LinkedIn token exchange - using PKCE with code_verifier")
            else:
                logger.info(f"LinkedIn token exchange - no PKCE code_verifier provided")
            
            # Log the parameters for debugging (without sensitive data)
            logger.info(f"LinkedIn token exchange - redirect_uri: {redirect_uri_to_use}")
            logger.info(f"LinkedIn token exchange - client_id: {self.client_id}")
            logger.info(f"LinkedIn token exchange - has code_verifier: {bool(code_verifier)}")
            
            # Increased timeout and added headers
            response = requests.post(token_url, data=data, headers=headers, timeout=30)
            
            if response.status_code == 200:
                token_data = response.json()
                return {
                    "success": True,
                    "access_token": token_data.get("access_token"),
                    "expires_in": token_data.get("expires_in"),
                    "refresh_token": token_data.get("refresh_token"),
                    "scope": token_data.get("scope"),
                }
            else:
                logger.error(f"LinkedIn token exchange failed: {response.status_code} - {response.text}")
                return {"success": False, "error": response.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_profile(self, access_token):
        """Get LinkedIn profile information with connection count"""
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "User-Agent": "SMMS/1.0",
            }
            
            # Get basic profile info
            profile_response = requests.get(
                "https://api.linkedin.com/v2/userinfo",
                headers=headers,
                timeout=30
            )
            
            if profile_response.status_code != 200:
                return {"success": False, "error": profile_response.text}
            
            profile_data = profile_response.json()
            
            # Try to get connection count from the profile API
            # Note: LinkedIn's v2 API has limited access to connection counts
            # We'll try the people endpoint for the authenticated user
            connection_count = 0
            try:
                # Get the person's profile including connection count
                person_id = profile_data.get("sub")
                if person_id:
                    person_response = requests.get(
                        f"https://api.linkedin.com/v2/people/{person_id}:(id,firstName,lastName,numConnections)",
                        headers=headers,
                        timeout=30
                    )
                    
                    if person_response.status_code == 200:
                        person_data = person_response.json()
                        connection_count = person_data.get("numConnections", 0)
            except Exception as e:
                logger.warning(f"Failed to get LinkedIn connection count: {e}")
                # Fallback: try to get connection count from profile endpoint
                try:
                    profile_detail_response = requests.get(
                        "https://api.linkedin.com/v2/people/~:(id,firstName,lastName,numConnections,publicProfileUrl)",
                        headers=headers,
                        timeout=30
                    )
                    if profile_detail_response.status_code == 200:
                        detail_data = profile_detail_response.json()
                        connection_count = detail_data.get("numConnections", 0)
                except Exception:
                    pass  # Keep connection_count as 0
            
            return {
                "success": True,
                "profile": {
                    "id": profile_data.get("sub"),
                    "first_name": profile_data.get("given_name", ""),
                    "last_name": profile_data.get("family_name", ""),
                    "email": profile_data.get("email", ""),
                    "profile_picture": profile_data.get("picture", ""),
                    "name": profile_data.get("name", ""),
                    "connection_count": connection_count,
                    "follower_count": connection_count,  # For LinkedIn, connections are similar to followers
                }
            }
                
        except Exception as e:
            return {"success": False, "error": str(e)}

    def publish_post(self, content, access_token=None, credentials=None):
        """Share a post on LinkedIn using UGC API"""
        try:
            if not access_token and credentials:
                access_token = credentials.get("access_token")
            
            if not access_token:
                return {"success": False, "error": "Access token is required"}
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
                "User-Agent": "SMMS/1.0",
            }
            
            # Get the user's profile ID using the userinfo endpoint
            profile_response = requests.get(
                "https://api.linkedin.com/v2/userinfo",
                headers=headers,
                timeout=30
            )
            
            if profile_response.status_code != 200:
                return {"success": False, "error": "Failed to get profile information"}
            
            profile_data = profile_response.json()
            person_urn = f"urn:li:person:{profile_data.get('sub')}"
            
            # Create the UGC post payload
            post_payload = {
                "author": person_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": content
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
            
            # Post the UGC content
            response = requests.post(
                "https://api.linkedin.com/v2/ugcPosts",
                headers=headers,
                json=post_payload,
                timeout=30
            )
            
            if response.status_code == 201:
                share_data = response.json()
                share_id = share_data.get("id", "").replace("urn:li:share:", "").replace("urn:li:ugcPost:", "")
                return {
                    "success": True,
                    "post_id": share_id,
                    "url": f"https://www.linkedin.com/feed/update/{share_id}",
                    "message": "Post shared successfully on LinkedIn"
                }
            else:
                return {"success": False, "error": f"LinkedIn API error: {response.text}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}

    def verify_account(self, access_token):
        """Verify LinkedIn account and get basic info"""
        return self.get_profile(access_token)

    def get_account_info(self, credentials):
        """Get LinkedIn account information"""
        access_token = credentials.get("access_token")
        return self.verify_account(access_token)


# Integration Factory
class FacebookIntegrator(SocialMediaIntegrator):
    """Facebook integration using OAuth 2.0"""

    def __init__(self):
        super().__init__("facebook")
        self.client_id = settings.SOCIAL_MEDIA_CONFIGS.get("FACEBOOK", {}).get("CLIENT_ID")
        self.client_secret = settings.SOCIAL_MEDIA_CONFIGS.get("FACEBOOK", {}).get("CLIENT_SECRET")

    def verify_account(self, credentials):
        """Verify Facebook account credentials"""
        try:
            access_token = credentials.get("access_token")
            if not access_token:
                return {"verified": False, "error": "Access token is required"}

            # Verify token with Facebook API
            response = requests.get(
                "https://graph.facebook.com/v18.0/me",
                params={"access_token": access_token, "fields": "id,name,email,picture"},
                timeout=30
            )

            if response.status_code == 200:
                user_data = response.json()
                return {
                    "verified": True,
                    "platform": "facebook",
                    "username": user_data.get("name", ""),
                    "user_id": user_data.get("id", ""),
                    "email": user_data.get("email", ""),
                    "profile_image": user_data.get("picture", {}).get("data", {}).get("url", ""),
                    "message": "Facebook account verified successfully"
                }
            else:
                return {"verified": False, "error": f"Facebook API error: {response.text}"}

        except Exception as e:
            return {"verified": False, "error": str(e)}

    def get_account_info(self, credentials):
        """Get Facebook account information"""
        return self.verify_account(credentials)

    def publish_post(self, content, media_urls=None, credentials=None):
        """Publish content to Facebook"""
        try:
            access_token = credentials.get("access_token") if credentials else None
            if not access_token:
                return {"success": False, "error": "Access token is required"}

            # First, try to get user's pages
            pages_response = requests.get(
                "https://graph.facebook.com/v18.0/me/accounts",
                params={"access_token": access_token},
                timeout=30
            )

            if pages_response.status_code == 200:
                pages_data = pages_response.json()
                pages = pages_data.get("data", [])
                
                if pages:
                    # Use the first page for posting
                    page = pages[0]
                    page_access_token = page.get("access_token")
                    page_id = page.get("id")
                    
                    if page_access_token:
                        # Post to Facebook Page
                        payload = {"message": content}
                        
                        response = requests.post(
                            f"https://graph.facebook.com/v18.0/{page_id}/feed",
                            data=payload,
                            params={"access_token": page_access_token},
                            timeout=30
                        )

                        if response.status_code == 200:
                            post_data = response.json()
                            post_id = post_data.get("id", "")
                            return {
                                "success": True,
                                "post_id": post_id,
                                "url": f"https://www.facebook.com/{post_id}",
                                "message": f"Post published successfully on Facebook page: {page.get('name', 'Unknown')}"
                            }
                        else:
                            error_data = response.json() if response.content else {"error": "Unknown error"}
                            return {"success": False, "error": f"Facebook Page API error: {error_data}"}
            
            # If no pages or page posting failed, try user feed (legacy - may not work)
            payload = {"message": content}
            
            response = requests.post(
                "https://graph.facebook.com/v18.0/me/feed",
                data=payload,
                params={"access_token": access_token},
                timeout=30
            )

            if response.status_code == 200:
                post_data = response.json()
                post_id = post_data.get("id", "")
                return {
                    "success": True,
                    "post_id": post_id,
                    "url": f"https://www.facebook.com/{post_id}",
                    "message": "Post published successfully on Facebook"
                }
            else:
                return {"success": False, "error": f"Facebook API error: {response.text}"}

        except Exception as e:
            return {"success": False, "error": str(e)}


class IntegrationFactory:
    """Factory for creating social media integrators"""

    @staticmethod
    def get_integrator(platform: str):
        """Get appropriate integrator for platform"""
        integrators = {
            "twitter": TwitterIntegrator,
            "reddit": RedditIntegrator,
            "slack": SlackIntegrator,
            "linkedin": LinkedInIntegrator,
            "facebook": FacebookIntegrator,
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
