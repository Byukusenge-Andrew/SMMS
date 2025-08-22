
# Script to set up and run the Django backend with Celery worker and beat

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    python -m venv venv
fi

# Activate venv
.\venv\Scripts\Activate.ps1

# Install requirements
pip install --upgrade pip
cd backend
pip install Pillow
pip install "click<8.1"
pip install -r requirements.txt

# Run migrations
python backend/manage.py migrate

# Start Redis (if using Docker and not already running)
if ! docker ps | grep -q redis; then
    docker run -d -p 6379:6379 --name redis redis
fi

# Start Celery worker (in background)
celery -A social_media_manager worker --pool=solo &

# Start Celery beat (in background)
celery -A social_media_manager beat &

# Start Django server
python backend/manage.py runserver
