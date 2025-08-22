#!/usr/bin/env python
"""
API test script to verify payment and CRM endpoints are working
"""
import os
import sys
import django
import requests
import json
from urllib.parse import urljoin

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')

# Setup Django
django.setup()

# Base API URL
BASE_URL = "http://127.0.0.1:8000/api/"

def test_api_endpoints():
    """Test API endpoints without authentication"""
    print("🧪 Testing API Endpoints...")
    
    endpoints_to_test = [
        "core/subscriptions/tiers/",
        "health/",
    ]
    
    results = []
    
    for endpoint in endpoints_to_test:
        url = urljoin(BASE_URL, endpoint)
        try:
            response = requests.get(url, timeout=5)
            if response.status_code in [200, 401, 403]:  # 401/403 are expected for protected endpoints
                print(f"✅ {endpoint}: Status {response.status_code}")
                results.append(True)
            else:
                print(f"❌ {endpoint}: Status {response.status_code}")
                results.append(False)
        except requests.exceptions.RequestException as e:
            print(f"❌ {endpoint}: Connection error - {e}")
            results.append(False)
    
    return all(results)

def test_django_admin():
    """Test Django admin is accessible"""
    print("\n🧪 Testing Django Admin...")
    
    try:
        response = requests.get("http://127.0.0.1:8000/admin/", timeout=5)
        if response.status_code == 200:
            print("✅ Django Admin: Accessible")
            return True
        else:
            print(f"❌ Django Admin: Status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Django Admin: Connection error - {e}")
        return False

def test_static_files():
    """Test static files are served"""
    print("\n🧪 Testing Static Files...")
    
    try:
        response = requests.get("http://127.0.0.1:8000/static/admin/css/base.css", timeout=5)
        if response.status_code == 200:
            print("✅ Static Files: Served correctly")
            return True
        else:
            print(f"❌ Static Files: Status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Static Files: Connection error - {e}")
        return False

def main():
    """Main function to run all API tests"""
    print("🚀 Starting API Integration Tests")
    print("⚠️  Note: Make sure Django development server is running on port 8000\n")
    
    tests_passed = 0
    total_tests = 3
    
    if test_api_endpoints():
        tests_passed += 1
    
    if test_django_admin():
        tests_passed += 1
        
    if test_static_files():
        tests_passed += 1
    
    print(f"\n📊 API Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All API tests passed! Server is running correctly.")
        return True
    else:
        print("⚠️  Some API tests failed. Make sure the Django server is running:")
        print("   Run: python manage.py runserver")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
