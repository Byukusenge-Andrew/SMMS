# Docker Deployment Guide for Railway

## Overview

This guide covers deploying the SMMS backend to Railway using Docker containers for production deployment.

## Prerequisites

1. Railway account with PostgreSQL and Redis services
2. Supabase account with storage bucket configured
3. Environment variables configured in Railway dashboard

## Files Structure

```bash
backend/
├── Dockerfile.railway          # Multi-stage production Dockerfile
├── docker-compose.railway.yml  # Local development with Railway services
├── railway.json                # Railway deployment configuration
├── requirements.txt             # Python dependencies
└── manage.py                   # Django management commands
```

## Deployment Steps

### 1. Railway Service Setup

Create the following services in Railway:

- **PostgreSQL**: Database service
- **Redis**: Cache and message broker
- **Web Service**: Django application (Docker-based)

### 2. Environment Variables

Configure these in Railway dashboard:

**Required:**

```env
DEBUG=False
SECRET_KEY=your-production-secret-key
DATABASE_URL=postgresql://... (auto-provided by Railway)
REDIS_URL=redis://... (auto-provided by Railway)
SUPABASE_URL=your-supabase-project-url
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_BUCKET_NAME=your-bucket-name
ALLOWED_HOSTS=your-domain.railway.app,localhost
PORT=8000
```

**Optional:**

```bash
CELERY_BROKER_URL=${REDIS_URL}
CELERY_RESULT_BACKEND=${REDIS_URL}
CORS_ALLOWED_ORIGINS=https://your-frontend-domain.com
```

### 3. Deploy to Railway

#### Option A: GitHub Integration

1. Push code to GitHub repository
2. Connect repository to Railway
3. Railway will automatically build using `Dockerfile.railway`
4. Set build command: `docker build -f Dockerfile.railway -t backend .`

#### Option B: Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Initialize project
railway init

# Deploy
railway up
```

### 4. Database Migration

After first deployment, run migrations:

```bash
railway run python manage.py migrate
railway run python manage.py collectstatic --noinput
railway run python manage.py createsuperuser
```

## Docker Configuration Details

### Multi-Stage Build Benefits
- **Builder Stage**: Installs dependencies and compiles packages
- **Production Stage**: Lean runtime with only necessary files
- **Security**: Non-root user, minimal attack surface
- **Performance**: Optimized for production workloads

### Health Checks
The Dockerfile includes health checks to ensure service reliability:
- Endpoint: `/health/`
- Interval: 30 seconds
- Timeout: 10 seconds
- Retries: 3

### Resource Optimization
- Python virtual environment for isolation
- Static file serving via WhiteNoise
- Gunicorn WSGI server for production
- Process management for concurrent requests

## Local Development

### Using Docker Compose
```bash
# Create .env file with Supabase credentials
cp .env.example .env

# Build and start services
docker-compose -f docker-compose.railway.yml up --build

# Run migrations
docker-compose exec backend python manage.py migrate

# Create superuser
docker-compose exec backend python manage.py createsuperuser
```

### Services Available
- **Backend API**: http://localhost:8000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **Celery Worker**: Background task processing
- **Celery Beat**: Scheduled task execution

## Production Considerations

### 1. Security
- Use strong SECRET_KEY in production
- Configure ALLOWED_HOSTS appropriately
- Enable HTTPS in production
- Use environment variables for sensitive data

### 2. Performance
- Configure Gunicorn workers based on CPU cores
- Use connection pooling for database
- Enable Redis persistence if needed
- Monitor memory usage and optimize

### 3. Monitoring
- Check Railway dashboard for service health
- Monitor application logs via Railway CLI
- Set up error tracking (Sentry recommended)
- Configure alerts for critical issues

### 4. Scaling
- Horizontal scaling: Add more web service instances
- Vertical scaling: Increase RAM/CPU allocation
- Database: Consider read replicas for high traffic
- Cache: Use Redis for session storage and caching

## Troubleshooting

### Common Issues

**Build Failures:**
```bash
# Check build logs
railway logs --service=your-service-name

# Local build test
docker build -f Dockerfile.railway -t smms-backend .
```

**Database Connection:**
```bash
# Test database connectivity
railway run python manage.py dbshell

# Check migrations
railway run python manage.py showmigrations
```

**Static Files:**
```bash
# Collect static files
railway run python manage.py collectstatic --noinput

# Check static file serving
curl https://your-app.railway.app/static/admin/css/base.css
```

**Environment Variables:**
```bash
# List all environment variables
railway variables

# Check specific variable
railway run echo $DATABASE_URL
```

### Logs and Debugging
```bash
# View application logs
railway logs

# Follow logs in real-time
railway logs --follow

# View specific service logs
railway logs --service=backend
```

### Performance Optimization
```bash
# Check resource usage
railway status

# Scale service
railway scale --replicas=2

# Update service configuration
railway service update
```

## Maintenance

### Updates and Rollbacks
```bash
# Deploy new version
git push origin main

# Rollback to previous version
railway rollback

# Check deployment history
railway deployments
```

### Database Maintenance
```bash
# Backup database
railway run pg_dump $DATABASE_URL > backup.sql

# Run custom management commands
railway run python manage.py your_custom_command
```

### Monitoring Health
```bash
# Check service health
curl https://your-app.railway.app/health/

# Monitor response times
railway metrics
```

## Best Practices

1. **Environment Management**: Use Railway's environment variables
2. **Secrets**: Never commit secrets to version control
3. **Logging**: Use structured logging for better debugging
4. **Testing**: Test Docker builds locally before deployment
5. **Monitoring**: Set up comprehensive monitoring and alerts
6. **Backup**: Regular database backups and disaster recovery plan
7. **Security**: Regular security updates and vulnerability scanning

## Support Resources

- **Railway Documentation**: https://docs.railway.app/
- **Django Deployment**: https://docs.djangoproject.com/en/4.2/howto/deployment/
- **Docker Best Practices**: https://docs.docker.com/develop/best-practices/
- **Gunicorn Configuration**: https://docs.gunicorn.org/en/stable/configure.html