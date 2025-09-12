#!/usr/bin/env python
"""
Simple test to check if Supabase authentication is working
"""
import os
from decouple import config

# Test the service role key directly
SUPABASE_URL = config("SUPABASE_URL", default="")
SUPABASE_SERVICE_ROLE_KEY = config("SUPABASE_SERVICE_ROLE_KEY", default="")

print("🔍 Testing Supabase Authentication")
print("=" * 50)
print(f"Supabase URL: {SUPABASE_URL}")
print(f"Service Role Key: {SUPABASE_SERVICE_ROLE_KEY[:20]}...")

try:
    from supabase import create_client
    
    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    
    # Test 1: Try to list bucket contents
    print("\n📦 Test 1: List bucket contents")
    response = client.storage.from_('keativpictures').list()
    
    if hasattr(response, 'error') and response.error:
        print(f"❌ Bucket list failed: {response.error}")
    else:
        print("✅ Bucket list successful!")
        print(f"Found {len(response) if response else 0} items in bucket")
    
    # Test 2: Try to get bucket info
    print("\n🪣 Test 2: Get bucket info")
    bucket_response = client.storage.get_bucket('keativpictures')
    
    if hasattr(bucket_response, 'error') and bucket_response.error:
        print(f"❌ Bucket info failed: {bucket_response.error}")
    else:
        print("✅ Bucket info retrieved successfully!")
        print(f"Bucket: {bucket_response}")
        
except Exception as e:
    print(f"❌ Authentication test failed: {e}")

print("\n" + "=" * 50)
print("🎯 Diagnosis:")
print("If tests pass: Profile pictures should upload to Supabase")
print("If tests fail: Files will fall back to local storage")