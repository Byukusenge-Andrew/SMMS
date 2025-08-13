#!/usr/bin/env python
"""
Test script for X/Twitter OAuth integration
Run this with: python test_twitter_oauth.py
"""
import requests
import sys

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api"

def test_endpoint(url, method="GET", data=None, headers=None):
    """Test an API endpoint"""
    print(f"\n{'='*50}")
    print(f"Testing: {method} {url}")
    print(f"{'='*50}")
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        # Try to parse JSON response
        try:
            json_data = response.json()
            print(f"JSON Response: {json_data}")
        except:
            print(f"Text Response: {response.text[:200]}...")
            
        return response.status_code == 200
        
    except requests.exceptions.RequestException as e:
        print(f"ERROR: {e}")
        return False

def main():
    print("🧪 Testing X/Twitter OAuth Integration")
    print("Make sure your Django server is running on localhost:8000")
    
    # Test OAuth endpoints
    endpoints = [
        # Basic server health
        (f"{BASE_URL}/health/", "GET"),
        
        # OAuth endpoints
        (f"{API_BASE}/integrations/twitter/authorize/", "GET"),
        (f"{API_BASE}/integrations/twitter/rate-limit/", "GET"),
        
        # Social auth endpoints (social-django)
        (f"{BASE_URL}/oauth/login/twitter/", "GET"),
        
        # Our custom OAuth callback endpoint
        (f"{API_BASE}/auth/x/login/callback/", "GET"),
    ]
    
    results = []
    for url, method in endpoints:
        success = test_endpoint(url, method)
        results.append((url, success))
    
    # Summary
    print(f"\n{'='*50}")
    print("TEST SUMMARY")
    print(f"{'='*50}")
    for url, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {url}")
    
    # Check if Twitter credentials are configured
    print(f"\n{'='*50}")
    print("ENVIRONMENT CHECK")
    print(f"{'='*50}")
    
    import os
    twitter_vars = [
        'TWITTER_API_KEY',
        'TWITTER_API_KEY_SECRET', 
        'TWITTER_BEARER_TOKEN',
        'TWITTER_ACCESS_TOKEN',
        'TWITTER_ACCESS_TOKEN_SECRET',
        'SOCIAL_AUTH_TWITTER_KEY',
        'SOCIAL_AUTH_TWITTER_SECRET'
    ]
    
    for var in twitter_vars:
        value = os.getenv(var)
        status = "✅ SET" if value else "❌ MISSING"
        print(f"{status}: {var}")

if __name__ == "__main__":
    main()
