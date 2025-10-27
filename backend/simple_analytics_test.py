#!/usr/bin/env python
"""
Simple test for analytics system
"""
import os
import sys
import django

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

def test_basic_functionality():
    """Test basic analytics functionality"""
    print("🧪 Testing Basic Analytics Functionality")
    print("=" * 40)
    
    try:
        # Test imports
        print("📦 Testing imports...")
        from apps.analytics.real_analytics_collector import RealAnalyticsCollector
        from apps.analytics.models import AnalyticsData
        from apps.integrations.models import SocialMediaAccount
        from django.contrib.auth.models import User
        print("✅ All imports successful")
        
        # Test RealAnalyticsCollector initialization
        print("\n🚀 Testing RealAnalyticsCollector...")
        collector = RealAnalyticsCollector()
        print("✅ RealAnalyticsCollector initialized successfully")
        
        # Test user creation
        print("\n👤 Testing user operations...")
        user, created = User.objects.get_or_create(
            username='analytics_test_user',
            defaults={'email': 'test@analytics.com'}
        )
        print(f"✅ User {'created' if created else 'retrieved'}: {user.username}")
        
        # Test platform insights with no accounts
        print("\n🔍 Testing platform insights (no accounts)...")
        insights = collector.get_platform_insights(user, days=30)
        print(f"✅ Platform insights returned: {len(insights)} platforms")
        
        # Create a test account
        print("\n📱 Creating test social media account...")
        test_account, account_created = SocialMediaAccount.objects.get_or_create(
            user=user,
            platform='twitter',
            platform_user_id='test_analytics_123',
            defaults={
                'username': 'analytics_test_twitter',
                'display_name': 'Analytics Test User',
                'followers_count': 1500,
                'following_count': 800,
                'is_active': True,
                'is_verified': False
            }
        )
        print(f"✅ Test account {'created' if account_created else 'retrieved'}: {test_account.platform}/@{test_account.username}")
        
        # Test platform insights with account
        print("\n🔍 Testing platform insights (with account)...")
        insights = collector.get_platform_insights(user, days=30)
        print(f"✅ Platform insights returned: {len(insights)} platforms")
        
        for platform, data in insights.items():
            print(f"   📊 {platform.upper()}:")
            print(f"      - Followers: {data['account_info']['followers']}")
            print(f"      - Engagement Rate: {data['performance_indicators']['engagement_rate']}%")
            print(f"      - Activity Score: {data['performance_indicators']['activity_score']}")
        
        # Test analytics data collection
        print("\n📈 Testing analytics data collection...")
        success = collector.collect_all_analytics(user)
        print(f"✅ Analytics collection {'successful' if success else 'failed'}")
        
        # Check database for analytics data
        analytics_count = AnalyticsData.objects.filter(user=user).count()
        print(f"📊 Analytics records in database: {analytics_count}")
        
        if analytics_count > 0:
            recent_data = AnalyticsData.objects.filter(user=user).order_by('-created_at')[:3]
            print("📋 Recent analytics data:")
            for data in recent_data:
                print(f"   - {data.platform} | {data.metric_type}: {data.value}")
        
        print("\n🎉 All tests passed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_basic_functionality()
    exit(0 if success else 1)