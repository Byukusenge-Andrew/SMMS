#!/usr/bin/env python
"""
Quick manual test for analytics endpoints
"""
import os
import sys
import django

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from django.contrib.auth.models import User
from apps.integrations.models import SocialMediaAccount
from apps.analytics.real_analytics_collector import RealAnalyticsCollector
from apps.analytics.models import AnalyticsData

def quick_test():
    """Quick test of analytics functionality"""
    print("🔥 Quick Analytics Test")
    print("=" * 30)
    
    try:
        # Get existing test user
        user = User.objects.filter(username='testuser').first()
        if not user:
            print("❌ No test user found")
            return False
        
        print(f"✅ Found user: {user.username}")
        
        # Check connected accounts
        accounts = SocialMediaAccount.objects.filter(user=user, is_active=True)
        print(f"📱 Connected accounts: {accounts.count()}")
        
        for account in accounts:
            print(f"   - {account.platform}: @{account.username} ({account.followers_count} followers)")
        
        if not accounts.exists():
            print("❌ No connected accounts found")
            return False
        
        # Test collector
        collector = RealAnalyticsCollector()
        print("🚀 Analytics collector initialized")
        
        # Test platform insights
        insights = collector.get_platform_insights(user, days=30)
        platform_count = len(insights)
        print(f"📊 Platform insights: {platform_count} platforms")
        
        if insights:
            for platform, data in insights.items():
                print(f"   🔍 {platform}:")
                print(f"      - Followers: {data['account_info']['followers']}")
                print(f"      - Growth: {data['growth_metrics']['follower_growth_percentage']}%")
        else:
            print("⚠️  No insights generated yet. Collect analytics data first or ensure accounts have metrics recorded.")
        
        # Test data collection
        print("\n📈 Testing data collection...")
        try:
            results = collector.collect_all_user_analytics(user)
            if results['errors']:
                print(f"⚠️  Data collection completed with {len(results['errors'])} errors")
                for error in results['errors']:
                    print(f"   - {error['platform']} (@{error['username']}): {error['error']}")
            else:
                print("✅ Data collection completed without errors")
        except Exception as e:
            print(f"❌ Data collection error: {e}")
            return False
        
        # Check analytics data in database
        analytics_count = AnalyticsData.objects.filter(user=user).count()
        print(f"📊 Total analytics records: {analytics_count}")
        
        if analytics_count > 0:
            recent = AnalyticsData.objects.filter(user=user).order_by('-created_at')[:3]
            print("📋 Recent data:")
            for data in recent:
                print(f"   - {data.platform} | {data.metric_type}: {data.value}")
        
        print("\n🎉 Quick test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    quick_test()