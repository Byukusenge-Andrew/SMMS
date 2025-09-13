# Railway Deployment Configuration

## Backend Service (Django API)
The backend is a Django REST API that handles:
- User authentication and profiles
- Social media integrations
- Post management and scheduling
- Analytics and reporting
- File uploads via Supabase

### Environment Variables Required:
- SECRET_KEY
- DATABASE_URL (PostgreSQL)
- SUPABASE_URL
- SUPABASE_KEY
- SUPABASE_BUCKET_NAME
- REDIS_URL
- ALLOWED_HOSTS
- DEBUG=False

### Build Command:
```bash
cd backend && pip install -r requirements.txt
```

### Start Command:
```bash
cd backend && python manage.py migrate && python manage.py collectstatic --noinput && gunicorn social_media_manager.wsgi:application --bind 0.0.0.0:$PORT
```

## Frontend Service (React/Vite)
The frontend is a React application built with Vite that provides:
- User dashboard
- Social media account management
- Post creation and scheduling
- Analytics visualization

### Environment Variables Required:
- VITE_API_URL (Backend API URL)

### Build Command:
```bash
cd SMMS_frontend/keativ && npm install && npm run build
```

### Start Command:
```bash
cd SMMS_frontend/keativ && npm run preview
```