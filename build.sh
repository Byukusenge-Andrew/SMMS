#!/bin/bash
# Vercel build script

echo "🚀 Starting Vercel build process..."

# Set Python path
export PYTHONPATH="${PYTHONPATH}:/vercel/path0/backend"

# Change to backend directory
cd backend

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput --settings=social_media_manager.settings_vercel

# Run Django checks
echo "✅ Running Django deployment checks..."
python manage.py check --deploy --settings=social_media_manager.settings_vercel

echo "✨ Build completed successfully!"
