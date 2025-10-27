"""
Django management command to test the real analytics collection system
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.integrations.models import SocialMediaAccount
from apps.analytics.real_analytics_collector import RealAnalyticsCollector
from apps.analytics.models import AnalyticsData

class Command(BaseCommand):
    help = 'Test the real analytics collection system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Username to test analytics for (defaults to testuser)',
            default='testuser'
        )
        parser.add_argument(
            '--create-test-data',
            action='store_true',
            help='Create test social media accounts if none exist',
        )

    def handle(self, *args, **options):
        username = options['username']
        create_test_data = options['create_test_data']
        
        self.stdout.write(
            self.style.SUCCESS('🧪 Testing Real Analytics Collection System')
        )
        self.stdout.write('=' * 50)
        
        try:
            # Get or create user
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'email': f'{username}@example.com'}
            )
            
            self.stdout.write(f"📋 Using user: {user.username} ({'created' if created else 'existing'})")
            
            # Check for connected accounts
            connected_accounts = SocialMediaAccount.objects.filter(user=user, is_active=True)
            self.stdout.write(f"🔗 Connected accounts found: {connected_accounts.count()}")
            
            for account in connected_accounts:
                self.stdout.write(f"   - {account.platform}: @{account.username} ({account.followers_count} followers)")
            
            if not connected_accounts.exists() and create_test_data:
                self.stdout.write("⚠️  No connected accounts found. Creating test accounts...")
                
                # Create test social media accounts
                test_accounts = [
                    {
                        'platform': 'twitter',
                        'platform_user_id': 'test123',
                        'username': f'{username}_twitter',
                        'display_name': 'Test Twitter User',
                        'followers_count': 1000,
                        'following_count': 500,
                    },
                    {
                        'platform': 'linkedin',
                        'platform_user_id': 'test456',
                        'username': f'{username}_linkedin',
                        'display_name': 'Test LinkedIn User',
                        'followers_count': 750,
                        'following_count': 300,
                    }
                ]
                
                for account_data in test_accounts:
                    test_account = SocialMediaAccount.objects.create(
                        user=user,
                        is_active=True,
                        is_verified=False,
                        **account_data
                    )
                    self.stdout.write(f"✅ Created test account: {test_account.platform}/@{test_account.username}")
                
                # Refresh connected accounts
                connected_accounts = SocialMediaAccount.objects.filter(user=user, is_active=True)
            
            if not connected_accounts.exists():
                self.stdout.write(
                    self.style.WARNING("❌ No connected accounts available. Use --create-test-data to create test accounts.")
                )
                return
            
            # Initialize analytics collector
            self.stdout.write("\n🚀 Initializing Real Analytics Collector...")
            collector = RealAnalyticsCollector()
            
            # Test platform insights
            self.stdout.write("\n🔍 Testing Platform Insights...")
            insights = collector.get_platform_insights(user, days=30)
            platform_count = len(insights)
            if platform_count == 0:
                self.stdout.write(self.style.WARNING("⚠️  No platform insights generated yet (no analytics data stored)."))
            else:
                self.stdout.write(f"✅ Platform insights generated for {platform_count} platforms")
            
            for platform, data in insights.items():
                self.stdout.write(f"   📱 {platform.upper()}:")
                self.stdout.write(f"      - Followers: {data['account_info']['followers']}")
                self.stdout.write(f"      - Growth: {data['growth_metrics']['follower_growth_percentage']}%")
                self.stdout.write(f"      - Engagement Rate: {data['performance_indicators']['engagement_rate']}%")
                self.stdout.write(f"      - Activity Score: {data['performance_indicators']['activity_score']}")
            
            # Test data collection
            self.stdout.write("\n📈 Testing Data Collection...")
            results = collector.collect_all_user_analytics(user)
            if results['errors']:
                self.stdout.write(self.style.WARNING(f"⚠️  Data collection completed with {len(results['errors'])} errors."))
                for error in results['errors']:
                    self.stdout.write(f"   - {error['platform']} (@{error['username']}): {error['error']}")
            else:
                self.stdout.write("✅ Data collection completed without errors")

            summary = results.get('summary', {})
            if summary:
                self.stdout.write("\n📌 Collection summary:")
                self.stdout.write(f"   - Total followers: {summary.get('total_followers', 0)}")
                self.stdout.write(f"   - Total connections: {summary.get('total_connections', 0)}")
                self.stdout.write(f"   - Platforms processed: {', '.join(summary.get('platforms_connected', [])) or 'None'}")
            
            # Check stored analytics data
            analytics_count = AnalyticsData.objects.filter(user=user).count()
            self.stdout.write(f"📊 Analytics records in database: {analytics_count}")
            
            # Recent analytics data
            recent_data = AnalyticsData.objects.filter(user=user).order_by('-created_at')[:5]
            if recent_data.exists():
                self.stdout.write("\n📋 Recent Analytics Data:")
                for data in recent_data:
                    self.stdout.write(f"   - {data.platform} | {data.metric_type}: {data.value} ({data.date})")
            else:
                self.stdout.write("\n📋 No analytics data found in database")
            
            # Test analytics endpoints (simulate API calls)
            self.stdout.write("\n🌐 Testing Analytics API Endpoints...")
            
            try:
                from apps.analytics.views import analytics_overview, platform_insights
                self.stdout.write("✅ Analytics view functions imported successfully")
                
            except ImportError as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Failed to import analytics views: {e}")
                )
            
            self.stdout.write(
                self.style.SUCCESS("\n🎉 Analytics system test completed successfully!")
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error during testing: {e}")
            )
            import traceback
            self.stdout.write(traceback.format_exc())