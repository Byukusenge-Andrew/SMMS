#!/usr/bin/env python
"""
Test Facebook posting functionality
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
import requests
import json

def test_facebook_post():
    """Test Facebook posting"""
    print("🚀 Testing Facebook Post Functionality")
    print("=" * 50)
    
    # Get user and token
    user = User.objects.get(id=3)
    token = Token.objects.get(user=user)
    headers = {
        'Authorization': f'Token {token.key}',
        'Content-Type': 'application/json'
    }
    
    # Test post data
    post_data = {
        'content': 'Hello Facebook! 👋 This is a test post from Keativ Social Media Manager. Testing Facebook integration! 🚀'
    }
    
    print(f"📝 Posting content: {post_data['content']}")
    
    # Make the request
    response = requests.post(
        'http://127.0.0.1:8000/api/integrations/facebook/post/',
        headers=headers,
        data=json.dumps(post_data)
    )
    
    print(f"📊 Response Status: {response.status_code}")
    
    try:
        data = response.json()
        print(f"✅ Success: {data.get('success')}")
        print(f"📄 Message: {data.get('message')}")
        
        if data.get('success'):
            print("🎉 SUCCESS! Post published to Facebook!")
            if data.get('post_id'):
                print(f"📌 Post ID: {data.get('post_id')}")
        else:
            print("❌ Failed to post to Facebook")
            if data.get('error'):
                print(f"🚨 Error: {data.get('error')}")
    except Exception as e:
        print(f"❌ Error parsing response: {e}")
        print(f"Raw response: {response.text}")

if __name__ == '__main__':
    test_facebook_post()
