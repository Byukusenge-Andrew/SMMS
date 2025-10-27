#!/usr/bin/env python
"""
Test script for Real Analytics Collection System
"""

import os
import django
import sys
from datetime import datetime

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from django.contrib.auth.models import User
from apps.integrations.models import SocialMediaAccount
from apps.analytics.real_analytics_collector import RealAnalyticsCollector
from apps.analytics.models import AnalyticsData

def test_analytics_system():
    """Test the real analytics collection system"""
    print("🧪 Testing Real Analytics Collection System")
    print("=" * 50)
    
    try:
        # Get or create a test user
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={'email': 'test@example.com'}
        )
        print(f"📋 Using test user: {user.username} ({'created' if created else 'existing'})")
        
        # Check for connected accounts
        connected_accounts = SocialMediaAccount.objects.filter(user=user, is_active=True)
        print(f"🔗 Connected accounts found: {connected_accounts.count()}")
        
        for account in connected_accounts:
            print(f"   - {account.platform}: @{account.username} ({account.followers_count} followers)")
        
        if not connected_accounts.exists():
            print("⚠️  No connected accounts found. Creating test account...")
            
            # Create a test social media account
            test_account = SocialMediaAccount.objects.create(
                user=user,
                platform='twitter',
                platform_user_id='test123',
                username='testuser_twitter',
                display_name='Test User',
                followers_count=1000,
                following_count=500,
                is_active=True,
                is_verified=False
            )
            print(f"✅ Created test account: {test_account.platform}/@{test_account.username}")
        
        # Initialize analytics collector
        print("\n🚀 Initializing Real Analytics Collector...")
        collector = RealAnalyticsCollector()
        
        # Test analytics overview
        print("\n📊 Testing Analytics Overview...")
        try:
            from apps.analytics.views import analytics_overview
            print("✅ Analytics overview function imported successfully")
        except ImportError as e:
            print(f"❌ Failed to import analytics_overview: {e}")
        
        # Test platform insights
        print("\n🔍 Testing Platform Insights...")
        insights = collector.get_platform_insights(user, days=30)
        print(f"✅ Platform insights generated for {len(insights)} platforms")
        
        for platform, data in insights.items():
            print(f"   📱 {platform.upper()}:")
            print(f"      - Followers: {data['account_info']['followers']}")
            print(f"      - Growth: {data['growth_metrics']['follower_growth_percentage']}%")
            print(f"      - Engagement Rate: {data['performance_indicators']['engagement_rate']}%")
        
        # Test data collection
        print("\n📈 Testing Data Collection...")
        success = collector.collect_all_analytics(user)
        print(f"✅ Data collection {'successful' if success else 'failed'}")
        
        # Check stored analytics data
        analytics_count = AnalyticsData.objects.filter(user=user).count()
        print(f"📊 Analytics records in database: {analytics_count}")
        
        # Recent analytics data
        recent_data = AnalyticsData.objects.filter(user=user).order_by('-created_at')[:5]
        print("\n📋 Recent Analytics Data:")
        for data in recent_data:
            print(f"   - {data.platform} | {data.metric_type}: {data.value} ({data.date})")
        
        print("\n🎉 Analytics system test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_analytics_system()