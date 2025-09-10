"""
TikTok API Integration Service

TikTok Business API Integration for content management and posting.
Supports TikTok's OAuth 2.0 flow with PKCE and video posting capabilities.
"""
import os
import logging
import requests
import json
import secrets
import hashlib
import base64
from typing import Dict, List, Optional, Any, Tuple
from django.conf import settings
from decouple import config
from datetime import datetime, timedelta
from urllib.parse import urlencode, parse_qs, urlparse

logger = logging.getLogger(__name__)


class TikTokService:
    """Service class for TikTok Business API integration"""
    
    # TikTok OAuth URLs (Standard TikTok Login Kit, not Business API)
    BASE_URL = "https://www.tiktok.com"
    AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
    TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
    
    # Content creation endpoints (TikTok API v2)
    CONTENT_UPLOAD_URL = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
    CONTENT_PUBLISH_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
    
    def __init__(self):
        """Initialize TikTok API service"""
        self.client_key = None
        self.client_secret = None
        self.redirect_uri = None
        self._initialized = False
        self.code_verifier = None
        self.code_challenge = None

    def _generate_pkce_pair(self) -> Tuple[str, str]:
        """
        Generate PKCE code_verifier and code_challenge pair
        
        Returns:
            Tuple of (code_verifier, code_challenge)
        """
        # Generate code_verifier (43-128 characters, URL-safe)
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        
        # Generate code_challenge using SHA256
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
        return code_verifier, code_challenge
    
    def _lazy_init(self):
        """Lazy initialization of TikTok API credentials"""
        if self._initialized:
            return True
        
        # Read credentials from Django settings first, then from environment
        social_auth = getattr(settings, 'SOCIAL_AUTH_CONFIG', {})
        tiktok_config = social_auth.get('TIKTOK', {})
        
        # Use decouple.config() to properly read from .env file
        self.client_key = (
            tiktok_config.get('CLIENT_KEY') or 
            config('TIKTOK_CLIENT_KEY', default=None)
        )
        self.client_secret = (
            tiktok_config.get('CLIENT_SECRET') or 
            config('TIKTOK_CLIENT_SECRET', default=None)
 
        )
        self.redirect_uri = (
            tiktok_config.get('REDIRECT_URI') or 
            config('TIKTOK_REDIRECT_URI', default=None) or 
            f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')}/integrations/tiktok/callback"
        )
        
        # Validate required credentials
        if not all([self.client_key, self.client_secret]):
            logger.error(f"Missing TikTok API credentials - client_key: {bool(self.client_key)}, client_secret: {bool(self.client_secret)}")
            return False
        
        self._initialized = True
        logger.info(f"TikTok API service initialized successfully with client_key: {self.client_key[:10]}...")
        return True
    
    def get_authorization_url(self, state: str = None) -> str:
        """
        Generate TikTok OAuth authorization URL with PKCE
        
        Args:
            state: State parameter for OAuth flow
            
        Returns:
            Authorization URL
        """
        if not self._lazy_init():
            raise Exception("TikTok service not properly initialized")
        
        # Generate PKCE parameters
        self.code_verifier, self.code_challenge = self._generate_pkce_pair()
        
        # TikTok Login Kit v2 parameters with PKCE
        params = {
            'client_key': self.client_key,  # TikTok uses client_key per official docs
            'scope': 'user.info.basic,video.upload,video.list,user.info.profile,user.info.stats',
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'code_challenge': self.code_challenge,
            'code_challenge_method': 'S256',
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
            Token response containing access_token, refresh_token, etc.
        """
        if not self._lazy_init():
            raise Exception("TikTok service not properly initialized")
        
        if not self.code_verifier:
            raise Exception("Code verifier not found. Must call get_authorization_url first.")
        
        payload = {
            'client_key': self.client_key,  # TikTok uses client_key per official docs
            'client_secret': self.client_secret,
            'code': authorization_code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri,
            'code_verifier': self.code_verifier,
        }
        
        # Use form data for TikTok API v2
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Cache-Control': 'no-cache'
        }
        
        try:
            response = requests.post(self.TOKEN_URL, data=payload, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            
            # TikTok API v2 response format
            if 'error' in data:
                logger.error(f"TikTok token exchange failed: {data.get('error_description', data.get('error'))}")
                raise Exception(f"Token exchange failed: {data.get('error_description', data.get('error'))}")
            
            return data
            
        except requests.RequestException as e:
            logger.error(f"TikTok token exchange request failed: {e}")
            raise Exception(f"Token exchange request failed: {e}")
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            New token response
        """
        if not self._lazy_init():
            raise Exception("TikTok service not properly initialized")
        
        payload = {
            'client_key': self.client_key,  # TikTok uses client_key per official docs
            'client_secret': self.client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
        }
        
        try:
            response = requests.post(self.TOKEN_URL, json=payload)
            response.raise_for_status()
            
            data = response.json()
            if data.get('code') != 0:
                logger.error(f"TikTok token refresh failed: {data.get('message')}")
                raise Exception(f"Token refresh failed: {data.get('message')}")
            
            return data.get('data', {})
            
        except requests.RequestException as e:
            logger.error(f"TikTok token refresh request failed: {e}")
            raise Exception(f"Token refresh request failed: {e}")
    
    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Get TikTok user information
        
        Args:
            access_token: User's access token
            
        Returns:
            User information
        """
        url = f"{self.BASE_URL}/open_api/v1.3/user/info/"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }
        
        try:
            response = requests.post(url, headers=headers, json={'fields': ['open_id', 'union_id', 'avatar_url', 'display_name']})
            response.raise_for_status()
            
            data = response.json()
            if data.get('code') != 0:
                logger.error(f"TikTok user info request failed: {data.get('message')}")
                raise Exception(f"User info request failed: {data.get('message')}")
            
            return data.get('data', {}).get('user', {})
            
        except requests.RequestException as e:
            logger.error(f"TikTok user info request failed: {e}")
            raise Exception(f"User info request failed: {e}")
    
    def upload_video(self, access_token: str, video_file_path: str, **kwargs) -> Dict[str, Any]:
        """
        Upload video to TikTok
        
        Args:
            access_token: User's access token
            video_file_path: Path to video file
            **kwargs: Additional video metadata (title, description, etc.)
            
        Returns:
            Upload response
        """
        if not os.path.exists(video_file_path):
            raise Exception(f"Video file not found: {video_file_path}")
        
        # Step 1: Initialize upload
        init_url = "https://open-api.tiktok.com/share/video/upload/init/"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }
        
        # Get file size
        file_size = os.path.getsize(video_file_path)
        
        init_payload = {
            'source_info': {
                'source': 'FILE_UPLOAD',
                'video_size': file_size,
                'chunk_size': min(file_size, 10 * 1024 * 1024),  # 10MB chunks max
                'total_chunk_count': (file_size // (10 * 1024 * 1024)) + 1
            }
        }
        
        try:
            # Initialize upload
            response = requests.post(init_url, headers=headers, json=init_payload)
            response.raise_for_status()
            
            data = response.json()
            if data.get('code') != 0:
                logger.error(f"TikTok upload init failed: {data.get('message')}")
                raise Exception(f"Upload init failed: {data.get('message')}")
            
            upload_id = data['data']['upload_id']
            
            # Step 2: Upload video chunks
            chunk_size = 10 * 1024 * 1024  # 10MB
            chunk_number = 1
            
            with open(video_file_path, 'rb') as video_file:
                while True:
                    chunk = video_file.read(chunk_size)
                    if not chunk:
                        break
                    
                    chunk_url = "https://open-api.tiktok.com/share/video/upload/part/"
                    files = {
                        'video': chunk
                    }
                    chunk_data = {
                        'upload_id': upload_id,
                        'part_number': chunk_number
                    }
                    
                    chunk_response = requests.post(
                        chunk_url, 
                        headers={'Authorization': f'Bearer {access_token}'}, 
                        files=files, 
                        data=chunk_data
                    )
                    chunk_response.raise_for_status()
                    
                    chunk_result = chunk_response.json()
                    if chunk_result.get('code') != 0:
                        raise Exception(f"Chunk upload failed: {chunk_result.get('message')}")
                    
                    chunk_number += 1
            
            # Step 3: Complete upload
            complete_url = "https://open-api.tiktok.com/share/video/upload/complete/"
            complete_payload = {'upload_id': upload_id}
            
            complete_response = requests.post(complete_url, headers=headers, json=complete_payload)
            complete_response.raise_for_status()
            
            complete_data = complete_response.json()
            if complete_data.get('code') != 0:
                raise Exception(f"Upload complete failed: {complete_data.get('message')}")
            
            return {
                'upload_id': upload_id,
                'video_id': complete_data['data'].get('video_id'),
                'status': 'uploaded'
            }
            
        except requests.RequestException as e:
            logger.error(f"TikTok video upload failed: {e}")
            raise Exception(f"Video upload failed: {e}")
    
    def publish_video(self, access_token: str, video_id: str, post_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Publish uploaded video to TikTok
        
        Args:
            access_token: User's access token
            video_id: ID of uploaded video
            post_info: Post information (title, description, privacy settings, etc.)
            
        Returns:
            Publish response
        """
        url = "https://open-api.tiktok.com/share/video/publish/"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }
        
        payload = {
            'video_id': video_id,
            'post_info': {
                'title': post_info.get('title', ''),
                'privacy_level': post_info.get('privacy_level', 'SELF_ONLY'),  # PUBLIC_TO_EVERYONE, MUTUAL_FOLLOW_FRIEND, SELF_ONLY
                'disable_duet': post_info.get('disable_duet', False),
                'disable_comment': post_info.get('disable_comment', False),
                'disable_stitch': post_info.get('disable_stitch', False),
                'video_cover_timestamp_ms': post_info.get('video_cover_timestamp_ms', 1000),
            }
        }
        
        # Add brand content and disclosure if specified
        if post_info.get('brand_content_toggle'):
            payload['post_info']['brand_content_toggle'] = True
            if post_info.get('brand_organic_toggle'):
                payload['post_info']['brand_organic_toggle'] = True
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            if data.get('code') != 0:
                logger.error(f"TikTok video publish failed: {data.get('message')}")
                raise Exception(f"Video publish failed: {data.get('message')}")
            
            return {
                'publish_id': data['data'].get('publish_id'),
                'status': 'published'
            }
            
        except requests.RequestException as e:
            logger.error(f"TikTok video publish failed: {e}")
            raise Exception(f"Video publish failed: {e}")
    
    def get_video_list(self, access_token: str, cursor: int = 0, max_count: int = 20) -> Dict[str, Any]:
        """
        Get list of user's TikTok videos
        
        Args:
            access_token: User's access token
            cursor: Pagination cursor
            max_count: Maximum number of videos to return
            
        Returns:
            List of videos
        """
        url = f"{self.BASE_URL}/open_api/v1.3/video/list/"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }
        
        payload = {
            'cursor': cursor,
            'max_count': min(max_count, 100),  # TikTok API limit
            'fields': ['id', 'create_time', 'cover_image_url', 'share_url', 'video_description', 'duration', 'height', 'width']
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            if data.get('code') != 0:
                logger.error(f"TikTok video list request failed: {data.get('message')}")
                raise Exception(f"Video list request failed: {data.get('message')}")
            
            return data.get('data', {})
            
        except requests.RequestException as e:
            logger.error(f"TikTok video list request failed: {e}")
            raise Exception(f"Video list request failed: {e}")
    
    def get_video_analytics(self, access_token: str, video_ids: List[str], fields: List[str] = None) -> Dict[str, Any]:
        """
        Get analytics for TikTok videos
        
        Args:
            access_token: User's access token
            video_ids: List of video IDs
            fields: Analytics fields to retrieve
            
        Returns:
            Video analytics data
        """
        if not fields:
            fields = ['video_id', 'views', 'likes', 'comments', 'shares']
        
        url = f"{self.BASE_URL}/open_api/v1.3/video/analytics/"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }
        
        payload = {
            'video_ids': video_ids[:100],  # TikTok API limit
            'fields': fields
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            if data.get('code') != 0:
                logger.error(f"TikTok video analytics request failed: {data.get('message')}")
                raise Exception(f"Video analytics request failed: {data.get('message')}")
            
            return data.get('data', {})
            
        except requests.RequestException as e:
            logger.error(f"TikTok video analytics request failed: {e}")
            raise Exception(f"Video analytics request failed: {e}")
    
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
            return bool(user_info.get('open_id'))
        except Exception as e:
            logger.error(f"TikTok token validation failed: {e}")
            return False
    
    def revoke_token(self, access_token: str) -> bool:
        """
        Revoke access token
        
        Args:
            access_token: Access token to revoke
            
        Returns:
            True if revoked successfully, False otherwise
        """
        if not self._lazy_init():
            return False
        
        url = f"{self.BASE_URL}/open_api/v1.3/oauth2/revoke/"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }
        
        payload = {
            'client_key': self.client_key,  # TikTok uses client_key per official docs
            'client_secret': self.client_secret,
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            return data.get('code') == 0
            
        except Exception as e:
            logger.error(f"TikTok token revocation failed: {e}")
            return False
