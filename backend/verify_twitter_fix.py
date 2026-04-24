import os
import sys
import django
from unittest.mock import MagicMock
from urllib.parse import parse_qs, urlparse

# Set up Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from apps.integrations.views_twitter import twitter_authorize
from rest_framework.test import APIRequestFactory
from django.contrib.auth.models import User

def test_twitter_authorize_url():
    factory = APIRequestFactory()
    user = User.objects.first()
    if not user:
        user = User.objects.create_user(username='testuser', password='password')
    
    request = factory.get('/api/integrations/twitter/authorize/')
    request.user = user
    # Mock session
    request.session = MagicMock()
    request.session.session_key = 'test_session_key'
    request.session.get.return_value = None
    
    response = twitter_authorize(request)
    
    if response.status_code == 200:
        auth_url = response.data['authorize_url']
        print(f"Generated URL: {auth_url}")
        
        parsed_url = urlparse(auth_url)
        params = parse_qs(parsed_url.query)
        
        if 'prompt' in params and params['prompt'][0] == 'login':
            print("SUCCESS: 'prompt=login' found in authorization URL.")
            return True
        else:
            print("FAILURE: 'prompt=login' NOT found in authorization URL.")
            return False
    else:
        print(f"FAILURE: Request failed with status code {response.status_code}")
        print(f"Response data: {response.data}")
        return False

if __name__ == "__main__":
    test_twitter_authorize_url()
