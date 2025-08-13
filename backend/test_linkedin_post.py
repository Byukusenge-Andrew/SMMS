#!/usr/bin/env python
import os
import django
from datetime import datetime, timedelta

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from django.utils import timezone
from apps.posts.models import Post
from apps.posts.tasks import publish_scheduled_post
from django.contrib.auth.models import User

# Get the user who has LinkedIn accounts
try:
    user = User.objects.get(username='byuridrew@gmail.com')
    
    # Create a test post scheduled for immediate publication
    test_post = Post.objects.create(
        user=user,
        content="Test post from corrected SMMS system! 🎉",
        platform="linkedin",  # Specify LinkedIn platform
        status="scheduled",
        scheduled_time=timezone.now() - timedelta(minutes=1),  # Past time so it gets published immediately
    )
    
    print(f"Created test post: {test_post.id}")
    print(f"Platform: {test_post.platform}")
    print(f"Content: {test_post.content}")
    print(f"User: {test_post.user}")
    print(f"Status: {test_post.status}")
    
    # Test the publication task directly
    print(f"\nTesting publication task...")
    publish_scheduled_post(str(test_post.id))
    
    # Check the result
    test_post.refresh_from_db()
    print(f"Final status: {test_post.status}")
    if test_post.error_message:
        print(f"Error message: {test_post.error_message}")
    if test_post.published_at:
        print(f"Published at: {test_post.published_at}")
        
except User.DoesNotExist:
    print("User 'byuridrew@gmail.com' not found")
except Exception as e:
    print(f"Error: {e}")
