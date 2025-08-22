# SMMS Backend

This is the backend for the Social Media Management System (SMMS), built with Django. It powers a full-stack platform for managing social media accounts, analytics, influencer collaborations, notifications, and integrations.

## Features

- **User Authentication:** Registration, login, email verification, token-based authentication.
- **Social Media Management:** Account and team management, influencer collaborations.
- **Analytics & Reporting:** Collect and analyze social media data, generate reports.
- **Notifications & Integrations:** Email, social integrations (Twitter/X, Slack, etc.).
- **Posts Management:** Posting, scheduling, and managing social media content.
- **Rate Limiting:** Efficient Redis-backed throttling for API requests.
- **RESTful API:** Secure endpoints for all core features.

## Requirements

- Python 3.13
- PostgreSQL
- Redis

## Architecture Overview

```
Client (Web/Frontend)
      │
      ▼
REST API (Django)
      │
      ├── PostgreSQL (main DB)
      ├── Redis (cache, rate limits, Celery broker)
      ├── Supabase (file/media storage)
      └── Celery (background tasks)
```

- **Django:** Main web framework (apps for auth, posts, analytics, integrations, etc.)
- **Celery + Redis:** For background/async tasks (notifications, analytics, reporting)
- **Supabase:** For storing media/files (custom Django storage backend)
- **GitHub Actions:** CI/CD for automated testing, linting, deployment

## Setup

1. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On macOS/Linux
   venv\Scripts\activate     # On Windows
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   - Copy `.env.example` to `.env` and fill in required values.

4. **Apply migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create a superuser**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run the development server**
   ```bash
   python manage.py runserver
   ```

## Running Background Tasks

- Start Celery worker:
  ```bash
  celery -A social_media_manager worker --loglevel=info --pool=solo
  ```
- Start Celery beat:
  ```bash
  celery -A social_media_manager beat --loglevel=info
  ```

## API Endpoints

- **Register:** `POST /api/auth/register/`
- **Login:** `POST /api/auth/login/`
- **Verify Email:** `GET /api/auth/verify-email/<token>/`
- **Resend Verification:** `POST /api/auth/resend-verification/`
- **Social Media Integrations:**  
  - Twitter OAuth: `/api/integrations/twitter/authorize/`, `/api/integrations/twitter/callback/`
- **Rate Limiting:**  
  - Dashboard: `/api/core/rate-limit/dashboard/`
  - Logs: `/api/core/rate-limit/logs/`
  - Stats: `/api/core/rate-limit/stats/`
  - Test: `/api/core/rate-limit/test/`
- **IP Management:**  
  - Whitelist: `/api/core/ip/whitelist/`
  - Blacklist: `/api/core/ip/blacklist/`
- **Posts:**  
  - `/api/integrations/twitter/my-posts/`

See the [Postman collection](docs/postman_collection.json) for examples.

## Code Quality

- **Formatting:**  
  ```bash
  black .
  black --check .
  ```
- **Import sorting:**  
  ```bash
  isort .
  isort --check-only .
  ```
- **Linting:**  
  ```bash
  flake8 .
  ```

## Testing

- Django test suite:
  ```bash
  python manage.py test
  ```
- With coverage:
  ```bash
  coverage run --source='.' manage.py test
  coverage report
  coverage html
  ```
- With pytest:
  ```bash
  pytest
  ```

## CI/CD Pipeline

- **GitHub Actions** for automated CI/CD:
  - Runs tests, linting, security checks, and build verification on push.
  - Docker builds and deployment to staging/production.
- **Branch strategy:**
  - `main`: Production-ready
  - `develop`: Integration
  - `feature/*`: Feature branches
- **Quality gates:**
  - All tests must pass
  - Coverage minimum: 80%
  - No security vulnerabilities (checked with safety/bandit)
  - Code formatted and linted

## Deployment

- Deployable on [Render](https://render.com) or other cloud platforms
- Uses AWS RDS for production database
- Redis for cache/tasks (Render or external)
- See `DEPLOYMENT_GUIDE.md` for step-by-step instructions

## Production Checklist

- All environment variables set
- Database migrations applied
- Static files served
- Health check endpoint operational
- Admin panel accessible
- API endpoints working
- Social integrations configured
- Email sending operational
- Redis/Celery tasks working
- Error tracking (Sentry) enabled

## Monitoring

- Sentry for error tracking (optional)
- Render service metrics
- Health check alerts
- AWS RDS performance monitoring

## Environment Variables

See `.env.example` for required and optional variables.

## License

MIT License
