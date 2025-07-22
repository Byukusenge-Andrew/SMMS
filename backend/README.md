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

Use [Postman](https://www.postman.com/) or similar tools to test the API endpoints.  
See the [Postman collection](../docs/postman_collection.json) for examples.

## Environment Variables

See `.env.example` for all required and optional environment variables.

## License

MIT License
