#!/bin/bash

echo "🚀 SMMS Test Setup Script"
echo "========================"

# Test Backend
echo "📡 Testing Backend Connection..."
cd backend

# Check if virtual environment exists and create if not
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
if [ -d "venv/Scripts" ]; then
    source venv/Scripts/activate  # Windows Git Bash
elif [ -d "venv/bin" ]; then
    source venv/bin/activate      # Linux/Mac
fi

echo "Installing backend dependencies..."
pip install -r requirements.txt

echo "Running database migrations..."
python manage.py migrate

echo "Creating superuser (if needed)..."
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin')" | python manage.py shell

# Test Frontend
echo "🌐 Testing Frontend Setup..."
cd ../SMMS_frontend/keativ

echo "Installing frontend dependencies..."
npm install

echo "✅ Setup Complete!"
echo ""
echo "Next steps:"
echo "1. Backend: cd backend && python manage.py runserver"
echo "2. Frontend: cd SMMS_frontend/keativ && npm run dev"
echo "3. Visit: http://localhost:5173"
echo ""
echo "🔐 Admin Panel: http://127.0.0.1:8000/admin (admin/admin)"
echo "📊 Billing Dashboard: http://localhost:5173/dashboard/billing"
echo "🏢 CRM Dashboard: http://localhost:5173/dashboard/crm"
