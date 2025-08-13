"""
Simple connectivity test for LinkedIn API
"""
import requests
import sys

def test_linkedin_connectivity():
    """Test basic connectivity to LinkedIn"""
    print("Testing connectivity to LinkedIn servers...")
    
    # Test basic connectivity
    try:
        response = requests.get("https://www.linkedin.com", timeout=10)
        print(f"✓ Basic LinkedIn connectivity: {response.status_code}")
    except Exception as e:
        print(f"✗ Basic LinkedIn connectivity failed: {e}")
        return False
    
    # Test API endpoint connectivity  
    try:
        # This should return 401 since we're not authenticated, but that means it's reachable
        response = requests.get("https://api.linkedin.com/v2/userinfo", timeout=10)
        print(f"✓ LinkedIn API endpoint reachable: {response.status_code}")
    except Exception as e:
        print(f"✗ LinkedIn API endpoint failed: {e}")
        return False
    
    # Test OAuth endpoint
    try:
        # This should return an error about missing parameters, but that means it's reachable
        response = requests.post("https://www.linkedin.com/oauth/v2/accessToken", 
                                timeout=10, 
                                data={"test": "test"})
        print(f"✓ LinkedIn OAuth endpoint reachable: {response.status_code}")
    except Exception as e:
        print(f"✗ LinkedIn OAuth endpoint failed: {e}")
        return False
    
    print("✓ All LinkedIn endpoints are reachable")
    return True

if __name__ == "__main__":
    test_linkedin_connectivity()
