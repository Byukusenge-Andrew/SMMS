#!/bin/bash
# Railway deployment script for Django backend

echo "🚂 Starting Railway Django deployment..."

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install --no-cache-dir -r requirements.txt

# Run database migrations
echo "🗃️ Running database migrations..."
python manage.py migrate

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

# Create subscription tiers if needed
echo "💳 Setting up subscription tiers..."
python create_subscription_tiers.py

echo "✅ Deployment setup complete!"

# Start the application
echo "🚀 Starting Django application..."
exec gunicorn social_media_manager.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120