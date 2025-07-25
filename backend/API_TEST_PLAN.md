# Social Media Management System (SMMS) API Test Plan

## Overview
This test plan covers all API endpoints in the SMMS Django backend, including authentication, posts, analytics, integrations, messaging, notifications, and collaborations.

## Test Environment Setup

### Prerequisites
- Django 5.0 backend running on `http://localhost:8000`
- PostgreSQL database configured
- Redis server running (for Celery tasks)
- Virtual environment activated with all dependencies installed

### Test Data Setup
```bash
# Create superuser
python manage.py createsuperuser

# Run migrations
python manage.py migrate

# Load test fixtures (if available)
python manage.py loaddata test_data.json
```

## 1. Authentication API Tests (`/api/auth/`)

### 1.1 User Registration
**Endpoint:** `POST /api/auth/register/`
```json
{
    "username": "testuser",
    "email": "test@example.com",
    "password": "TestPassword123!",
    "password2": "TestPassword123!",
    "first_name": "Test",
    "last_name": "User"
}
```
**Expected:** `201 Created` with user data and tokens

### 1.2 User Login
**Endpoint:** `POST /api/auth/login/`
```json
{
    "username": "testuser",
    "password": "TestPassword123!"
}
```
**Expected:** `200 OK` with access/refresh tokens

### 1.3 Token Refresh
**Endpoint:** `POST /api/auth/token/refresh/`
```json
{
    "refresh": "<refresh_token>"
}
```
**Expected:** `200 OK` with new access token

### 1.4 User Profile
**Endpoint:** `GET /api/auth/profile/`
**Headers:** `Authorization: Bearer <access_token>`
**Expected:** `200 OK` with user profile data

### 1.5 Team Management
**Endpoint:** `POST /api/auth/team/create/`
```json
{
    "name": "Test Team",
    "description": "A test team for API testing"
}
```
**Expected:** `201 Created` with team data

**Endpoint:** `POST /api/auth/team/invite/`
```json
{
    "email": "member@example.com",
    "role": "member"
}
```
**Expected:** `200 OK` with invitation sent confirmation

### 1.6 Social Media Account Connection
**Endpoint:** `POST /api/auth/social-accounts/`
```json
{
    "platform": "twitter",
    "account_name": "testaccount",
    "account_id": "123456789",
    "access_token": "mock_token",
    "is_active": true
}
```
**Expected:** `201 Created` with account data

## 2. Posts API Tests (`/api/posts/`)

### 2.1 Create Post
**Endpoint:** `POST /api/posts/`
```json
{
    "title": "Test Post",
    "content": "This is a test post for API testing",
    "platforms": ["twitter", "instagram"],
    "status": "draft",
    "scheduled_time": "2025-07-26T10:00:00Z"
}
```
**Expected:** `201 Created` with post data

### 2.2 List Posts
**Endpoint:** `GET /api/posts/`
**Query Parameters:** `?status=draft&platform=twitter&limit=10`
**Expected:** `200 OK` with paginated post list

### 2.3 Get Post Details
**Endpoint:** `GET /api/posts/{post_id}/`
**Expected:** `200 OK` with detailed post data

### 2.4 Update Post
**Endpoint:** `PUT /api/posts/{post_id}/`
```json
{
    "title": "Updated Test Post",
    "content": "Updated content",
    "status": "scheduled"
}
```
**Expected:** `200 OK` with updated post data

### 2.5 Delete Post
**Endpoint:** `DELETE /api/posts/{post_id}/`
**Expected:** `204 No Content`

### 2.6 Bulk Actions
**Endpoint:** `POST /api/posts/bulk-actions/`
```json
{
    "action": "publish",
    "post_ids": ["uuid1", "uuid2", "uuid3"]
}
```
**Expected:** `200 OK` with bulk action results

### 2.7 Calendar View
**Endpoint:** `GET /api/posts/calendar/`
**Query Parameters:** `?start_date=2025-07-01&end_date=2025-07-31`
**Expected:** `200 OK` with calendar data

### 2.8 Dashboard Stats
**Endpoint:** `GET /api/posts/dashboard/`
**Expected:** `200 OK` with dashboard statistics

## 3. AI-Powered Features Tests (`/api/posts/ai/`)

### 3.1 Content Suggestions
**Endpoint:** `POST /api/posts/ai/content-suggestions/`
```json
{
    "platform": "twitter",
    "topic": "technology",
    "count": 5
}
```
**Expected:** `200 OK` with AI-generated content suggestions

### 3.2 Content Analysis
**Endpoint:** `POST /api/posts/ai/analyze-content/`
```json
{
    "content": "This is amazing content for social media!",
    "platform": "instagram"
}
```
**Expected:** `200 OK` with content analysis and optimization suggestions

### 3.3 Optimal Posting Times
**Endpoint:** `GET /api/posts/ai/optimal-times/`
**Query Parameters:** `?platform=twitter&days=30`
**Expected:** `200 OK` with optimal posting time recommendations

### 3.4 Single Comment Sentiment Analysis
**Endpoint:** `POST /api/posts/ai/sentiment/comment/`
```json
{
    "comment": "This is absolutely amazing! I love it so much! 😍"
}
```
**Expected:** `200 OK` with sentiment analysis results

### 3.5 Post Comments Sentiment Analysis
**Endpoint:** `POST /api/posts/ai/sentiment/post/{post_id}/`
```json
{
    "comments": [
        "Great post!",
        "Love this content!",
        "Not bad, could be better",
        "This is terrible"
    ]
}
```
**Expected:** `200 OK` with aggregate sentiment analysis and insights

### 3.6 Batch Sentiment Analysis
**Endpoint:** `POST /api/posts/ai/sentiment/batch/`
```json
{
    "posts": [
        {
            "post_id": "uuid1",
            "comments": ["Great!", "Love it!"]
        },
        {
            "post_id": "uuid2",
            "comments": ["Nice work", "Could be better"]
        }
    ]
}
```
**Expected:** `200 OK` with batch sentiment analysis results

## 4. Analytics API Tests (`/api/analytics/`)

### 4.1 Analytics Data
**Endpoint:** `GET /api/analytics/data/`
**Query Parameters:** `?start_date=2025-07-01&end_date=2025-07-31&platform=twitter`
**Expected:** `200 OK` with analytics data

### 4.2 Performance Report
**Endpoint:** `GET /api/analytics/performance/`
**Query Parameters:** `?period=monthly&metric=engagement`
**Expected:** `200 OK` with performance metrics

### 4.3 AI Insights
**Endpoint:** `POST /api/analytics/ai-insights/`
```json
{
    "period": "last_30_days",
    "platforms": ["twitter", "instagram"]
}
```
**Expected:** `200 OK` with AI-generated insights

### 4.4 AI Recommendations
**Endpoint:** `POST /api/analytics/ai-recommendations/`
```json
{
    "user_context": {
        "industry": "technology",
        "target_audience": "developers"
    }
}
```
**Expected:** `200 OK` with AI recommendations

### 4.5 Competitor Analysis
**Endpoint:** `POST /api/analytics/competitor-analysis/`
```json
{
    "competitors": ["@competitor1", "@competitor2"],
    "platform": "twitter"
}
```
**Expected:** `200 OK` with competitor analysis

### 4.6 Performance Prediction
**Endpoint:** `POST /api/analytics/predict-performance/`
```json
{
    "content": "Exciting new product launch coming soon!",
    "platform": "instagram",
    "posting_time": "2025-07-26T15:00:00Z"
}
```
**Expected:** `200 OK` with performance predictions

## 5. Templates and Social Sets (`/api/posts/templates/`, `/api/posts/social-sets/`)

### 5.1 Create Template
**Endpoint:** `POST /api/posts/templates/`
```json
{
    "name": "Product Launch Template",
    "content": "🚀 Exciting news! {product_name} is now available!",
    "platforms": ["twitter", "linkedin"],
    "variables": ["product_name"]
}
```
**Expected:** `201 Created` with template data

### 5.2 List Templates
**Endpoint:** `GET /api/posts/templates/`
**Expected:** `200 OK` with template list

### 5.3 Create Social Set
**Endpoint:** `POST /api/posts/social-sets/`
```json
{
    "name": "Weekly Update Set",
    "description": "Templates for weekly updates",
    "posts": [
        {
            "platform": "twitter",
            "content": "Weekly update thread 1/3"
        },
        {
            "platform": "twitter",
            "content": "Key highlights this week 2/3"
        }
    ]
}
```
**Expected:** `201 Created` with social set data

## 6. Messaging API Tests (`/api/messaging/`)

### 6.1 Create Message
**Endpoint:** `POST /api/messaging/messages/`
```json
{
    "recipient": "user2@example.com",
    "subject": "Test Message",
    "content": "This is a test message",
    "priority": "normal"
}
```
**Expected:** `201 Created` with message data

### 6.2 List Messages
**Endpoint:** `GET /api/messaging/messages/`
**Query Parameters:** `?type=inbox&status=unread`
**Expected:** `200 OK` with message list

### 6.3 Automated Messaging
**Endpoint:** `POST /api/messaging/automated/`
```json
{
    "trigger": "new_follower",
    "platform": "twitter",
    "message_template": "Thank you for following! Welcome to our community!",
    "delay_minutes": 5
}
```
**Expected:** `201 Created` with automated message setup

## 7. Collaboration API Tests (`/api/collaborators/`)

### 7.1 Invite Collaborator
**Endpoint:** `POST /api/collaborators/invite/`
```json
{
    "email": "collaborator@example.com",
    "role": "editor",
    "permissions": ["create_posts", "edit_posts"]
}
```
**Expected:** `201 Created` with invitation data

### 7.2 List Collaborators
**Endpoint:** `GET /api/collaborators/`
**Expected:** `200 OK` with collaborator list

### 7.3 Update Collaborator Role
**Endpoint:** `PUT /api/collaborators/{collaborator_id}/`
```json
{
    "role": "admin",
    "permissions": ["create_posts", "edit_posts", "delete_posts", "manage_team"]
}
```
**Expected:** `200 OK` with updated collaborator data

## 8. Notifications API Tests (`/api/notifications/`)

### 8.1 List Notifications
**Endpoint:** `GET /api/notifications/`
**Query Parameters:** `?read=false&type=mention`
**Expected:** `200 OK` with notification list

### 8.2 Mark as Read
**Endpoint:** `POST /api/notifications/{notification_id}/mark-read/`
**Expected:** `200 OK` with confirmation

### 8.3 Notification Preferences
**Endpoint:** `GET /api/notifications/preferences/`
**Expected:** `200 OK` with user preferences

**Endpoint:** `PUT /api/notifications/preferences/`
```json
{
    "email_notifications": true,
    "push_notifications": false,
    "mention_notifications": true,
    "comment_notifications": true
}
```
**Expected:** `200 OK` with updated preferences

## 9. Integration Tests (`/api/integrations/`)

### 9.1 Social Media Account Verification
**Endpoint:** `POST /api/integrations/verify-account/`
```json
{
    "platform": "twitter",
    "username": "testaccount"
}
```
**Expected:** `200 OK` with verification result

### 9.2 OAuth Flow Initiation
**Endpoint:** `POST /api/integrations/oauth/start/`
```json
{
    "platform": "twitter",
    "callback_url": "http://localhost:3000/auth/callback"
}
```
**Expected:** `200 OK` with OAuth URL

## 10. Error Handling Tests

### 10.1 Authentication Errors
- **401 Unauthorized:** Invalid or missing token
- **403 Forbidden:** Insufficient permissions

### 10.2 Validation Errors
- **400 Bad Request:** Invalid request data
- **422 Unprocessable Entity:** Validation failures

### 10.3 Resource Errors
- **404 Not Found:** Resource doesn't exist
- **409 Conflict:** Resource conflict (e.g., duplicate)

### 10.4 Server Errors
- **500 Internal Server Error:** Server issues
- **503 Service Unavailable:** Service temporarily unavailable

## 11. Performance Tests

### 11.1 Load Testing
- Test concurrent user requests
- Measure response times under load
- Test database performance with large datasets

### 11.2 API Rate Limiting
- Test rate limiting functionality
- Verify proper rate limit headers
- Test rate limit exceeded responses

## 12. Security Tests

### 12.1 Authentication Security
- Test JWT token validation
- Test token expiration handling
- Test refresh token security

### 12.2 Authorization Testing
- Test role-based access control
- Test resource ownership validation
- Test cross-user data access prevention

### 12.3 Input Validation
- Test SQL injection prevention
- Test XSS prevention
- Test input sanitization

## 13. Background Task Tests

### 13.1 Celery Task Testing
- Test scheduled post publishing
- Test email notification sending
- Test AI analysis background tasks
- Test bulk operation processing

## Test Execution Checklist

### Pre-Test Setup
- [ ] Database is clean and seeded with test data
- [ ] Redis server is running
- [ ] Celery workers are running
- [ ] Environment variables are set
- [ ] API documentation is accessible

### Test Categories
- [ ] Authentication and authorization
- [ ] CRUD operations for all models
- [ ] AI-powered features
- [ ] File upload and media handling
- [ ] Background task processing
- [ ] Email notifications
- [ ] Rate limiting and security
- [ ] Error handling and edge cases
- [ ] Performance under load

### Post-Test Cleanup
- [ ] Reset test database
- [ ] Clear Redis cache
- [ ] Archive test results
- [ ] Update test documentation

## Automated Testing Commands

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test apps.posts
python manage.py test apps.analytics
python manage.py test apps.authentication

# Run with coverage
coverage run --source='.' manage.py test
coverage report
coverage html

# Run API integration tests
python manage.py test tests.integration

# Run performance tests
python manage.py test tests.performance
```

## API Testing Tools

### Recommended Tools
1. **Postman** - For manual API testing and collection management
2. **pytest + requests** - For automated Python testing
3. **Django REST Framework test client** - For unit testing
4. **Artillery.js** - For load testing
5. **OWASP ZAP** - For security testing

### Sample Postman Collection Structure
```
SMMS API Tests/
├── Authentication/
│   ├── Register User
│   ├── Login User
│   ├── Refresh Token
│   └── Get Profile
├── Posts/
│   ├── Create Post
│   ├── List Posts
│   ├── Update Post
│   └── Delete Post
├── AI Features/
│   ├── Content Suggestions
│   ├── Sentiment Analysis
│   └── Performance Prediction
└── Analytics/
    ├── Get Analytics Data
    ├── AI Insights
    └── Competitor Analysis
```

This comprehensive test plan ensures all API endpoints are thoroughly tested across different scenarios, including happy paths, error conditions, edge cases, and security considerations.
