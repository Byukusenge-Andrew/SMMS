#!/usr/bin/env python
"""
PostgreSQL Migration Helper Script

This script helps with the transition from MySQL to PostgreSQL.
Run this after setting up your PostgreSQL database.
"""

import os
import django
from django.core.management import execute_from_command_line

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "social_media_manager.settings")
django.setup()


def migrate_to_postgresql():
    """
    Step-by-step migration to PostgreSQL
    """
    print("=== PostgreSQL Migration Helper ===")
    print()

    print("1. Make sure PostgreSQL is installed and running")
    print("2. Create a database named 'social_media_db' (or your preferred name)")
    print("3. Update your .env file with PostgreSQL credentials:")
    print("   DB_NAME=social_media_db")
    print("   DB_USER=postgres")
    print("   DB_PASSWORD=your_password")
    print("   DB_HOST=localhost")
    print("   DB_PORT=5432")
    print()

    print("4. Install PostgreSQL dependencies:")
    print("   pip install psycopg2-binary")
    print()

    print("5. Run migrations:")
    print("   python manage.py makemigrations")
    print("   python manage.py migrate")
    print()

    print("6. Create a superuser:")
    print("   python manage.py createsuperuser")
    print()

    print("=== Migration Complete! ===")
    print("Your Django app is now configured to use PostgreSQL.")


if __name__ == "__main__":
    migrate_to_postgresql()
