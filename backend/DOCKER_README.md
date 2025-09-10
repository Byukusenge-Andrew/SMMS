# SMMS Backend Docker Setup

This document explains how to run the SMMS backend using Docker and Docker Compose.

## Prerequisites

- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- Docker Compose v2.0+
- Git

## Quick Start (Development)

1. **Clone and navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Copy environment file:**
   ```bash
   # Windows
   copy .env.docker .env
   
   # Linux/Mac
   cp .env.docker .env
   ```

3. **Start the development environment:**
   ```bash
   # Windows
   docker-manager.bat start
   
   # Linux/Mac
   ./docker-manager.sh start
   ```

4. **Run initial migrations:**
   ```bash
   # Windows
   docker-manager.bat migrate
   
   # Linux/Mac
   ./docker-manager.sh migrate
   ```

5. **Create a superuser (optional):**
   ```bash
   # Windows
   docker-manager.bat createsuperuser
   
   # Linux/Mac
   ./docker-manager.sh createsuperuser
   ```

6. **Access the application:**
   - Backend API: http://localhost:8000
   - Admin Panel: http://localhost:8000/admin
   - API Documentation: http://localhost:8000/api/docs/

## Services

The Docker setup includes the following services:

### Development Environment
- **backend**: Django application server
- **postgres**: PostgreSQL database
- **redis**: Redis cache and Celery broker
- **celery-worker**: Celery task worker
- **celery-beat**: Celery periodic task scheduler

### Production Environment
- **backend**: Django with Gunicorn
- **postgres**: PostgreSQL database
- **celery-worker**: Celery task worker
- **celery-beat**: Celery periodic task scheduler
- **nginx**: Reverse proxy (optional)

## Management Commands

### Windows (PowerShell/CMD)
```batch
# Development
docker-manager.bat build         # Build development images
docker-manager.bat start         # Start development environment
docker-manager.bat stop          # Stop development environment
docker-manager.bat logs          # View logs

# Production
docker-manager.bat build-prod    # Build production images
docker-manager.bat start-prod    # Start production environment
docker-manager.bat stop-prod     # Stop production environment

# Django Management
docker-manager.bat migrate       # Run migrations
docker-manager.bat makemigrations # Create migrations
docker-manager.bat shell         # Django shell
docker-manager.bat createsuperuser # Create superuser
docker-manager.bat test          # Run tests
docker-manager.bat collectstatic # Collect static files

# Maintenance
docker-manager.bat cleanup       # Clean up Docker resources
docker-manager.bat reset         # Reset entire environment (deletes data!)
```

### Linux/Mac (Bash)
```bash
# Development
./docker-manager.sh build         # Build development images
./docker-manager.sh start         # Start development environment
./docker-manager.sh stop          # Stop development environment
./docker-manager.sh logs          # View logs

# Production
./docker-manager.sh build-prod    # Build production images
./docker-manager.sh start-prod    # Start production environment
./docker-manager.sh stop-prod     # Stop production environment

# Django Management
./docker-manager.sh migrate       # Run migrations
./docker-manager.sh makemigrations # Create migrations
./docker-manager.sh shell         # Django shell
./docker-manager.sh createsuperuser # Create superuser
./docker-manager.sh test          # Run tests
./docker-manager.sh collectstatic # Collect static files

# Maintenance
./docker-manager.sh cleanup       # Clean up Docker resources
./docker-manager.sh reset         # Reset entire environment (deletes data!)
```

## Manual Docker Commands

If you prefer using Docker Compose directly:

### Development
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Run Django commands
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py createsuperuser
docker-compose exec backend python manage.py shell
```

### Production
```bash
# Start production environment
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Stop production environment
docker-compose -f docker-compose.prod.yml down
```

## Environment Configuration

### Development (.env.docker)
- Uses local PostgreSQL and Redis containers
- Debug mode enabled
- Development-friendly settings

### Production (.env)
- Use your actual production environment variables
- Set DEBUG=False
- Configure your cloud Redis/Valkey instance
- Set production database credentials

## Port Mappings

| Service | Container Port | Host Port |
|---------|----------------|-----------|
| Backend | 8000 | 8000 |
| PostgreSQL | 5432 | 5432 |
| Redis | 6379 | 6379 |
| Nginx (prod) | 80/443 | 80/443 |

## Volumes

- **postgres_data**: PostgreSQL database files
- **redis_data**: Redis persistence files
- **media_files**: User uploaded media
- **static_files**: Django static files

## Troubleshooting

### Common Issues

1. **Port already in use:**
   ```bash
   docker-compose down
   # Or change ports in docker-compose.yml
   ```

2. **Database connection issues:**
   ```bash
   docker-compose logs postgres
   # Check if PostgreSQL is healthy
   ```

3. **Celery worker not starting:**
   ```bash
   docker-compose logs celery-worker
   # Check Redis connection
   ```

4. **Permission issues (Linux/Mac):**
   ```bash
   sudo chown -R $USER:$USER .
   ```

### Logs

View logs for specific services:
```bash
# Backend logs
docker-compose logs backend

# Database logs
docker-compose logs postgres

# Celery logs
docker-compose logs celery-worker

# All logs
docker-compose logs
```

### Database Access

Connect to PostgreSQL:
```bash
# From host
psql -h localhost -U postgres -d social-media-db

# From container
docker-compose exec postgres psql -U postgres -d social-media-db
```

### Redis Access

Connect to Redis:
```bash
# From container
docker-compose exec redis redis-cli
```

## Development Workflow

1. **Make code changes** in your local files
2. **Restart services** if needed:
   ```bash
   docker-compose restart backend
   ```
3. **Run migrations** when models change:
   ```bash
   docker-manager.bat migrate
   ```
4. **View logs** to debug:
   ```bash
   docker-manager.bat logs
   ```

## Production Deployment

1. **Update environment variables** in `.env`
2. **Build production images:**
   ```bash
   docker-manager.bat build-prod
   ```
3. **Deploy:**
   ```bash
   docker-manager.bat start-prod
   ```
4. **Run migrations:**
   ```bash
   docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate
   ```

## Security Notes

- Change default passwords in production
- Use secrets management for sensitive data
- Enable SSL/TLS in production
- Regularly update Docker images
- Use non-root user in containers (already configured)

## Backup and Restore

### Database Backup
```bash
docker-compose exec postgres pg_dump -U postgres social-media-db > backup.sql
```

### Database Restore
```bash
docker-compose exec -T postgres psql -U postgres social-media-db < backup.sql
```

### Volume Backup
```bash
docker run --rm -v smms_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres-backup.tar.gz /data
```

## Support

For issues with Docker setup, check:
1. Docker Desktop is running
2. Required ports are available
3. Environment variables are correctly set
4. Log files for error messages
