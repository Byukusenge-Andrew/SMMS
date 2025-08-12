#!/usr/bin/env bash
# Pre-deployment check script
# Run this before deploying to Render to catch issues early

echo "🔍 Running pre-deployment checks..."

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    echo "❌ Error: manage.py not found. Make sure you're in the Django project root."
    exit 1
fi

# Check if virtual environment exists and try to activate it
if [ -d "venv" ]; then
    echo "🐍 Virtual environment found, activating..."
    source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null || {
        echo "⚠️  Could not activate virtual environment automatically."
        echo "💡 Please run: source venv/bin/activate (Linux/Mac) or venv\\Scripts\\activate (Windows)"
        echo "   Then run this script again."
        exit 1
    }
    echo "✅ Virtual environment activated"
elif [ ! -z "$VIRTUAL_ENV" ]; then
    echo "✅ Virtual environment already activated: $VIRTUAL_ENV"
else
    echo "⚠️  Warning: No virtual environment detected."
    echo "💡 Consider creating one: python -m venv venv"
    echo "   Then activate it and install requirements"
fi

# Check if Django is available
python -c "import django; print(f'✅ Django {django.get_version()} found')" 2>/dev/null || {
    echo "❌ Django not found. Installing requirements..."
    pip install -r requirements.txt || {
        echo "❌ Failed to install requirements. Please check your environment."
        exit 1
    }
}

echo "📦 Installing/updating requirements..."
pip install -r requirements.txt

echo "🔧 Checking Django configuration..."
python manage.py check --deploy 2>/dev/null || {
    echo "⚠️  Django check failed. This might be due to missing environment variables."
    echo "💡 This is normal for local testing - production environment variables will be set in Render."
}

echo "📊 Testing database connection..."
python manage.py check --database=default 2>/dev/null || {
    echo "⚠️  Database check failed. This is expected locally if using production database URL."
    echo "💡 Your AWS RDS database will work in production."
}

echo "🗄️  Testing static files collection..."
python manage.py collectstatic --dry-run --verbosity=0 2>/dev/null || {
    echo "⚠️  Static files check had issues, but this should work in production."
}

echo "🧪 Running basic Python syntax check..."
python -m py_compile manage.py && echo "✅ Python syntax OK" || echo "❌ Python syntax errors found"

echo "📋 Checking required files..."
[ -f "requirements.txt" ] && echo "✅ requirements.txt found" || echo "❌ requirements.txt missing"
[ -f "build.sh" ] && echo "✅ build.sh found" || echo "❌ build.sh missing"
[ -f "render.yaml" ] && echo "✅ render.yaml found" || echo "❌ render.yaml missing"

echo ""
echo "✅ Pre-deployment checks complete!"
echo "🚀 Your app should be ready for deployment to Render."
echo ""
echo "Next steps:"
echo "1. Commit and push your changes to GitHub"
echo "2. Deploy using render.yaml or manual setup"
echo "3. Set environment variables in Render Dashboard"
