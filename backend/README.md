# SMMS Backend

This is the Django backend for the Social Media Manager platform.

## Features

- User authentication (registration, login, email verification)
- Social media account and team management
- Analytics and reporting
- Notifications and integrations
- RESTful API with token authentication

## Requirements

- Python 3.13
- PostgreSQL
- Redis

## Setup

### 1. Create and activate a virtual environment

```bash
python -m venv venv
venv\Scripts\activate  # On Windows
# or
source venv/bin/activate  # On macOS/Linux
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy `.env.example` to `.env` and fill in your settings.

### 4. Apply migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Create a superuser

```bash
python manage.py createsuperuser
```

### 6. Run the development server

```bash
python manage.py runserver
```

## API Endpoints

- **Register:** `POST /api/auth/register/`
- **Login:** `POST /api/auth/login/`
- **Verify Email:** `GET /api/auth/verify-email/<token>/`
- **Resend Verification:** `POST /api/auth/resend-verification/`

## Testing

Run the test suite:

```bash
python manage.py test
```

Run tests with coverage:

```bash
coverage run --source='.' manage.py test
coverage report
coverage html  # Generate HTML coverage report
```

Run tests with pytest:

```bash
pytest
```

Use [Postman](https://www.postman.com/) or similar tools to test the API endpoints.  
See the [Postman collection](../docs/postman_collection.json) for examples.

## Code Quality

### Formatting with Black

```bash
black .
black --check .  # Check without making changes
```

### Import sorting with isort

```bash
isort .
isort --check-only .  # Check without making changes
```

### Linting with flake8

```bash
flake8 .
```

## CI/CD Pipeline

This project uses GitHub Actions for continuous integration and deployment:

### Workflows

1. **CI Pipeline** (`.github/workflows/ci.yml`)
   - Runs on push to main/develop branches
   - Includes: testing, linting, security checks, build verification
   - Services: PostgreSQL, Redis
   - Generates coverage reports

2. **Development CI** (`.github/workflows/dev.yml`)
   - Runs on feature branches and PRs to develop
   - Quick feedback for development work
   - Focus on code quality and basic tests

3. **Deployment** (`.github/workflows/deploy.yml`)
   - Builds and pushes Docker images
   - Deploys to staging (main branch) and production (tags)

### Docker

Build the Docker image:

```bash
docker build -t smms-backend .
```

Run with Docker Compose:

```bash
docker-compose up -d
```

### Environment Setup for CI

The CI pipeline requires these secrets in your GitHub repository:

- `CODECOV_TOKEN` (optional, for coverage reporting)
- Database and Redis services are automatically configured

### Branch Strategy

- `main`: Production-ready code
- `develop`: Integration branch for features
- `feature/*`: Feature development branches

### Quality Gates

- All tests must pass
- Code coverage minimum: 80%
- No security vulnerabilities (checked with safety/bandit)
- Code formatting with Black
- Import sorting with isort
- Linting with flake8

## Environment Variables

See `.env.example` for all required and optional environment variables.

## License

MIT License
