# Environment Variables Checklist for Render Deployment

## Required Environment Variables

Copy and paste these into your Render service environment variables section:

### Django Core
```
SECRET_KEY=generate-in-render-dashboard
DEBUG=False
ALLOWED_HOSTS=*
```

### Database
```
DATABASE_URL=postgres://postgres:andre01ab.@social-media-db.chgyuqs4suf5.eu-north-1.rds.amazonaws.com:5432/postgres?sslmode=require
```

### Redis (will be auto-populated if using Render Redis)
```
REDIS_URL=redis://red-xxxxx:6379
CELERY_BROKER_URL=redis://red-xxxxx:6379/0
CELERY_RESULT_BACKEND=redis://red-xxxxx:6379/0
```

### Email Configuration
```
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=andrebyukusenge9@gmail.com
EMAIL_HOST_PASSWORD=kxqy raah dhxh kjby
DEFAULT_FROM_EMAIL=andrebyukusenge9@gmail.com
```

### Supabase Storage
```
SUPABASE_URL=https://cudeuievwnpvmuyebmgc.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN1ZGV1aWV2d25wdm11eWVibWdjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NDExNjk3MywiZXhwIjoyMDY5NjkyOTczfQ.nsymKougaTsVPpQzFCTGNcYEeoYnbAWnId-pk_P7hNs
SUPABASE_BUCKET=keativpictures
```

### Twitter API
```
TWITTER_API_KEY=9VwiLfVqzVLrE4JjaHVijn6PB
TWITTER_API_KEY_SECRET=F5iYe9SEBnyuRsrDyUYwv22A8szxieC1wypAoX9urTh3J6HrHE
TWITTER_BEARER_TOKEN=AAAAAAAAAAAAAAAAAAAAACPs3AEAAAAA524DXLxWtp9wk%2BkAJRAjH9yvrRo%3DDo78f4oSOFDmX2rGwFoMbcdsYQSRg5Tv2HSOgCOGp5qoLRRqS4
TWITTER_ACCESS_TOKEN=1841004192564981761-xOYiDYI5kLTyrevaS4LyGVYagCtBpy
TWITTER_ACCESS_TOKEN_SECRET=GCrs6nm60j5xv9tLZx7uZq5T6Oc4NW3LI8L6OodFs0fAt
TWITTER_CLIENT_ID=your-oauth2-client-id
TWITTER_CLIENT_SECRET=your-oauth2-client-secret
TWITTER_REDIRECT_URI=https://smms-backend.onrender.com/api/integrations/twitter/callback/
TWITTER_SCOPES=tweet.read tweet.write users.read offline.access
```

### TikTok API
```
TIKTOK_CLIENT_KEY=awri2oqdqtiej4l8
TIKTOK_CLIENT_SECRET=TmRZtxxEJO5PLJZkUxGvGbntgtWYRDRn
```

### Reddit API
```
REDDIT_CLIENT_ID=Izl0HYIIusIFWyuTZQX_iQ
REDDIT_CLIENT_SECRET=your-reddit-secret
```

### Slack Integration
```
SLACK_BOT_TOKEN=xoxb-5970417719634-9252612975492-uoCdJlEXjH1nDAVlS1J5rPfp
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/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
SLACK_CLIENT_ID=5970417719634.9230548690211
SLACK_CLIENT_SECRET=22c01f64c88414cc25842b7ed1355672
SLACK_SIGNING_SECRET=9b554aa258ee184295d0bcac889fd606
SLACK_VERIFICATION_TOKEN=eXzkBjnZgjtrIboovWTF4anL
SLACK_APP_ID=A096SG4LA67
```

### Social Authentication
```
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY=751977519516-v4ts4j9fjje5mrn1gm1fdint5b57e2jn.apps.googleusercontent.com
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET=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
SOCIAL_AUTH_GITHUB_KEY=Ov23liUqIgKKYZzfVwCS
SOCIAL_AUTH_GITHUB_SECRET=14c8e732901aaa8c60c47fc1deb9c6a510a05b0d
```

### Admin User
```
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=andrebyukusenge9@gmail.com
DJANGO_SUPERUSER_PASSWORD=generate-secure-password
```

### Application Settings
```
FRONTEND_URL=https://your-frontend-domain.com
CORS_ALLOWED_ORIGINS=https://your-frontend-domain.com
WEB_CONCURRENCY=4
```

### Optional (Error Tracking)
```
SENTRY_DSN=your-sentry-dsn
```

## Instructions for Render Dashboard

1. Go to your service in Render Dashboard
2. Navigate to the "Environment" tab
3. Add each environment variable by clicking "Add Environment Variable"
4. For `SECRET_KEY` and `DJANGO_SUPERUSER_PASSWORD`, click "Generate Value" for secure random values
5. Update `FRONTEND_URL` and `CORS_ALLOWED_ORIGINS` with your actual frontend domain
6. Save all environment variables
7. Redeploy your service

## Security Notes

- Never commit sensitive keys to your repository
- Use the "Generate Value" option for secrets when possible
- Keep your API keys secure and rotate them periodically
- Consider using environment-specific keys for development vs production
