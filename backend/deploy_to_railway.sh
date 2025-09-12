#!/bin/bash

# 🚂 One-Click Railway Deployment for SMMS Backend

echo "🚀 Starting Railway deployment for SMMS Backend..."

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "📦 Installing Railway CLI..."
    npm install -g @railway/cli
fi

# Login to Railway (if not already logged in)
echo "🔐 Logging into Railway..."
railway login

# Create new Railway project
echo "🏗️ Creating new Railway project..."
railway new

# Add PostgreSQL database
echo "🗃️ Adding PostgreSQL database..."
railway add --database postgresql

# Add Redis for Celery
echo "🔴 Adding Redis for Celery..."
railway add --database redis

# Set environment variables
echo "⚙️ Setting environment variables..."
railway variables set SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(50))')
railway variables set DEBUG=False
railway variables set DJANGO_SETTINGS_MODULE=social_media_manager.settings

# Deploy the application
echo "🚀 Deploying application..."
railway up

echo "✅ Deployment complete!"
echo "📋 Next steps:"
echo "1. Go to Railway dashboard and set your environment variables"
echo "2. Add your Supabase credentials"
echo "3. Add your social media API keys"
echo "4. Test your deployment"
echo ""
echo "🌐 Your app will be available at: https://your-project.railway.app"