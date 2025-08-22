#!/usr/bin/env bash
# Setup script for local development
# Run this first to set up your environment

echo "🚀 Setting up SMMS Backend Development Environment..."

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    echo "❌ Error: manage.py not found. Make sure you're in the Django project root."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🐍 Creating virtual environment..."
    python -m venv venv || {
        echo "❌ Failed to create virtual environment. Make sure Python is installed."
        exit 1
    }
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows (Git Bash/MSYS2)
    source venv/Scripts/activate || {
        echo "❌ Failed to activate virtual environment on Windows"
        echo "💡 Try running: venv\\Scripts\\activate.bat"
        exit 1
    }
else
    # Linux/Mac
    source venv/bin/activate || {
        echo "❌ Failed to activate virtual environment on Unix"
        echo "💡 Try running: source venv/bin/activate"
        exit 1
    }
fi

echo "✅ Virtual environment activated"

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📋 Installing requirements..."
pip install -r requirements.txt || {
    echo "❌ Failed to install requirements"
    exit 1
}

echo "✅ Requirements installed"

# Check Django installation
python -c "import django; print(f'✅ Django {django.get_version()} installed successfully')" || {
    echo "❌ Django installation verification failed"
    exit 1
}

echo ""
echo "🎉 Setup complete! Your development environment is ready."
echo ""
echo "💡 To activate the virtual environment in future sessions:"
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    echo "   Windows: venv\\Scripts\\activate"
else
    echo "   Linux/Mac: source venv/bin/activate"
fi
echo ""
echo "🔄 Next steps:"
echo "1. Run: ./pre-deploy-check.sh (to test everything works)"
echo "2. Run: python manage.py runserver (to start development server)"
echo "3. Visit: http://127.0.0.1:8000/api/health/ (to test API)"
