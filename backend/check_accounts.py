#!/usr/bin/env python
import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from apps.integrations.models import SocialMediaAccount

# Check LinkedIn accounts
linkedin_accounts = SocialMediaAccount.objects.filter(platform='linkedin')
print(f"LinkedIn accounts found: {linkedin_accounts.count()}")

for acc in linkedin_accounts:
    print(f"- User: {acc.user}")
    print(f"  Username: {acc.username}")
    print(f"  Active: {acc.is_active}")
    print(f"  Has access token: {bool(acc.access_token)}")
    print(f"  Access token length: {len(acc.access_token) if acc.access_token else 0}")
    print("---")
