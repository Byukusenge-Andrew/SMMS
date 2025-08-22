import os
import sys
import django
from django.core.wsgi import get_wsgi_application

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings_vercel')

# Initialize Django
django.setup()

# Get WSGI application
application = get_wsgi_application()

def handler(request):
    return application(request)
