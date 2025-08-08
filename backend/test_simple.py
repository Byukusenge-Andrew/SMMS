#!/usr/bin/env python3
"""
Simple test script to check if the server is responding correctly
"""
import requests
import json

def test_health_endpoint():
    """Test the health check endpoint"""
    try:
        print("Testing health endpoint...")
        response = requests.get('http://127.0.0.1:8000/api/auth/health/')
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        print(f"Headers: {dict(response.headers)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error testing health endpoint: {e}")
        return False

def test_simple_endpoint():
    """Test the simple test endpoint"""
    try:
        print("\nTesting simple-test endpoint...")
        response = requests.get('http://127.0.0.1:8000/api/auth/simple-test/')
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        print(f"Headers: {dict(response.headers)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error testing simple endpoint: {e}")
        return False

def test_login_endpoint():
    """Test the login endpoint with proper data"""
    try:
        print("\nTesting login endpoint...")
        data = {
            'username': 'testuser',
            'password': 'testpass'
        }
        response = requests.post(
            'http://127.0.0.1:8000/api/auth/login/',
            json=data,
            headers={'Content-Type': 'application/json'}
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        print(f"Headers: {dict(response.headers)}")
        return True
    except Exception as e:
        print(f"Error testing login endpoint: {e}")
        return False

if __name__ == "__main__":
    print("=== Testing Backend Endpoints ===")
    test_health_endpoint()
    test_simple_endpoint()
    test_login_endpoint()
    print("\n=== Test Complete ===")
