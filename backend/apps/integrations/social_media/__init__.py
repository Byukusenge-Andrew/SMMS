# Stub file for the social media integration
from typing import Any, Dict, List


class SocialMediaManager:
    """Simplified social media manager for development"""

    def __init__(self, social_account=None):
        self.social_account = social_account

    def publish_post(self, post):
        """Simulate publishing a post"""
        return {
            "success": True,
            "post_id": "mock-post-12345",
            "platform": getattr(self.social_account, "platform", "unknown"),
            "url": "https://example.com/mock-post",
        }

    def get_analytics(self, post_id=None, date_range=None):
        """Simulate getting analytics data"""
        return {"likes": 120, "comments": 25, "shares": 10, "impressions": 2000, "reach": 1500, "engagement_rate": 3.5}


# Export the class as default
__all__ = ["SocialMediaManager"]
