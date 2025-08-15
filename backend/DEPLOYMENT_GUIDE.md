# SMMS Backend Deployment Guide for Render

This guide will help you deploy your Django backend to Render while keeping your existing AWS RDS database.

## Prerequisites

- [ ] GitHub account with your code pushed
- [ ] Render account (render.com)
- [ ] Your AWS RDS database is running and accessible
- [ ] Frontend domain/URL (if you have one)

## Step 1: Prepare Your Repository

1. Ensure all files are committed and pushed to GitHub:
   - `render.yaml`
   - `build.sh`
   - Updated `requirements.txt`
   - Updated `settings.py`

2. Make sure your `build.sh` is executable (already done)

## Step 2: Deploy to Render

### Option 1: Using render.yaml (Recommended)

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New" → "Blueprint"
3. Connect your GitHub repository
4. Select your repository and branch (`main`)
5. Give your project a name (e.g., "SMMS")
6. Click "Apply"

### Option 2: Manual Deployment

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Name**: `smms-backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `./build.sh`
   - **Start Command**: `python -m gunicorn social_media_manager.asgi:application -k uvicorn.workers.UvicornWorker`
   - **Plan**: `Starter` (or `Free` for testing)

## Step 3: Environment Variables

Add these environment variables in Render Dashboard:

### Required Variables (Add these manually)

```bash
SECRET_KEY=generate-in-render-dashboard
DEBUG=False
DATABASE_URL=postgres://postgres:andre01ab.@social-media-db.chgyuqs4suf5.eu-north-1.rds.amazonaws.com:5432/postgres?sslmode=require
FRONTEND_URL=https://your-frontend-domain.com
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=andrebyukusenge9@gmail.com
DJANGO_SUPERUSER_PASSWORD=create-secure-password
```

### Copy from your .env file

- All your API keys (Twitter, TikTok, etc.)
- Supabase configuration
- Slack integration keys
- Social auth keys
- Email configuration

## Step 4: Set Up Redis (Choose One)

### Option A: Use Render Redis (Recommended)

1. In Render Dashboard, create a new Redis service
2. Copy the Redis URL
3. Update these environment variables:

```bash
   REDIS_URL=redis://red-xxxxx:6379
   CELERY_BROKER_URL=redis://red-xxxxx:6379/0
   CELERY_RESULT_BACKEND=redis://red-xxxxx:6379/0
   ```

### Option B: Use External Redis

- Use AWS ElastiCache or another Redis service
- Update the Redis URLs accordingly

## Step 5: Update Redirect URIs

Update your social media app settings with new URLs:

1. **Twitter Developer Portal**:
   - Update redirect URI to: `https://your-app.onrender.com/api/integrations/twitter/callback/`

2. **Google OAuth**:
   - Update redirect URI to: `https://your-app.onrender.com/api/auth/google/callback/`

3. **GitHub OAuth**:
   - Update redirect URI to: `https://your-app.onrender.com/api/auth/github/callback/`

4. **Slack App**:
   - Update redirect URI to: `https://your-app.onrender.com/api/integrations/slack/callback/`

## Step 6: Database Migration

Your AWS RDS database should work without changes, but ensure:

1. Your RDS security group allows connections from Render IPs
2. SSL is properly configured (your connection string already has `sslmode=require`)

## Step 7: Test Deployment

1. Wait for deployment to complete
2. Check deployment logs for any errors
3. Visit your app URL: `https://your-app.onrender.com`
4. Test the health endpoint: `https://your-app.onrender.com/api/health/`
5. Test admin access: `https://your-app.onrender.com/admin/`

## Step 8: Set Up Custom Domain (Optional)

1. In Render Dashboard, go to your service settings
2. Add your custom domain
3. Update DNS records as instructed
4. Update `ALLOWED_HOSTS` and redirect URIs accordingly

## Troubleshooting

### Common Issues

1. **Database Connection Failed**:
   - Check AWS RDS security group
   - Verify DATABASE_URL format
   - Ensure SSL settings are correct

2. **Static Files Not Loading**:
   - Check WhiteNoise configuration
   - Verify `STATIC_ROOT` setting
   - Ensure `collectstatic` runs in build script

3. **Environment Variables**:
   - Double-check all environment variables are set
   - Ensure no trailing spaces or quotes

4. **Celery Tasks Not Working**:
   - Verify Redis connection
   - Check Celery configuration
   - Consider deploying Celery as a separate background worker

### Logs

- Check deployment logs in Render Dashboard
- Use `python manage.py check --deploy` for production readiness

## Production Checklist

- [ ] All environment variables are set correctly
- [ ] Database migrations ran successfully
- [ ] Static files are served correctly
- [ ] Health check endpoint works
- [ ] Admin panel is accessible
- [ ] API endpoints work correctly
- [ ] Social media integrations work
- [ ] Email sending works
- [ ] Redis/Celery tasks work
- [ ] Error tracking is set up (Sentry)

## Monitoring

1. Set up Sentry for error tracking (optional but recommended)
2. Monitor Render service metrics
3. Set up health check alerts
4. Monitor AWS RDS performance

Your Django backend should now be successfully deployed on Render while using your existing AWS infrastructure!
