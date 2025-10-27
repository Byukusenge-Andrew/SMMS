"""
Real Analytics Data Collection Service
Fetches actual metrics from connected social media accounts
"""

import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import models
from django.db.models import Q
from apps.integrations.models import SocialMediaAccount
from apps.integrations.social_media_integrator import TwitterIntegrator, LinkedInIntegrator
from apps.analytics.models import AnalyticsData
import requests

logger = logging.getLogger(__name__)


class RealAnalyticsCollector:
    """Collects real analytics data from connected social media accounts"""
    
    def __init__(self):
        self.twitter_integrator = TwitterIntegrator()
        self.linkedin_integrator = LinkedInIntegrator()
    
    def collect_all_user_analytics(self, user):
        """Collect analytics for all connected accounts of a user"""
        results = {
            'success': [],
            'errors': [],
            'summary': {
                'total_followers': 0,
                'total_connections': 0,
                'platforms_connected': [],
                'last_updated': timezone.now()
            }
        }
        
        # Get all connected social media accounts
        connected_accounts = SocialMediaAccount.objects.filter(
            user=user, 
            is_active=True
        )
        
        for account in connected_accounts:
            try:
                platform_data = self._collect_platform_analytics(account)
                if platform_data['success']:
                    results['success'].append({
                        'platform': account.platform,
                        'username': account.username,
                        'data': platform_data['data']
                    })
                    
                    # Update summary
                    results['summary']['total_followers'] += platform_data['data'].get('followers_count', 0)
                    results['summary']['total_connections'] += platform_data['data'].get('connections_count', 0)
                    results['summary']['platforms_connected'].append(account.platform)
                    
                    # Update account metrics
                    self._update_account_metrics(account, platform_data['data'])
                    
                else:
                    results['errors'].append({
                        'platform': account.platform,
                        'username': account.username,
                        'error': platform_data['error']
                    })
                    
            except Exception as e:
                logger.error(f"Error collecting analytics for {account.platform} - {account.username}: {e}")
                results['errors'].append({
                    'platform': account.platform,
                    'username': account.username,
                    'error': str(e)
                })
        
        return results

    def get_platform_insights(self, user, platform=None, days=30):
        """Get detailed insights for specific platform or all platforms"""
        insights = {}
        
        # Get connected accounts
        connected_accounts = SocialMediaAccount.objects.filter(user=user, is_active=True)
        if platform:
            connected_accounts = connected_accounts.filter(platform=platform)
        
        # Date range for analysis
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        for account in connected_accounts:
            platform_name = account.platform
            
            # Get analytics data for this platform
            platform_analytics = AnalyticsData.objects.filter(
                user=user,
                platform=platform_name,
                date__gte=start_date
            )
            
            # Calculate growth metrics
            follower_data = platform_analytics.filter(metric_type='followers').order_by('date')
            follower_growth = 0
            if follower_data.count() >= 2:
                latest = follower_data.last()
                earliest = follower_data.first()
                if latest and earliest and earliest.value > 0:
                    follower_growth = ((latest.value - earliest.value) / earliest.value) * 100
            
            # Engagement metrics
            engagement_metrics = platform_analytics.filter(
                metric_type__in=['likes', 'shares', 'comments', 'views']
            ).aggregate(
                total_likes=models.Sum('value', filter=Q(metric_type='likes')),
                total_shares=models.Sum('value', filter=Q(metric_type='shares')),
                total_comments=models.Sum('value', filter=Q(metric_type='comments')),
                total_views=models.Sum('value', filter=Q(metric_type='views'))
            )
            
            # Post frequency
            posts_count = platform_analytics.filter(metric_type='posts').count()
            
            insights[platform_name] = {
                'account_info': {
                    'username': account.username,
                    'display_name': account.display_name,
                    'followers': account.followers_count or 0,
                    'following': account.following_count or 0,
                    'verified': account.is_verified,
                    'profile_image': account.profile_image_url
                },
                'growth_metrics': {
                    'follower_growth_percentage': round(follower_growth, 2),
                    'posts_in_period': posts_count,
                    'avg_posts_per_day': round(posts_count / days, 2) if days > 0 else 0
                },
                'engagement_metrics': {
                    'total_likes': engagement_metrics['total_likes'] or 0,
                    'total_shares': engagement_metrics['total_shares'] or 0,
                    'total_comments': engagement_metrics['total_comments'] or 0,
                    'total_views': engagement_metrics['total_views'] or 0,
                    'avg_engagement_per_post': round(
                        ((engagement_metrics['total_likes'] or 0) + 
                         (engagement_metrics['total_shares'] or 0) + 
                         (engagement_metrics['total_comments'] or 0)) / max(posts_count, 1), 2
                    )
                },
                'performance_indicators': {
                    'engagement_rate': self._calculate_engagement_rate(account, engagement_metrics, posts_count),
                    'reach_estimate': self._estimate_reach(account, engagement_metrics),
                    'activity_score': self._calculate_activity_score(posts_count, days)
                }
            }
        
        return insights
    
    def _calculate_engagement_rate(self, account, engagement_metrics, posts_count):
        """Calculate engagement rate for an account"""
        if not account.followers_count or account.followers_count == 0 or posts_count == 0:
            return 0
        
        total_engagement = (
            (engagement_metrics['total_likes'] or 0) +
            (engagement_metrics['total_shares'] or 0) +
            (engagement_metrics['total_comments'] or 0)
        )
        
        # Engagement rate = (Total Engagement / (Followers * Posts)) * 100
        return round((total_engagement / (account.followers_count * posts_count)) * 100, 2)
    
    def _estimate_reach(self, account, engagement_metrics):
        """Estimate reach based on engagement and follower count"""
        if not account.followers_count:
            return 0
        
        # Simple reach estimation: typically 10-30% of followers see organic posts
        base_reach = account.followers_count * 0.2  # 20% average
        
        # Boost based on engagement
        engagement_boost = (engagement_metrics['total_views'] or 0) * 0.1
        
        return round(base_reach + engagement_boost)
    
    def _calculate_activity_score(self, posts_count, days):
        """Calculate activity score (0-100) based on posting frequency"""
        if days == 0:
            return 0
        
        posts_per_day = posts_count / days
        
        # Score based on ideal posting frequency (1-2 posts per day = 100)
        if posts_per_day >= 1:
            return min(100, posts_per_day * 50)
        else:
            return round(posts_per_day * 100, 2)
    
    def _collect_platform_analytics(self, account):
        """Collect analytics for a specific platform account"""
        try:
            if account.platform == 'linkedin':
                return self._collect_linkedin_analytics(account)
            elif account.platform == 'twitter':
                return self._collect_twitter_analytics(account)
            elif account.platform == 'facebook':
                return self._collect_facebook_analytics(account)
            else:
                return {
                    'success': False,
                    'error': f'Analytics not implemented for {account.platform}'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _collect_linkedin_analytics(self, account):
        """Collect LinkedIn analytics using access token"""
        try:
            # Get profile data using stored access token
            profile_result = self.linkedin_integrator.get_profile(account.access_token)
            
            if not profile_result.get('success'):
                return {
                    'success': False,
                    'error': profile_result.get('error', 'Failed to fetch LinkedIn profile')
                }
            
            profile = profile_result['profile']
            
            # Store metrics in analytics data
            today = timezone.now().date()
            
            analytics_data = {
                'followers_count': profile.get('connection_count', 0),
                'connections_count': profile.get('connection_count', 0),
                'profile_views': 0,  # LinkedIn API doesn't provide this in basic scope
                'posts_count': 0,    # Would need additional API calls
                'engagement_rate': 0,
                'platform': 'linkedin',
                'last_updated': timezone.now()
            }
            
            # Save follower count to AnalyticsData
            self._save_metric(
                user=account.user,
                social_account=account,
                metric_type='followers',
                value=analytics_data['followers_count'],
                platform='linkedin',
                date=today
            )
            
            return {
                'success': True,
                'data': analytics_data
            }
            
        except Exception as e:
            logger.error(f"LinkedIn analytics error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _collect_twitter_analytics(self, account):
        """Collect Twitter analytics using access token"""
        try:
            # For Twitter, we'll use the stored credentials
            # Note: Twitter API v2 has strict rate limits on free tier
            
            if not account.access_token:
                return {
                    'success': False,
                    'error': 'No access token available for Twitter account'
                }
            
            headers = {
                'Authorization': f'Bearer {account.access_token}',
                'Content-Type': 'application/json'
            }
            
            # Get user profile with metrics
            user_url = 'https://api.twitter.com/2/users/me'
            params = {
                'user.fields': 'public_metrics,verified,profile_image_url'
            }
            
            response = requests.get(user_url, headers=headers, params=params, timeout=10)
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'error': f'Twitter API error: {response.status_code} - {response.text}'
                }
            
            user_data = response.json()
            metrics = user_data.get('data', {}).get('public_metrics', {})
            
            today = timezone.now().date()
            
            analytics_data = {
                'followers_count': metrics.get('followers_count', 0),
                'following_count': metrics.get('following_count', 0),
                'tweet_count': metrics.get('tweet_count', 0),
                'like_count': metrics.get('like_count', 0),
                'platform': 'twitter',
                'last_updated': timezone.now()
            }
            
            # Save metrics to AnalyticsData
            for metric_name, value in metrics.items():
                metric_type = self._map_twitter_metric(metric_name)
                if metric_type:
                    self._save_metric(
                        user=account.user,
                        social_account=account,
                        metric_type=metric_type,
                        value=value,
                        platform='twitter',
                        date=today
                    )
            
            return {
                'success': True,
                'data': analytics_data
            }
            
        except Exception as e:
            logger.error(f"Twitter analytics error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _collect_facebook_analytics(self, account):
        """Collect Facebook analytics using access token"""
        try:
            if not account.access_token:
                return {
                    'success': False,
                    'error': 'No access token available for Facebook account'
                }
            
            # Facebook Graph API
            base_url = 'https://graph.facebook.com/v18.0'
            
            # Get user profile
            profile_url = f'{base_url}/me'
            params = {
                'fields': 'id,name,picture,friends',
                'access_token': account.access_token
            }
            
            response = requests.get(profile_url, params=params, timeout=10)
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'error': f'Facebook API error: {response.status_code} - {response.text}'
                }
            
            profile_data = response.json()
            
            today = timezone.now().date()
            
            analytics_data = {
                'followers_count': 0,  # Facebook doesn't provide follower count for personal profiles
                'friends_count': profile_data.get('friends', {}).get('summary', {}).get('total_count', 0),
                'platform': 'facebook',
                'last_updated': timezone.now()
            }
            
            return {
                'success': True,
                'data': analytics_data
            }
            
        except Exception as e:
            logger.error(f"Facebook analytics error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _map_twitter_metric(self, twitter_metric):
        """Map Twitter metric names to our AnalyticsData metric types"""
        mapping = {
            'followers_count': 'followers',
            'tweet_count': 'posts',
            'like_count': 'likes',
            'following_count': 'following'
        }
        return mapping.get(twitter_metric)
    
    def _save_metric(self, user, social_account, metric_type, value, platform, date):
        """Save or update a metric in AnalyticsData"""
        try:
            analytics_data, created = AnalyticsData.objects.update_or_create(
                user=user,
                social_account=social_account,
                metric_type=metric_type,
                platform=platform,
                date=date,
                defaults={'value': value}
            )
            return analytics_data
        except Exception as e:
            logger.error(f"Error saving metric {metric_type}: {e}")
            return None
    
    def _update_account_metrics(self, account, data):
        """Update the social media account with latest metrics"""
        try:
            if 'followers_count' in data:
                account.followers_count = data['followers_count']
            if 'following_count' in data:
                account.following_count = data['following_count']
            
            account.last_synced = timezone.now()
            account.save(update_fields=['followers_count', 'following_count', 'last_synced'])
            
        except Exception as e:
            logger.error(f"Error updating account metrics: {e}")
    
    def get_platform_insights(self, user, platform=None, days=30):
        """Get analytics insights for specific platform or all platforms"""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        query = AnalyticsData.objects.filter(
            user=user,
            date__gte=start_date,
            date__lte=end_date
        )
        
        if platform:
            query = query.filter(platform=platform)
        
        # Group by platform and metric type
        insights = {}
        
        for data in query:
            platform_key = data.platform
            if platform_key not in insights:
                insights[platform_key] = {}
            
            metric_key = data.metric_type
            if metric_key not in insights[platform_key]:
                insights[platform_key][metric_key] = []
            
            insights[platform_key][metric_key].append({
                'date': data.date,
                'value': data.value
            })
        
        # Calculate trends and changes
        for platform_key in insights:
            for metric_key in insights[platform_key]:
                values = insights[platform_key][metric_key]
                if len(values) >= 2:
                    latest = values[-1]['value']
                    previous = values[-2]['value']
                    change = latest - previous
                    change_percent = (change / previous * 100) if previous > 0 else 0
                    
                    insights[platform_key][f'{metric_key}_change'] = change
                    insights[platform_key][f'{metric_key}_change_percent'] = round(change_percent, 2)
        
        return insights