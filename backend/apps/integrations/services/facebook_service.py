"""
Facebook API Integration Service

Facebook Graph API Integration for content management and posting.
Supports Facebook's OAuth 2.0 flow and content posting capabilities.
"""
import os
import logging
import requests
import json
from typing import Dict, List, Optional, Any, Tuple
from django.conf import settings
from decouple import config
from datetime import datetime, timedelta
from urllib.parse import urlencode, parse_qs, urlparse

logger = logging.getLogger(__name__)


class FacebookService:
    """Service class for Facebook Graph API integration"""
    
    # Facebook OAuth URLs
    BASE_URL = "https://graph.facebook.com"
    AUTH_URL = "https://www.facebook.com/v19.0/dialog/oauth"
    TOKEN_URL = "https://graph.facebook.com/v19.0/oauth/access_token"
    
    # Graph API version
    API_VERSION = "v19.0"
    
    def __init__(self):
        """Initialize Facebook API service"""
        self.app_id = None
        self.app_secret = None
        self.redirect_uri = None
        self._initialized = False
    
    def _lazy_init(self):
        """Lazy initialization of Facebook API credentials"""
        if self._initialized:
            return True
        
        # Read credentials from Django settings first, then from environment
        social_auth = getattr(settings, 'SOCIAL_AUTH_CONFIG', {})
        facebook_config = social_auth.get('FACEBOOK', {})
        
        # Use decouple.config() to properly read from .env file
        self.app_id = (
            facebook_config.get('APP_ID') or 
            config('FACEBOOK_APP_ID', default=None)
        )
        self.app_secret = (
            facebook_config.get('APP_SECRET') or 
            config('FACEBOOK_APP_SECRET', default=None)
        )
        self.redirect_uri = (
            facebook_config.get('REDIRECT_URI') or 
            config('FACEBOOK_REDIRECT_URI', default=None) or 
            f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')}/integrations/facebook/callback"
        )
        
        # Validate required credentials
        if not all([self.app_id, self.app_secret]):
            logger.error(f"Missing Facebook API credentials - app_id: {bool(self.app_id)}, app_secret: {bool(self.app_secret)}")
            return False
        
        self._initialized = True
        logger.info(f"Facebook API service initialized successfully with app_id: {self.app_id}")
        return True
    
    def get_authorization_url(self, state: str = None) -> str:
        """
        Generate Facebook OAuth authorization URL
        
        Args:
            state: State parameter for OAuth flow
            
        Returns:
            Authorization URL
        """
        if not self._lazy_init():
            raise Exception("Facebook service not properly initialized")
        
        # Facebook Login Kit parameters
        params = {
            'client_id': self.app_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'public_profile,email,pages_manage_posts,pages_read_engagement',
            'response_type': 'code',
        }
        
        if state:
            params['state'] = state
        
        return f"{self.AUTH_URL}?{urlencode(params)}"
    
    def exchange_code_for_token(self, authorization_code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token
        
        Args:
            authorization_code: Authorization code from OAuth callback
            
        Returns:
            Token response containing access_token, expires_in, etc.
        """
        if not self._lazy_init():
            raise Exception("Facebook service not properly initialized")
        
        params = {
            'client_id': self.app_id,
            'client_secret': self.app_secret,
            'redirect_uri': self.redirect_uri,
            'code': authorization_code,
        }
        
        try:
            response = requests.get(self.TOKEN_URL, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Facebook returns error in the response
            if 'error' in data:
                logger.error(f"Facebook token exchange failed: {data.get('error', {}).get('message')}")
                raise Exception(f"Token exchange failed: {data.get('error', {}).get('message')}")
            
            return data
            
        except requests.RequestException as e:
            logger.error(f"Facebook token exchange request failed: {e}")
            raise Exception(f"Token exchange request failed: {e}")
    
    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Get Facebook user information
        
        Args:
            access_token: User's access token
            
        Returns:
            User information
        """
        url = f"{self.BASE_URL}/{self.API_VERSION}/me"
        params = {
            'access_token': access_token,
            'fields': 'id,name,email,picture.type(large),link'
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if 'error' in data:
                logger.error(f"Facebook user info request failed: {data.get('error', {}).get('message')}")
                raise Exception(f"User info request failed: {data.get('error', {}).get('message')}")
            
            return data
            
        except requests.RequestException as e:
            logger.error(f"Facebook user info request failed: {e}")
            raise Exception(f"User info request failed: {e}")
    
    def get_user_pages(self, access_token: str) -> Dict[str, Any]:
        """
        Get user's Facebook pages
        
        Args:
            access_token: User's access token
            
        Returns:
            List of user's pages
        """
        url = f"{self.BASE_URL}/{self.API_VERSION}/me/accounts"
        params = {
            'access_token': access_token,
            'fields': 'id,name,access_token,category,picture.type(large),fan_count'
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if 'error' in data:
                logger.error(f"Facebook pages request failed: {data.get('error', {}).get('message')}")
                raise Exception(f"Pages request failed: {data.get('error', {}).get('message')}")
            
            return data
            
        except requests.RequestException as e:
            logger.error(f"Facebook pages request failed: {e}")
            raise Exception(f"Pages request failed: {e}")
    
    def post_to_page(self, page_access_token: str, page_id: str, message: str, **kwargs) -> Dict[str, Any]:
        """
        Post content to Facebook page
        
        Args:
            page_access_token: Page's access token
            page_id: Page ID
            message: Post message
            **kwargs: Additional post parameters (link, picture, etc.)
            
        Returns:
            Post response
        """
        url = f"{self.BASE_URL}/{self.API_VERSION}/{page_id}/feed"
        
        data = {
            'access_token': page_access_token,
            'message': message,
        }
        
        # Add optional parameters
        if kwargs.get('link'):
            data['link'] = kwargs['link']
        if kwargs.get('picture'):
            data['picture'] = kwargs['picture']
        if kwargs.get('name'):
            data['name'] = kwargs['name']
        if kwargs.get('caption'):
            data['caption'] = kwargs['caption']
        if kwargs.get('description'):
            data['description'] = kwargs['description']
        
        try:
            response = requests.post(url, data=data)
            response.raise_for_status()
            
            result = response.json()
            
            if 'error' in result:
                logger.error(f"Facebook post failed: {result.get('error', {}).get('message')}")
                raise Exception(f"Post failed: {result.get('error', {}).get('message')}")
            
            return result
            
        except requests.RequestException as e:
            logger.error(f"Facebook post request failed: {e}")
            raise Exception(f"Post request failed: {e}")
    
    def get_page_posts(self, page_access_token: str, page_id: str, limit: int = 25) -> Dict[str, Any]:
        """
        Get posts from Facebook page
        
        Args:
            page_access_token: Page's access token
            page_id: Page ID
            limit: Number of posts to retrieve
            
        Returns:
            List of posts
        """
        url = f"{self.BASE_URL}/{self.API_VERSION}/{page_id}/posts"
        params = {
            'access_token': page_access_token,
            'fields': 'id,message,created_time,full_picture,permalink_url,likes.summary(true),comments.summary(true),shares',
            'limit': min(limit, 100)  # Facebook limit
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if 'error' in data:
                logger.error(f"Facebook posts request failed: {data.get('error', {}).get('message')}")
                raise Exception(f"Posts request failed: {data.get('error', {}).get('message')}")
            
            return data
            
        except requests.RequestException as e:
            logger.error(f"Facebook posts request failed: {e}")
            raise Exception(f"Posts request failed: {e}")
    
    def validate_token(self, access_token: str) -> bool:
        """
        Validate if access token is still valid
        
        Args:
            access_token: Access token to validate
            
        Returns:
            True if token is valid, False otherwise
        """
        try:
            user_info = self.get_user_info(access_token)
            return bool(user_info.get('id'))
        except Exception as e:
            logger.error(f"Facebook token validation failed: {e}")
            return False
    
    def extend_access_token(self, short_lived_token: str) -> Dict[str, Any]:
        """
        Exchange short-lived token for long-lived token
        
        Args:
            short_lived_token: Short-lived access token
            
        Returns:
            Long-lived token response
        """
        if not self._lazy_init():
            raise Exception("Facebook service not properly initialized")
        
        url = f"{self.BASE_URL}/{self.API_VERSION}/oauth/access_token"
        params = {
            'grant_type': 'fb_exchange_token',
            'client_id': self.app_id,
            'client_secret': self.app_secret,
            'fb_exchange_token': short_lived_token,
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if 'error' in data:
                logger.error(f"Facebook token extension failed: {data.get('error', {}).get('message')}")
                raise Exception(f"Token extension failed: {data.get('error', {}).get('message')}")
            
            return data
            
        except requests.RequestException as e:
            logger.error(f"Facebook token extension request failed: {e}")
            raise Exception(f"Token extension request failed: {e}")
