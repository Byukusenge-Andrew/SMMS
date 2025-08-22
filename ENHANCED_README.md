# SMMS - Social Media Management System

## Enhanced with GoHighLevel CRM Integration & Stripe Payment Processing

### 🚀 New Features Added

#### Payment Integration (Stripe)

- **Subscription Tiers**: Free, Professional, Business, Enterprise
- **Billing Management**: Monthly/Yearly billing cycles, payment history
- **Secure Payments**: PCI-compliant Stripe integration
- **Subscription Management**: Upgrade/downgrade plans, cancel subscriptions

#### GoHighLevel CRM Integration

- **Contact Management**: Sync contacts between SMMS and GoHighLevel
- **Lead Tracking**: Track leads from social media campaigns
- **Pipeline Management**: Manage sales pipelines within SMMS
- **Automated Workflows**: Trigger CRM actions based on social media events

### 🛠️ Quick Setup

#### Prerequisites

- Python 3.9+
- Node.js 16+
- PostgreSQL (or SQLite for development)
- Redis (for Celery background tasks)

#### Windows Setup (PowerShell)

```powershell
# Run the automated setup script
.\test-setup.bat
```

#### Linux/Mac Setup

```bash
# Make setup script executable and run
chmod +x test-setup.sh
./test-setup.sh
```

### 📋 Manual Setup Instructions

#### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate

# Install dependencies  
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Start development server
python manage.py runserver
```

#### Frontend Setup

```bash
cd SMMS_frontend/keativ

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Start development server
npm run dev
```

### 🔧 Environment Configuration

#### Backend (.env in backend directory)

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/smms_db
# Or for SQLite: DATABASE_URL=sqlite:///db.sqlite3

# Redis (for Celery)
REDIS_URL=redis://localhost:6379/0

# Stripe Configuration
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# GoHighLevel Configuration
GOHIGHLEVEL_API_KEY=your-ghl-api-key
GOHIGHLEVEL_CLIENT_ID=your-ghl-client-id
GOHIGHLEVEL_CLIENT_SECRET=your-ghl-client-secret
GOHIGHLEVEL_BASE_URL=https://services.leadconnectorhq.com

# Email Settings
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

#### Frontend (.env in SMMS_frontend/keativ directory)

```env
# Backend API Configuration
VITE_API_URL=http://127.0.0.1:8000/api

# Stripe Configuration (replace with your actual keys)
VITE_STRIPE_PUBLIC_KEY=pk_test_51234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ

# Application Configuration
VITE_APP_NAME=SMMS - Social Media Management System
VITE_APP_VERSION=1.0.0

# Feature Flags
VITE_ENABLE_STRIPE_PAYMENTS=true
VITE_ENABLE_GOHIGHLEVEL_CRM=true
```

### 📊 New Pages & Features

#### Payment System

- **Billing Dashboard**: `/dashboard/billing`
  - View current subscription
  - Update payment methods
  - View payment history
  - Manage billing settings

- **Enhanced Pricing**: `/pricing-enhanced`
  - Interactive subscription tier comparison
  - Feature matrix
  - FAQ section
  - Direct subscription signup

#### CRM Integration

- **CRM Contacts**: `/dashboard/crm`
  - View and manage GoHighLevel contacts
  - Sync contact data
  - Track interaction history

- **CRM Integration Setup**: `/dashboard/crm/integration`
  - Configure GoHighLevel API credentials
  - Test connection
  - Manage sync settings

### 🗄️ Database Schema

#### New Models Added

- **SubscriptionTier**: Defines available subscription plans
- **UserSubscription**: Tracks user's active subscription
- **PaymentHistory**: Records all payment transactions
- **GoHighLevelIntegration**: Stores CRM integration settings
- **CRMContact**: Cached contact data from GoHighLevel

### 🔌 API Endpoints

#### Payment Endpoints

```bash
 POST /api/core/subscriptions/subscribe/
GET /api/core/subscriptions/tiers/
GET /api/core/subscriptions/current/
POST /api/core/subscriptions/cancel/
GET /api/core/payments/methods/
POST /api/core/payments/methods/add/
POST /api/core/payments/webhook/ (Stripe webhook)
```

#### CRM Endpoints  

```bash
GET /api/core/crm/contacts/
POST /api/core/crm/contacts/sync/
GET /api/core/crm/integration/status/
POST /api/core/crm/integration/configure/
POST /api/core/crm/integration/test/
```

### 🧪 Testing

#### Run Backend Tests

```bash
cd backend
python manage.py test
```

#### Run Frontend Tests

```bash
cd SMMS_frontend/keativ
npm test
```

### 🚀 Deployment Notes

1. **Environment Variables**: Ensure all production environment variables are set
2. **Database**: Run migrations on production database
3. **Static Files**: Collect static files for Django admin
4. **Stripe Webhooks**: Configure webhook endpoints in Stripe Dashboard
5. **GoHighLevel**: Set up OAuth application in GoHighLevel

### 🔐 Security Considerations

- All payment processing uses Stripe's secure infrastructure
- API keys and secrets are stored as environment variables
- CSRF protection enabled for all forms
- Rate limiting applied to API endpoints
- User authentication required for all dashboard features

### 📞 Support

For technical support or setup assistance:

- Check the logs: `backend/logs/` directory
- Review error messages in browser console
- Verify environment variables are correctly set
- Ensure all services (PostgreSQL, Redis) are running

---

**Latest Version**: Enhanced with Stripe Payments & GoHighLevel CRM Integration
**Last Updated**: January 2025
