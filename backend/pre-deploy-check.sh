#!/usr/bin/env bash
# Pre-deployment check script
# Run this before deploying to Render to catch issues early

echo "🔍 Running pre-deployment checks..."

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    echo "❌ Error: manage.py not found. Make sure you're in the Django project root."
    exit 1
fi

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: Virtual environment not detected. Consider activating your venv."
fi

echo "📦 Installing requirements..."
pip install -r requirements.txt

echo "🔧 Checking Django configuration..."
python manage.py check --deploy

echo "📊 Running database migrations (dry-run)..."
python manage.py migrate --dry-run

echo "🗄️  Collecting static files..."
python manage.py collectstatic --dry-run --verbosity=0

echo "🧪 Running tests..."
python manage.py test --verbosity=1

echo "✅ Pre-deployment checks complete!"
echo "🚀 Your app should be ready for deployment to Render."
echo ""
echo "Next steps:"
echo "1. Commit and push your changes to GitHub"
echo "2. Deploy using render.yaml or manual setup"
echo "3. Set environment variables in Render Dashboard"
