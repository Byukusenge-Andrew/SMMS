"""
Twitter/X API Integration Service
"""
import os
import logging
import tweepy
from typing import Dict, List, Optional, Any, Tuple
from django.conf import settings
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class TwitterService:
    """Service class for Twitter/X API integration"""
    
    def __init__(self):
        """Initialize Twitter API clients"""
        self.api_key = None
        self.api_secret = None
        self.bearer_token = None
        self.access_token = None
        self.access_token_secret = None
        self.api_v1 = None
        self.client_v2 = None
        self._initialized = False
    
    def _lazy_init(self):
        """Lazy initialization of Twitter API clients"""
        if self._initialized:
            return True
            
        self.api_key = os.getenv('TWITTER_API_KEY')
        self.api_secret = os.getenv('TWITTER_API_KEY_SECRET')
        self.bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        self.access_token = os.getenv('TWITTER_ACCESS_TOKEN')
        self.access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
        
        # Validate required credentials
        if not all([self.api_key, self.api_secret, self.bearer_token, 
                   self.access_token, self.access_token_secret]):
            logger.error("Missing Twitter API credentials")
            return False
        
        # Initialize API clients
        try:
            self._init_api_clients()
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Twitter API clients: {e}")
            return False
    
    def _init_api_clients(self):
        """Initialize Twitter API v1.1 and v2 clients"""
        try:
            # Twitter API v1.1 client (for media uploads and some legacy features)
            auth_v1 = tweepy.OAuthHandler(self.api_key, self.api_secret)
            auth_v1.set_access_token(self.access_token, self.access_token_secret)
            self.api_v1 = tweepy.API(auth_v1, wait_on_rate_limit=True)
            
            # Twitter API v2 client (for modern features)
            self.client_v2 = tweepy.Client(
                bearer_token=self.bearer_token,
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret,
                wait_on_rate_limit=True
            )
            
            logger.info("Twitter API clients initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Twitter API clients: {e}")
            raise

    def _build_clients(self, access_token: Optional[str], access_token_secret: Optional[str]) -> Tuple[Optional[Any], Optional[Any]]:
        """Build per-user clients if user tokens provided, else use app-level clients."""
        # If user tokens provided, build user-scoped clients
        if access_token and access_token_secret:
            try:
                auth_v1 = tweepy.OAuthHandler(self.api_key, self.api_secret)
                auth_v1.set_access_token(access_token, access_token_secret)
                api_v1 = tweepy.API(auth_v1, wait_on_rate_limit=True)

                client_v2 = tweepy.Client(
                    consumer_key=self.api_key,
                    consumer_secret=self.api_secret,
                    access_token=access_token,
                    access_token_secret=access_token_secret,
                    wait_on_rate_limit=True
                )
                return api_v1, client_v2
            except Exception as e:
                logger.error(f"Failed to build user-scoped Twitter clients: {e}")
                # Fall through to app-level
        
        # Fallback to app-level
        if not self._lazy_init():
            return None, None
        return self.api_v1, self.client_v2
    
    def verify_credentials(self, account: Optional[Any] = None) -> Dict[str, Any]:
        """Verify Twitter API credentials and return user info. If account provided, use user tokens."""
        access_token = getattr(account, 'access_token', None) if account else None
        access_token_secret = getattr(account, 'refresh_token', None) if account else None  # using refresh_token to store OAuth1 secret
        api_v1, client_v2 = self._build_clients(access_token, access_token_secret)
        if not client_v2:
            return {'success': False, 'error': 'Twitter API credentials are not properly configured'}
            
        try:
            # Get authenticated user info
            user = client_v2.get_me(
                user_fields=['id', 'name', 'username', 'profile_image_url', 
                           'public_metrics', 'description', 'location', 'verified']
            )
            
            if user.data:
                return {
                    'success': True,
                    'user_id': user.data.id,
                    'name': user.data.name,
                    'username': user.data.username,
                    'profile_image_url': user.data.profile_image_url,
                    'description': user.data.description or '',
                    'location': user.data.location or '',
                    'verified': user.data.verified or False,
                    'followers_count': user.data.public_metrics['followers_count'],
                    'following_count': user.data.public_metrics['following_count'],
                    'tweet_count': user.data.public_metrics['tweet_count'],
                }
            else:
                return {'success': False, 'error': 'Unable to verify credentials'}
                
        except Exception as e:
            logger.error(f"Twitter credentials verification failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def post_tweet(self, text: str, media_paths: List[str] = None, account: Optional[Any] = None) -> Dict[str, Any]:
        """
        Post a tweet with optional media
        
        Args:
            text: Tweet text content
            media_paths: List of local file paths to media files
            account: optional SocialMediaAccount with user tokens
            
        Returns:
            Dict containing success status and tweet info
        """
        access_token = getattr(account, 'access_token', None) if account else None
        access_token_secret = getattr(account, 'refresh_token', None) if account else None
        api_v1, client_v2 = self._build_clients(access_token, access_token_secret)
        if not client_v2:
            return {'success': False, 'error': 'Twitter API credentials are not properly configured'}
            
        try:
            media_ids = []
            
            # Upload media if provided and if api_v1 available (OAuth1 required for v1.1 upload)
            if media_paths and api_v1:
                for media_path in media_paths:
                    if os.path.exists(media_path):
                        media = api_v1.media_upload(media_path)
                        media_ids.append(media.media_id)
                        logger.info(f"Uploaded media: {media_path}")
                    else:
                        logger.warning(f"Media file not found: {media_path}")
            elif media_paths and not api_v1:
                logger.warning("Media upload skipped: OAuth1 client not available; posting text-only tweet")
            
            # Post tweet
            tweet = client_v2.create_tweet(
                text=text,
                media_ids=media_ids if media_ids else None
            )
            
            if tweet.data:
                logger.info(f"Tweet posted successfully: {tweet.data['id']}")
                return {
                    'success': True,
                    'tweet_id': tweet.data['id'],
                    'text': text,
                    'media_count': len(media_ids),
                    'url': f"https://twitter.com/i/web/status/{tweet.data['id']}"
                }
            else:
                return {'success': False, 'error': 'Failed to post tweet'}
                
        except Exception as e:
            logger.error(f"Failed to post tweet: {e}")
            return {'success': False, 'error': str(e)}
    
    def delete_tweet(self, tweet_id: str, account: Optional[Any] = None) -> Dict[str, Any]:
        """Delete a tweet"""
        access_token = getattr(account, 'access_token', None) if account else None
        access_token_secret = getattr(account, 'refresh_token', None) if account else None
        _, client_v2 = self._build_clients(access_token, access_token_secret)
        if not client_v2:
            return {'success': False, 'error': 'Twitter API credentials are not properly configured'}
            
        try:
            result = client_v2.delete_tweet(tweet_id)
            
            if result.data.get('deleted'):
                logger.info(f"Tweet deleted successfully: {tweet_id}")
                return {'success': True, 'tweet_id': tweet_id}
            else:
                return {'success': False, 'error': 'Failed to delete tweet'}
                
        except Exception as e:
            logger.error(f"Failed to delete tweet {tweet_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_user_tweets(self, user_id: str = None, count: int = 10, account: Optional[Any] = None) -> Dict[str, Any]:
        """
        Get recent tweets from a user (default: authenticated user)
        
        Args:
            user_id: Twitter user ID (if None, gets authenticated user's tweets)
            count: Number of tweets to retrieve (max 100)
            account: optional SocialMediaAccount with user tokens
            
        Returns:
            Dict containing tweets data
        """
        access_token = getattr(account, 'access_token', None) if account else None
        access_token_secret = getattr(account, 'refresh_token', None) if account else None
        _, client_v2 = self._build_clients(access_token, access_token_secret)
        if not client_v2:
            return {'success': False, 'error': 'Twitter API credentials are not properly configured'}
            
        try:
            if not user_id:
                # Get authenticated user's ID
                me = client_v2.get_me()
                user_id = me.data.id
            
            tweets = client_v2.get_users_tweets(
                id=user_id,
                max_results=min(count, 100),
                tweet_fields=['id', 'text', 'created_at', 'public_metrics', 
                             'context_annotations', 'attachments'],
                expansions=['attachments.media_keys'],
                media_fields=['url', 'preview_image_url', 'type']
            )
            
            tweet_list = []
            if tweets.data:
                for tweet in tweets.data:
                    tweet_data = {
                        'id': tweet.id,
                        'text': tweet.text,
                        'created_at': tweet.created_at.isoformat(),
                        'retweet_count': tweet.public_metrics['retweet_count'],
                        'like_count': tweet.public_metrics['like_count'],
                        'reply_count': tweet.public_metrics['reply_count'],
                        'quote_count': tweet.public_metrics['quote_count'],
                        'url': f"https://twitter.com/i/web/status/{tweet.id}"
                    }
                    
                    # Add media information if available
                    if hasattr(tweet, 'attachments') and tweet.attachments:
                        tweet_data['has_media'] = True
                        tweet_data['media_keys'] = tweet.attachments.get('media_keys', [])
                    else:
                        tweet_data['has_media'] = False
                    
                    tweet_list.append(tweet_data)
            
            return {
                'success': True,
                'tweets': tweet_list,
                'count': len(tweet_list)
            }
            
        except Exception as e:
            logger.error(f"Failed to get user tweets: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_tweet_analytics(self, tweet_id: str, account: Optional[Any] = None) -> Dict[str, Any]:
        """Get analytics/metrics for a specific tweet"""
        access_token = getattr(account, 'access_token', None) if account else None
        access_token_secret = getattr(account, 'refresh_token', None) if account else None
        _, client_v2 = self._build_clients(access_token, access_token_secret)
        if not client_v2:
            return {'success': False, 'error': 'Twitter API credentials are not properly configured'}
            
        try:
            tweet = client_v2.get_tweet(
                tweet_id,
                tweet_fields=['public_metrics', 'created_at', 'context_annotations'],
                expansions=['author_id'],
                user_fields=['username', 'name']
            )
            
            if tweet.data:
                metrics = tweet.data.public_metrics
                return {
                    'success': True,
                    'tweet_id': tweet_id,
                    'metrics': {
                        'retweet_count': metrics['retweet_count'],
                        'like_count': metrics['like_count'],
                        'reply_count': metrics['reply_count'],
                        'quote_count': metrics['quote_count'],
                        'impression_count': metrics.get('impression_count', 0)
                    },
                    'created_at': tweet.data.created_at.isoformat(),
                    'text': tweet.data.text,
                    'url': f"https://twitter.com/i/web/status/{tweet_id}"
                }
            else:
                return {'success': False, 'error': 'Tweet not found'}
                
        except Exception as e:
            logger.error(f"Failed to get tweet analytics for {tweet_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def search_tweets(self, query: str, count: int = 10, account: Optional[Any] = None) -> Dict[str, Any]:
        """
        Search for tweets based on query
        
        Args:
            query: Search query (can include hashtags, mentions, keywords)
            count: Number of tweets to retrieve (max 100)
            account: optional SocialMediaAccount with user tokens
            
        Returns:
            Dict containing search results
        """
        access_token = getattr(account, 'access_token', None) if account else None
        access_token_secret = getattr(account, 'refresh_token', None) if account else None
        _, client_v2 = self._build_clients(access_token, access_token_secret)
        if not client_v2:
            return {'success': False, 'error': 'Twitter API credentials are not properly configured'}
            
        try:
            tweets = client_v2.search_recent_tweets(
                query=query,
                max_results=min(count, 100),
                tweet_fields=['id', 'text', 'created_at', 'public_metrics', 'author_id'],
                expansions=['author_id'],
                user_fields=['username', 'name', 'profile_image_url']
            )
            
            tweet_list = []
            if tweets.data:
                # Create a mapping of user IDs to user info
                users = {user.id: user for user in tweets.includes.get('users', [])}
                
                for tweet in tweets.data:
                    author = users.get(tweet.author_id)
                    tweet_data = {
                        'id': tweet.id,
                        'text': tweet.text,
                        'created_at': tweet.created_at.isoformat(),
                        'author': {
                            'id': tweet.author_id,
                            'username': author.username if author else 'unknown',
                            'name': author.name if author else 'Unknown User',
                            'profile_image_url': author.profile_image_url if author else ''
                        },
                        'metrics': {
                            'retweet_count': tweet.public_metrics['retweet_count'],
                            'like_count': tweet.public_metrics['like_count'],
                            'reply_count': tweet.public_metrics['reply_count'],
                        },
                        'url': f"https://twitter.com/i/web/status/{tweet.id}"
                    }
                    tweet_list.append(tweet_data)
            
            return {
                'success': True,
                'query': query,
                'tweets': tweet_list,
                'count': len(tweet_list)
            }
            
        except Exception as e:
            logger.error(f"Failed to search tweets: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_rate_limit_status(self, account: Optional[Any] = None) -> Dict[str, Any]:
        """Get current rate limit status for various endpoints"""
        access_token = getattr(account, 'access_token', None) if account else None
        access_token_secret = getattr(account, 'refresh_token', None) if account else None
        _, client_v2 = self._build_clients(access_token, access_token_secret)
        if not client_v2:
            return {'success': False, 'error': 'Twitter API credentials are not properly configured'}
            
        try:
            # This is a simple check using the verify_credentials endpoint
            user = client_v2.get_me()
            
            return {
                'success': True,
                'message': 'API is accessible',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to check rate limit status: {e}")
            return {'success': False, 'error': str(e)}


# Singleton instance
twitter_service = TwitterService()
