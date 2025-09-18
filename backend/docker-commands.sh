# Railway Docker Deployment Commands

# Build Docker image locally for testing
docker build -f Dockerfile.railway -t smms-backend:latest .

# Test Docker container locally
docker run -p 8000:8000 --env-file .env smms-backend:latest

# Test with Railway environment variables
docker run -p 8000:8000 \
  -e DEBUG=False \
  -e SECRET_KEY=your-secret-key \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  -e REDIS_URL=redis://host:6379/0 \
  -e SUPABASE_URL=your-supabase-url \
  -e SUPABASE_KEY=your-supabase-key \
  -e SUPABASE_BUCKET_NAME=your-bucket \
  -e ALLOWED_HOSTS=localhost,127.0.0.1 \
  -e PORT=8000 \
  smms-backend:latest

# Check container health
docker run --rm smms-backend:latest python manage.py check

# Run migrations in container
docker run --rm --env-file .env smms-backend:latest python manage.py migrate

# Collect static files
docker run --rm --env-file .env smms-backend:latest python manage.py collectstatic --noinput

# Create superuser interactively
docker run -it --env-file .env smms-backend:latest python manage.py createsuperuser

# Shell access to container
docker run -it --env-file .env smms-backend:latest /bin/bash

# View container logs
docker logs container-id

# Clean up images
docker image prune -f

# Remove all containers and images
docker system prune -af