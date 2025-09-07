#!/usr/bin/env python
"""
Test the updated Facebook posting system
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from apps.posts.tasks import publish_scheduled_post
from apps.posts.models import Post
from django.utils import timezone

def test_updated_facebook_system():
    """Test the updated Facebook posting system"""
    
    print("=== Facebook Integration Status ===")
    
    # Check if Facebook is now supported in tasks
    try:
        from apps.posts.tasks import publish_to_facebook_accounts
        print("✅ Facebook posting function exists")
    except ImportError:
        print("❌ Facebook posting function missing")
        return
    
    # Check for Facebook posts
    facebook_posts = Post.objects.filter(platform__icontains='facebook')
    print(f"📊 Found {facebook_posts.count()} Facebook posts in system")
    
    for post in facebook_posts:
        print(f"   Post: {post.content[:30]}... (Status: {post.status})")
    
    # Check Facebook integrator
    try:
        from apps.integrations.social_media_integrator import FacebookIntegrator
        fb_integrator = FacebookIntegrator()
        print("✅ FacebookIntegrator available")
        
        # Test with dummy credentials to check method signature
        try:
            result = fb_integrator.publish_post(
                content="Test", 
                credentials={"access_token": "dummy"}
            )
            if "access_token is required" in str(result):
                print("✅ FacebookIntegrator.publish_post() working (expected dummy token error)")
            else:
                print(f"⚠️  Unexpected result: {result}")
        except Exception as e:
            print(f"❌ FacebookIntegrator error: {e}")
            
    except ImportError as e:
        print(f"❌ FacebookIntegrator import error: {e}")
    
    print("\n=== Next Steps ===")
    print("1. User should disconnect and reconnect Facebook account")
    print("2. Ensure user has a Facebook Page (not just personal profile)")
    print("3. Re-authorization will include new permissions:")
    print("   - pages_manage_posts")
    print("   - pages_read_engagement") 
    print("4. Test posting to the Facebook Page")
    
if __name__ == '__main__':
    test_updated_facebook_system()
