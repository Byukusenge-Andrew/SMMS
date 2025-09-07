#!/usr/bin/env python3
"""
Quick script to generate a test authentication token for Facebook integration testing
"""
import os
import sys
import django

# Add the backend directory to the Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(backend_dir)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

User = get_user_model()

def get_or_create_test_token():
    """Get or create a test token for the first available user"""
    try:
        # Try to get the first user
        user = User.objects.first()
        
        if not user:
            print("❌ No users found in the database.")
            print("Please create a user first:")
            print("   python manage.py createsuperuser")
            return None
        
        # Get or create token for this user
        token, created = Token.objects.get_or_create(user=user)
        
        if created:
            print(f"✅ Created new authentication token for user: {user.username}")
        else:
            print(f"✅ Retrieved existing authentication token for user: {user.username}")
        
        print(f"\n🔑 Authentication Token: {token.key}")
        print(f"\n📝 Copy this token and use it in the Facebook test page:")
        print(f"   1. Open facebook_test.html in your browser")
        print(f"   2. Paste this token in the 'Authentication Setup' section")
        print(f"   3. Click 'Set Token'")
        print(f"   4. Start testing Facebook integration!")
        
        return token.key
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    print("🚀 Facebook Integration Test Token Generator")
    print("=" * 50)
    token = get_or_create_test_token()
    
    if token:
        print("\n" + "=" * 50)
        print("✅ Token generated successfully!")
        print("🌐 Now you can test the Facebook integration in your browser.")
    else:
        print("\n" + "=" * 50)
        print("❌ Failed to generate token.")
