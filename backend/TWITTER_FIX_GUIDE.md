# Twitter App Configuration Fix

## The "Something went wrong" Error

The error you're seeing typically occurs when the redirect URI in your OAuth request doesn't match what's configured in your Twitter app settings.

## Steps to Fix:

### 1. Configure Redirect URI in Twitter App
You need to add the redirect URI to your Twitter app settings:

1. Go to your Twitter Developer Portal
2. Navigate to your app (Default project-1948504189044490246)
3. Click on "App settings" or "Settings"
4. Look for "Authentication settings" or "OAuth 2.0 settings"
5. Add this exact redirect URI:
   ```
   http://127.0.0.1:8000/api/integrations/twitter/callback/
   ```

### 2. Enable OAuth 2.0
Make sure OAuth 2.0 is enabled in your app settings:
- Look for "OAuth 2.0" settings
- Ensure it's enabled/turned on
- Check that "Confidential client" is selected (not "Public client")

### 3. App Permissions
Verify your app has the required permissions:
- Read and Write permissions
- Users and Tweets permissions

### 4. Environment Variables
Update your environment variables with the credentials from the portal:

```bash
TWITTER_CLIENT_ID=SVZ5M2lINmtzekVHa0t5ODJXVTI6MTpjaQ
TWITTER_CLIENT_SECRET=RHIBYqoFLnBEBC9ng1DQ_HNImoIZZfOUb40ESaq7H1osBY6pe7
TWITTER_REDIRECT_URI=http://127.0.0.1:8000/api/integrations/twitter/callback/
```

### 5. Test the Authorization URL
After configuring the redirect URI, test the OAuth flow again.

## Common Issues:
- Redirect URI mismatch (most common)
- OAuth 2.0 not enabled
- App in "Restricted" mode
- Missing permissions
- Using HTTP instead of HTTPS in production

## Next Steps:
1. Configure the redirect URI in your Twitter app
2. Test the OAuth flow
3. Check the browser network tab for the actual authorization URL being generated
4. Verify the URL parameters match your app configuration