#!/usr/bin/env bash
# Local production test script
# This simulates the production environment locally

echo "🚀 Testing production configuration locally..."

# Set production-like environment variables
export DEBUG=False
export SECRET_KEY="test-secret-key-for-local-production-test"
export DATABASE_URL="postgres://postgres:andre01ab.@social-media-db.chgyuqs4suf5.eu-north-1.rds.amazonaws.com:5432/postgres?sslmode=require"

echo "📦 Installing requirements..."
pip install -r requirements.txt

echo "🗄️  Collecting static files..."
python manage.py collectstatic --noinput

echo "🔧 Running system checks..."
python manage.py check --deploy

echo "📊 Testing database connection..."
python manage.py migrate --dry-run

echo "🌐 Starting server in production mode..."
echo "Visit http://localhost:8000 to test your app"
echo "Press Ctrl+C to stop the server"

python -m gunicorn social_media_manager.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
