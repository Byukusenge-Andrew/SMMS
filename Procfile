web: cd backend && python manage.py migrate && python manage.py collectstatic --noinput && gunicorn social_media_manager.wsgi:application --bind 0.0.0.0:$PORT
release: cd backend && python manage.py migrate
worker: cd backend && celery -A social_media_manager worker --loglevel=info
beat: cd backend && celery -A social_media_manager beat --loglevel=info