"""
Vercel-specific Django settings
"""

import os
import sys
from .settings import *

# Override for Vercel serverless environment
DEBUG = False

# Vercel provides VERCEL_URL automatically
ALLOWED_HOSTS = [
    '.vercel.app',
    'localhost',
    '127.0.0.1',
    os.environ.get('VERCEL_URL', '').replace('https://', '').replace('http://', ''),
]

# Remove localhost/127.0.0.1 from CORS_ALLOWED_ORIGINS for production
CORS_ALLOWED_ORIGINS = [
    origin for origin in CORS_ALLOWED_ORIGINS 
    if not any(host in origin for host in ['localhost', '127.0.0.1'])
]

# Add Vercel URL to CORS if available
if os.environ.get('VERCEL_URL'):
    CORS_ALLOWED_ORIGINS.append(f"https://{os.environ.get('VERCEL_URL')}")

# Disable Celery for serverless (use background tasks alternatives)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Use console logging for Vercel
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Static files for Vercel
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Disable migrations check for serverless
if 'runserver' not in sys.argv:
    DATABASES['default']['OPTIONS'] = {'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"}
