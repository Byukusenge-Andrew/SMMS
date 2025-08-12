"""
Django settings for social_media_manager project.
"""

from pathlib import Path

import dj_database_url
from decouple import config
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("SECRET_KEY", default=os.environ.get('SECRET_KEY', 'django-insecure-change-in-production'))

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = 'RENDER' not in os.environ

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=lambda v: [s.strip() for s in v.split(",")])

# Add Render.com hostname
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Application definition
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "django_celery_beat",
    "django_filters",
    "drf_spectacular",
]

LOCAL_APPS = [
    "apps.authentication",
    "apps.posts",
    "apps.analytics",
    "apps.integrations",
    "apps.influencers",
    "apps.notifications",
    "apps.collaborators",
    "apps.health",
    "apps.messaging",
    "apps.media",  # Media management app
    "apps.core",  # Rate limiting and core utilities
]

INSTALLED_APPS = (
    DJANGO_APPS
    + THIRD_PARTY_APPS
    + LOCAL_APPS
    + [
        "social_django",
    ]
)

MIDDLEWARE = [
    "social_django.middleware.SocialAuthExceptionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",  
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # "apps.core.middleware.BurstProtectionMiddleware",  # TEMPORARILY DISABLED FOR DEBUGGING
    # "apps.core.middleware.RateLimitMiddleware",  # TEMPORARILY DISABLED FOR DEBUGGING
]

ROOT_URLCONF = "social_media_manager.urls"


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "social_media_manager.wsgi.application"

# Database
DATABASES = {"default": dj_database_url.config(default=config("DATABASE_URL"))}

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

# AUTHENTICATION_BACKENDS = [
#     'apps.authentication.backends.EmailOrUsernameModelBackend',
#     'django.contrib.auth.backends.ModelBackend',
# ]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": ("django.contrib.auth.password_validation." "UserAttributeSimilarityValidator"),
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Natural Language Processing settings
NLP_SETTINGS = {
    "TEXTBLOB_ENABLED": True,
    "SENTIMENT_ANALYSIS_ENABLED": True,
    "LANGUAGE_DETECTION_ENABLED": True,
}

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# This production code might break development mode, so we check whether we're in DEBUG mode
if not DEBUG:
    # Enable the WhiteNoise storage backend, which compresses static files to reduce disk use
    # and renames the files with unique names for each version to support long-term caching
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files - Supabase Storage
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"  # Fallback for local development

# Supabase Storage Configuration
SUPABASE_URL = config("SUPABASE_URL", default="")
SUPABASE_KEY = config("SUPABASE_KEY", default="")
SUPABASE_SERVICE_ROLE_KEY = config("SUPABASE_SERVICE_ROLE_KEY", default="")
SUPABASE_BUCKET = config("SUPABASE_BUCKET", default="keativpictures")

# Use Supabase Storage as default file storage
DEFAULT_FILE_STORAGE = "apps.core.storage.SupabaseStorage"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# REST Framework configuration
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        # "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Note: Rate limiting is handled by middleware, not DRF throttling
    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/hour",
        "user": "1000/hour",
        "premium": "10000/hour",
        "admin": "50000/hour",
    },
}

# CORS settings - Updated for production
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React dev server
    "http://127.0.0.1:3000",
    "http://localhost:8081",  # React Native
    "http://localhost:5173",  # Vite default port
    "http://127.0.0.1:5173",
]

# Add production frontend URL if available
FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:3000")
if FRONTEND_URL and FRONTEND_URL not in CORS_ALLOWED_ORIGINS:
    CORS_ALLOWED_ORIGINS.append(FRONTEND_URL)

# Allow additional origins from environment
CORS_ADDITIONAL_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="", cast=lambda v: [s.strip() for s in v.split(",") if s.strip()])
CORS_ALLOWED_ORIGINS.extend(CORS_ADDITIONAL_ORIGINS)

CORS_ALLOW_CREDENTIALS = True

# CSRF settings for production
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS.copy()
# Add Render domain
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")
# CORS_ALLOW_ALL_ORIGINS = True  # Set to True for development debugging

# Allow common headers
# CORS_ALLOW_HEADERS = [
#     'accept',
#     'accept-encoding',
#     'authorization',
#     'content-type',
#     'dnt',
#     'origin',
#     'user-agent',
#     'x-csrftoken',
#     'x-requested-with',
# ]

# CSRF settings for API
# CSRF_TRUSTED_ORIGINS = [
#     "http://localhost:3000",
#     "http://127.0.0.1:3000", 
#     "http://localhost:5173",
#     "http://127.0.0.1:5173",
# ]

# Celery Configuration
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/0")

# Social Auth settings
AUTHENTICATION_BACKENDS = (
    'apps.authentication.backends.EmailOrUsernameModelBackend',
    "social_core.backends.google.GoogleOAuth2",
    "social_core.backends.github.GithubOAuth2",
    "social_core.backends.twitter.TwitterOAuth",
    "django.contrib.auth.backends.ModelBackend",
)

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = config("SOCIAL_AUTH_GOOGLE_OAUTH2_KEY", default="")
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = config("SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET", default="")
SOCIAL_AUTH_GITHUB_KEY = config("SOCIAL_AUTH_GITHUB_KEY", default="")
SOCIAL_AUTH_GITHUB_SECRET = config("SOCIAL_AUTH_GITHUB_SECRET", default="")
SOCIAL_AUTH_TWITTER_KEY = config("SOCIAL_AUTH_TWITTER_KEY", default="")
SOCIAL_AUTH_TWITTER_SECRET = config("SOCIAL_AUTH_TWITTER_SECRET", default="")

LOGIN_URL = "login"
LOGOUT_URL = "logout"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

from celery.schedules import crontab

CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# Celery Beat Schedule
CELERY_BEAT_SCHEDULE = {
    "check-scheduled-posts": {
        "task": "apps.posts.tasks.check_scheduled_posts",
        "schedule": crontab(minute="*"),  # Every minute
    },
    "weekly-analytics-report": {
        "task": "apps.analytics.tasks.send_weekly_report",
        "schedule": crontab(hour=9, minute=0, day_of_week=1),  # Monday 9 AM
    },
    "monthly-analytics-report": {
        "task": "apps.analytics.tasks.send_monthly_report",
        "schedule": crontab(hour=9, minute=0, day_of_month=1),  # 1st day 9 AM
    },
    "yearly-analytics-report": {
        "task": "apps.analytics.tasks.send_yearly_report",
        "schedule": crontab(hour=9, minute=0, day_of_month=1, month_of_year=1),  # Jan 1st 9 AM
    },
    "cleanup-rate-limit-logs": {
        "task": "apps.core.tasks.cleanup_rate_limit_logs",
        "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    "generate-rate-limit-stats": {
        "task": "apps.core.tasks.generate_hourly_stats",
        "schedule": crontab(minute=5),  # Every hour at 5 minutes past
    },
}

# Cache configuration
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}

# Social Media API Keys
SOCIAL_MEDIA_CONFIGS = {
    "INSTAGRAM": {
        "CLIENT_ID": config("INSTAGRAM_CLIENT_ID", default=""),
        "CLIENT_SECRET": config("INSTAGRAM_CLIENT_SECRET", default=""),
        "REDIRECT_URI": config("INSTAGRAM_REDIRECT_URI", default=""),
    },
    "FACEBOOK": {
        "APP_ID": config("FACEBOOK_APP_ID", default=""),
        "APP_SECRET": config("FACEBOOK_APP_SECRET", default=""),
        "REDIRECT_URI": config("FACEBOOK_REDIRECT_URI", default=""),
    },
    "TWITTER": {
        "API_KEY": config("TWITTER_API_KEY", default=""),
        "API_SECRET": config("TWITTER_API_SECRET", default=""),
        "BEARER_TOKEN": config("TWITTER_BEARER_TOKEN", default=""),
    },
    "LINKEDIN": {
        "CLIENT_ID": config("LINKEDIN_CLIENT_ID", default=""),
        "CLIENT_SECRET": config("LINKEDIN_CLIENT_SECRET", default=""),
    },
    "TIKTOK": {
        "CLIENT_KEY": config("TIKTOK_CLIENT_KEY", default=""),
        "CLIENT_SECRET": config("TIKTOK_CLIENT_SECRET", default=""),
    },
    "YOUTUBE": {
        "API_KEY": config("YOUTUBE_API_KEY", default=""),
        "CLIENT_ID": config("YOUTUBE_CLIENT_ID", default=""),
        "CLIENT_SECRET": config("YOUTUBE_CLIENT_SECRET", default=""),
    },
    "PINTEREST": {
        "APP_ID": config("PINTEREST_APP_ID", default=""),
        "APP_SECRET": config("PINTEREST_APP_SECRET", default=""),
    },
    "SNAPCHAT": {
        "CLIENT_ID": config("SNAPCHAT_CLIENT_ID", default=""),
        "CLIENT_SECRET": config("SNAPCHAT_CLIENT_SECRET", default=""),
    },
    "REDDIT": {
        "CLIENT_ID": config("REDDIT_CLIENT_ID", default=""),
        "CLIENT_SECRET": config("REDDIT_CLIENT_SECRET", default=""),
    },
}

# Integration API Keys
SLACK_BOT_TOKEN = config("SLACK_BOT_TOKEN", default="")
SLACK_WEBHOOK_URL = config("SLACK_WEBHOOK_URL", default="")

CANVA_API_KEY = config("CANVA_API_KEY", default="")
ZAPIER_API_KEY = config("ZAPIER_API_KEY", default="")

GOOGLE_DRIVE_CREDENTIALS = config("GOOGLE_DRIVE_CREDENTIALS", default="")
DROPBOX_ACCESS_TOKEN = config("DROPBOX_ACCESS_TOKEN", default="")

# Email configuration
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="")

# Logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": "logs/django.log",
        },
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": True,
        },
        "apps": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": True,
        },
    },
}

# DRF Spectacular settings
SPECTACULAR_SETTINGS = {
    "TITLE": "Social Media Manager API",
    "DESCRIPTION": "Comprehensive social media management platform API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

# Sentry for error tracking
if not DEBUG:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=config("SENTRY_DSN", default=""),
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
        ],
        traces_sample_rate=0.1,
        send_default_pii=True,
    )

# Frontend URL for email verification links
FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:3000")

# Twitter OAuth 2.0 configuration (use python-decouple to read from .env)
TWITTER_CLIENT_ID = config('TWITTER_CLIENT_ID', default='')
TWITTER_CLIENT_SECRET = config('TWITTER_CLIENT_SECRET', default='')
# For dev, default to backend callback path
TWITTER_REDIRECT_URI = config('TWITTER_REDIRECT_URI', default='http://127.0.0.1:8000/api/integrations/twitter/callback/')
TWITTER_SCOPES = config('TWITTER_SCOPES', default='tweet.read tweet.write users.read offline.access')

# Twitter App-level API keys (OAuth 1.0a / v2 app context) used by twitter_service
TWITTER_API_KEY = config('TWITTER_API_KEY', default='')
TWITTER_API_KEY_SECRET = config('TWITTER_API_KEY_SECRET', default='')
TWITTER_BEARER_TOKEN = config('TWITTER_BEARER_TOKEN', default='')
TWITTER_ACCESS_TOKEN = config('TWITTER_ACCESS_TOKEN', default='')
TWITTER_ACCESS_TOKEN_SECRET = config('TWITTER_ACCESS_TOKEN_SECRET', default='')
