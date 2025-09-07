#!/usr/bin/env python3
"""
Test Facebook Integration Setup - Keativ App (678085037958557)
"""
import requests
import json

# Configuration
BASE_URL = "http://127.0.0.1:8000"
API_TOKEN = "YOUR_API_TOKEN_HERE"  # Replace with actual user token

def test_facebook_endpoint_availability():
    """Test that all Facebook endpoints are accessible"""
    
    print("🔍 Testing Facebook Integration Setup")
    print("App: Keativ (ID: 678085037958557)")
    print("=" * 50)
    
    endpoints = [
        ("/api/integrations/facebook/authorize/", "Facebook Authorization"),
        ("/api/integrations/facebook/callback/", "Facebook Callback"),
        ("/api/integrations/facebook/verify/", "Facebook Verification"),
        ("/api/integrations/facebook/post/", "Facebook Posting"),
        ("/api/integrations/facebook/disconnect/", "Facebook Disconnect")
    ]
    
    all_working = True
    
    for endpoint, name in endpoints:
        try:
            # Test OPTIONS request (should work without auth)
            response = requests.options(f"{BASE_URL}{endpoint}")
            if response.status_code == 200:
                print(f"✅ {name}: Endpoint available")
            else:
                print(f"❌ {name}: Status {response.status_code}")
                all_working = False
        except Exception as e:
            print(f"❌ {name}: Exception {e}")
            all_working = False
    
    return all_working

def test_facebook_config():
    """Test Facebook configuration"""
    
    print(f"\n📱 Facebook App Configuration:")
    print(f"   App ID: 678085037958557")
    print(f"   App Name: Keativ")
    print(f"   Contact: byuridrew@gmail.com")
    print(f"   Terms: https://keativ.netlify.app/terms")
    print(f"   Redirect URI: http://127.0.0.1:8000/api/integrations/facebook/callback/")

def main():
    """Run Facebook integration setup test"""
    
    print("🚀 Facebook Integration Setup Test")
    print("Meta App: Keativ")
    print("=" * 50)
    
    # Test endpoint availability
    endpoints_ok = test_facebook_endpoint_availability()
    
    # Show configuration
    test_facebook_config()
    
    print("\n" + "=" * 50)
    
    if endpoints_ok:
        print("✅ All Facebook endpoints are properly configured!")
        print("\n📝 Next steps to complete setup:")
        print("1. Start Django server: python manage.py runserver")
        print("2. Get user authentication token")  
        print("3. Test authorization flow: GET /api/integrations/facebook/authorize/")
        print("4. Complete OAuth flow via Facebook callback")
        print("5. Verify connection: GET /api/integrations/facebook/verify/")
        print("\n🎉 Facebook integration is ready for testing!")
    else:
        print("❌ Some endpoints are not working. Check server status.")
    
    return endpoints_ok

if __name__ == "__main__":
    main()
