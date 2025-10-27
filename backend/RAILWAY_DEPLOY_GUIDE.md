# 🚂 Railway Backend Deployment Guide

## Quick Deploy Instructions

### Method 1: GitHub Integration (Recommended)

1. **Push to GitHub**:

   ```bash
   git add .
   git commit -m "Add Railway deployment config"
   git push origin main
   ```

2. **Deploy on Railway**:
   - Go to [railway.app](https://railway.app)
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your SMMS repository
   - Set **Root Directory**: `backend`
   - Railway will auto-detect Python and deploy

### Method 2: Railway CLI

1. **Install CLI**:

   ```bash
   npm install -g @railway/cli
   ```

2. **Login & Deploy**:

   ```bash
   cd backend
   railway login
   railway new
   railway up
   ```

## Required Environment Variables

Set these in Railway Dashboard → Project → Variables:

```env
# Core Django Settings
SECRET_KEY=your-super-secret-key-here
DEBUG=False
DJANGO_SETTINGS_MODULE=social_media_manager.settings

# Database (Railway PostgreSQL)
DATABASE_URL=postgresql://user:pass@host:port/db

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_BUCKET_NAME=keativpictures

# Redis (for Celery - Railway Redis)
REDIS_URL=redis://default:password@host:port

# Social Media API Keys
TWITTER_API_KEY=your-twitter-api-key
TWITTER_API_SECRET=your-twitter-api-secret
LINKEDIN_CLIENT_ID=your-linkedin-client-id
LINKEDIN_CLIENT_SECRET=your-linkedin-client-secret
TIKTOK_CLIENT_KEY=your-tiktok-client-key
TIKTOK_CLIENT_SECRET=your-tiktok-client-secret

# Email Configuration (Optional)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# CORS Settings
ALLOWED_HOSTS=your-railway-domain.railway.app,localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=https://your-frontend-domain.com
```

## Railway Services Needed

### 1. Main Backend Service

- **Type**: Web Service
- **Source**: GitHub Repository
- **Root Directory**: `backend`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python manage.py migrate && python manage.py collectstatic --noinput && gunicorn social_media_manager.wsgi:application --bind 0.0.0.0:$PORT`

### 2. PostgreSQL Database

- Add from Railway Templates
- Copy `DATABASE_URL` to backend environment variables

### 3. Redis Instance

- Add from Railway Templates  
- Copy `REDIS_URL` to backend environment variables

### 4. Celery Worker (Optional)

- **Type**: Worker Service
- **Source**: Same GitHub Repository
- **Root Directory**: `backend`
- **Start Command**: `celery -A social_media_manager worker --loglevel=info`

## Post-Deployment Steps

1. **Access Railway Console**:

   ```bash
   railway run python manage.py shell
   ```

2. **Create Superuser**:

   ```python
   from django.contrib.auth import get_user_model
   User = get_user_model()
   User.objects.create_superuser('admin', 'admin@example.com', 'your-password')
   ```

3. **Test API Endpoints**:
   - Health Check: `https://your-app.railway.app/health/`
   - Admin Panel: `https://your-app.railway.app/admin/`
   - API Docs: `https://your-app.railway.app/api/docs/`

## Troubleshooting

### Common Issues

1. **Static Files Not Loading**:
   - Check `STATIC_ROOT` and `STATIC_URL` in settings
   - Ensure `whitenoise` is in `MIDDLEWARE`

2. **Database Connection Error**:
   - Verify `DATABASE_URL` environment variable
   - Check PostgreSQL service is running

3. **Supabase Upload Failing**:
   - Verify `SUPABASE_URL` and `SUPABASE_KEY`
   - Check bucket name and RLS policies

4. **CORS Errors**:
   - Add frontend domain to `CORS_ALLOWED_ORIGINS`
   - Update `ALLOWED_HOSTS`

### View Logs

```bash
railway logs
```

### Connect to Database

```bash
railway connect postgres
```

## Production Checklist

- [ ] Set `DEBUG=False`
- [ ] Configure proper `SECRET_KEY`
- [ ] Set up SSL/HTTPS
- [ ] Configure proper CORS settings
- [ ] Set up monitoring and logging
- [ ] Configure backup strategy
- [ ] Set up domain name
- [ ] Test all API endpoints
- [ ] Test file uploads to Supabase
- [ ] Test social media integrations

## Performance Optimization

1. **Gunicorn Configuration**:
   - Workers: 2-4 (based on Railway plan)
   - Timeout: 120 seconds
   - Max requests: 1000

2. **Database Optimization**:
   - Connection pooling
   - Query optimization
   - Database indexing

3. **Caching**:
   - Redis for session storage
   - Cache API responses
   - Static file caching

Your Railway deployment URL will be: `https://your-project-name.railway.app`
