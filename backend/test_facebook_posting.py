#!/usr/bin/env python
"""
Test Facebook posting functionality
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from apps.posts.models import Post
from apps.posts.tasks import publish_scheduled_post
from apps.integrations.models import SocialMediaAccount, SocialMediaPlatform
from django.contrib.auth.models import User

def test_facebook_posting():
    """Test Facebook posting functionality"""
    
    # Get user
    user = User.objects.get(id=3)
    print(f"Testing Facebook posting for user: {user.username}")
    
    # Check Facebook accounts
    facebook_accounts = SocialMediaAccount.objects.filter(
        user=user,
        platform=SocialMediaPlatform.FACEBOOK,
        is_active=True
    )
    print(f"Active Facebook accounts: {facebook_accounts.count()}")
    for account in facebook_accounts:
        print(f"  Account: {account.username} (ID: {account.id})")
        print(f"  Has access token: {'Yes' if account.access_token else 'No'}")
    
    # Check the existing Facebook post
    try:
        post = Post.objects.get(id='a3d986a4-e267-411c-a730-b8e0e94dbb19')
        print(f"\nExisting Facebook post:")
        print(f"  Status: {post.status}")
        print(f"  Content: {post.content[:50]}...")
        print(f"  Platform: {post.platform}")
        
        if hasattr(post, 'error_message') and post.error_message:
            print(f"  Error: {post.error_message}")
        if hasattr(post, 'published_at') and post.published_at:
            print(f"  Published at: {post.published_at}")
            
        # Try to publish if failed
        if post.status == 'failed':
            print("\n  Retrying failed post...")
            post.status = 'scheduled'
            post.save()
            
            # Trigger publish
            publish_scheduled_post(str(post.id))
            
            # Check result
            post.refresh_from_db()
            print(f"  New status: {post.status}")
            if hasattr(post, 'error_message') and post.error_message:
                print(f"  Error: {post.error_message}")
            if hasattr(post, 'published_at') and post.published_at:
                print(f"  Published at: {post.published_at}")
                
    except Post.DoesNotExist:
        print("No existing Facebook post found")

if __name__ == '__main__':
    test_facebook_posting()
