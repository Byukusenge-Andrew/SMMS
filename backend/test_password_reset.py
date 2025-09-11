#!/usr/bin/env python3
"""
Test script for password reset functionality
"""

import os
import sys
import django
import requests
import json
from datetime import datetime

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from django.contrib.auth.models import User
from apps.authentication.models import PasswordResetToken

BASE_URL = "http://127.0.0.1:8000"

def test_forgot_password():
    """Test the forgot password functionality"""
    print("🔍 TESTING FORGOT PASSWORD FUNCTIONALITY")
    print("=" * 60)
    
    # Test with a valid email
    test_email = "complete.user@example.com"
    
    # Check if user exists
    try:
        user = User.objects.get(email=test_email)
        print(f"✅ Test user found: {user.username} ({user.email})")
    except User.DoesNotExist:
        print(f"❌ Test user with email {test_email} not found!")
        print("Please create a test user first or use an existing email.")
        return False
    
    # Test 1: Valid email
    print(f"\n📧 Testing forgot password with email: {test_email}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/forgot-password/",
            json={"email": test_email},
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Forgot password request successful!")
            print(f"Response: {data['message']}")
            
            # Check if token was created in database
            tokens = PasswordResetToken.objects.filter(user=user, is_used=False)
            if tokens.exists():
                token = tokens.first()
                print(f"✅ Password reset token created: {token.token}")
                print(f"   Expires at: {token.expires_at}")
                return str(token.token)
            else:
                print("❌ No password reset token found in database")
                return False
        else:
            print(f"❌ Request failed: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error! Is the Django server running?")
        print("Start it with: python manage.py runserver")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_validate_reset_token(token):
    """Test token validation"""
    print(f"\n🔍 TESTING TOKEN VALIDATION")
    print("=" * 40)
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/auth/validate-reset-token/{token}/",
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Token validation successful!")
            print(f"Message: {data['message']}")
            print(f"Email: {data['email']}")
            print(f"Username: {data['username']}")
            return True
        else:
            print(f"❌ Token validation failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error validating token: {e}")
        return False

def test_reset_password(token):
    """Test password reset with token"""
    print(f"\n🔒 TESTING PASSWORD RESET")
    print("=" * 40)
    
    new_password = "NewTestPassword123!"
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/reset-password/",
            json={
                "token": token,
                "password": new_password,
                "password_confirm": new_password
            },
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Password reset successful!")
            print(f"Message: {data['message']}")
            
            # Verify token is marked as used
            try:
                reset_token = PasswordResetToken.objects.get(token=token)
                if reset_token.is_used:
                    print("✅ Token marked as used in database")
                else:
                    print("❌ Token not marked as used")
            except PasswordResetToken.DoesNotExist:
                print("❌ Token not found in database")
            
            return True
        else:
            print(f"❌ Password reset failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error resetting password: {e}")
        return False

def test_login_with_new_password():
    """Test login with new password"""
    print(f"\n🔐 TESTING LOGIN WITH NEW PASSWORD")
    print("=" * 40)
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login/",
            json={
                "username": "complete.user@example.com",
                "password": "NewTestPassword123!"
            },
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Login with new password successful!")
            print(f"Token received: {data.get('token', 'N/A')[:20]}...")
            return True
        else:
            print(f"❌ Login failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error logging in: {e}")
        return False

def test_invalid_scenarios():
    """Test invalid scenarios"""
    print(f"\n🚫 TESTING INVALID SCENARIOS")
    print("=" * 40)
    
    # Test 1: Invalid email format
    print("Testing invalid email format...")
    response = requests.post(
        f"{BASE_URL}/api/auth/forgot-password/",
        json={"email": "invalid-email"},
        headers={'Content-Type': 'application/json'},
        timeout=10
    )
    print(f"Invalid email status: {response.status_code} ({'✅' if response.status_code == 400 else '❌'})")
    
    # Test 2: Non-existent email (should still return 200 for security)
    print("Testing non-existent email...")
    response = requests.post(
        f"{BASE_URL}/api/auth/forgot-password/",
        json={"email": "nonexistent@example.com"},
        headers={'Content-Type': 'application/json'},
        timeout=10
    )
    print(f"Non-existent email status: {response.status_code} ({'✅' if response.status_code == 200 else '❌'})")
    
    # Test 3: Invalid token
    print("Testing invalid reset token...")
    response = requests.get(
        f"{BASE_URL}/api/auth/validate-reset-token/invalid-token-12345/",
        timeout=10
    )
    print(f"Invalid token status: {response.status_code} ({'✅' if response.status_code == 400 else '❌'})")

def main():
    """Main test function"""
    print("🔑 PASSWORD RESET FUNCTIONALITY TEST")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test forgot password
    token = test_forgot_password()
    if not token:
        print("\n❌ Forgot password test failed. Stopping tests.")
        return
    
    # Test token validation
    if not test_validate_reset_token(token):
        print("\n❌ Token validation test failed. Stopping tests.")
        return
    
    # Test password reset
    if not test_reset_password(token):
        print("\n❌ Password reset test failed. Stopping tests.")
        return
    
    # Test login with new password
    if not test_login_with_new_password():
        print("\n❌ Login test failed.")
        return
    
    # Test invalid scenarios
    test_invalid_scenarios()
    
    print("\n" + "=" * 60)
    print("🎉 ALL PASSWORD RESET TESTS COMPLETED!")
    print("✅ The forgot password functionality is working correctly.")
    print("=" * 60)

if __name__ == "__main__":
    main()
