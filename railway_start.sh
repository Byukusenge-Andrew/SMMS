#!/bin/bash

# Railway startup script for Django backend

echo "Starting Railway deployment..."

# Navigate to backend directory
cd backend

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --settings=social_media_manager.settings_railway

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --settings=social_media_manager.settings_railway

# Create superuser if needed (only in development)
if [ "$CREATE_SUPERUSER" = "true" ]; then
    echo "Creating superuser..."
    python manage.py shell --settings=social_media_manager.settings_railway -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created')
else:
    print('Superuser already exists')
"
fi

# Start the Django application
echo "Starting Django application..."
gunicorn social_media_manager.wsgi:application --bind 0.0.0.0:$PORT --settings=social_media_manager.settings_railway