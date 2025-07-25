import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class BaseSocialMediaIntegrator(ABC):
    """Base class for all social media integrators"""

    def __init__(self, platform: str):
        self.platform = platform
        self.logger = logger

    @abstractmethod
    def verify_account(self, account_name: str) -> Dict[str, Any]:
        """Verify if an account exists and is accessible"""
        self.logger.info(f"Verifying account {account_name} on {self.platform}")
        return {
            "verified": True,
            "account_name": account_name,
            "platform": self.platform,
            "follower_count": 1000,  # Mock data
            "following_count": 500,
            "bio": f"Mock bio for {account_name}",
            "profile_image": "https://example.com/profile.jpg",
        }

    @abstractmethod
    def publish_post(self, content: str, media_urls: Optional[list] = None, **kwargs) -> Dict[str, Any]:
        """Publish a post to the platform"""
        self.logger.info(f"Publishing post to {self.platform}: {content[:50]}...")
        return {
            "success": True,
            "post_id": f"mock_{self.platform}_{hash(content)}",
            "url": f"https://{self.platform}.com/post/mock",
            "published_at": "2025-07-25T00:00:00Z",
        }

    @abstractmethod
    def get_analytics(self, post_id: str) -> Dict[str, Any]:
        """Get analytics data for a post"""
        self.logger.info(f"Getting analytics for post {post_id} on {self.platform}")
        return {
            "post_id": post_id,
            "platform": self.platform,
            "impressions": 2500,
            "reach": 1800,
            "likes": 150,
            "comments": 25,
            "shares": 30,
            "engagement_rate": 8.5,
            "retrieved_at": "2025-07-25T00:00:00Z",
        }

    @abstractmethod
    def get_account_info(self, account_name: str) -> Dict[str, Any]:
        """Get account information"""
        self.logger.info(f"Getting account info for {account_name} on {self.platform}")
        return {
            "username": account_name,
            "display_name": f"{account_name} on {self.platform}",
            "follower_count": 1250,
            "following_count": 580,
            "posts_count": 42,
            "verified": False,
            "bio": f"Bio for {account_name}",
            "website": f"https://{account_name}.com",
            "profile_image": "https://example.com/profile.jpg",
        }

    def start_oauth(self, callback_url: str) -> Dict[str, Any]:
        """Start OAuth flow (optional for some platforms)"""
        self.logger.warning(f"OAuth not implemented for {self.platform}")
        return {
            "auth_url": f"https://{self.platform}.com/oauth/authorize?callback={callback_url}",
            "state": "mock_state_token",
            "platform": self.platform,
        }
