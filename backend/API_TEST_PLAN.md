# API Test Plan

## Backend Server

Run command: `python manage.py runserver_with_celery --no-celery`
Run celery worker: `celery -A social_media_manager worker --loglevel=info --pool=solo`

Run celery beats:`celery -A social_media_manager beat --loglevel=info`

## X/Twitter OAuth Testing

### 1. Manual Frontend Testing

1.Start both frontend and backend servers
2. Navigate to: `http://localhost:3000/dashboard/integrations`
3. Click "Connect" on the Twitter card
4. Complete OAuth flow on X/Twitter
5. Verify redirect back to integrations page
6. Check if Twitter shows as "Connected"

### 2. Backend Endpoint Testing

Run the test script:

```bash
python test_twitter_oauth.py
```

### 3. Manual Backend Testing

Test individual endpoints using curl or browser:

#### OAuth Flow Endpoints

- **Start OAuth**: `GET http://localhost:8000/api/integrations/twitter/authorize/`
- **OAuth Callback**: `GET http://localhost:8000/api/integrations/twitter/callback/`
- **Social Auth**: `GET http://localhost:8000/oauth/login/twitter/`

#### API Endpoints

- **Verify Credentials**: `GET http://localhost:8000/api/integrations/twitter/verify/`
- **Rate Limit**: `GET http://localhost:8000/api/integrations/twitter/rate-limit/`
- **My Posts**: `GET http://localhost:8000/api/integrations/twitter/my-posts/`

### 4. Environment Variables Check

Ensure these are set in your environment:
-`TWITTER_API_KEY`
-`TWITTER_API_KEY_SECRET`
-`TWITTER_BEARER_TOKEN`
-`TWITTER_ACCESS_TOKEN`
-`TWITTER_ACCESS_TOKEN_SECRET`
-`SOCIAL_AUTH_TWITTER_KEY`
-`SOCIAL_AUTH_TWITTER_SECRET`

### 5. Expected OAuth Flow

1. **Frontend** → `GET /api/integrations/twitter/authorize/`
2. **Backend** → Redirect to X/Twitter authorization
3. **X/Twitter** → User authorizes app
4. **X/Twitter** → `GET /api/integrations/twitter/callback/?code=...`
5. **Backend** → Process OAuth tokens
6. **Backend** → Redirect to `http://localhost:3000/dashboard/integrations/twitter/callback`
7. **Frontend** → Handle callback and bind tokens
8. **Frontend** → Redirect to `/dashboard/integrations`

### 6. Troubleshooting

- Check browser console for errors
- Check Django server logs
- Verify X Developer Portal callback URL matches: `http://localhost:8000/oauth/complete/twitter/`
- Ensure all environment variables are loaded
