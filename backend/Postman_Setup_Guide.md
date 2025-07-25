# Postman Environment Variables

This file contains the environment variables you need to set up in Postman for testing the SMMS API.

## Required Environment Variables

Create a new environment in Postman and add these variables:

### Base Configuration
- `base_url`: `http://localhost:8000` (or your Django server URL)

### Authentication Variables (Auto-populated by tests)
- `access_token`: `` (will be filled automatically after login)
- `refresh_token`: `` (will be filled automatically after login)

### Test Data Variables (Auto-populated by tests)
- `test_post_id`: `` (will be filled automatically when creating test posts)
- `test_user_id`: `` (will be filled automatically after registration)

## How to Use

1. **Import Collection**: Import the `SMMS_Postman_Collection.json` file into Postman
2. **Create Environment**: Create a new environment in Postman
3. **Set Variables**: Add the variables listed above to your environment
4. **Select Environment**: Make sure to select your environment before running tests
5. **Run Tests**: Execute requests in order, starting with Authentication

## Test Flow Recommendations

### Quick Test Flow
1. Login User (to get auth tokens)
2. Get Profile (to verify authentication)
3. Create Post (to test basic functionality)
4. AI Content Suggestions (to test AI features)
5. Sentiment Analysis (to test AI sentiment features)
6. Get Analytics Data (to test analytics)
7. Delete Test Post (cleanup)

### Complete Test Flow
1. **Authentication Tests**
   - Register User (creates new user and gets tokens)
   - Login User (alternative login method)
   - Get Profile (verify authentication works)

2. **Posts Tests**
   - Create Post (creates test post, saves ID)
   - List Posts (verify post appears)
   - Get Post Detail (verify individual post retrieval)

3. **AI Features Tests**
   - AI Content Suggestions (test content generation)
   - Sentiment Analysis - Single Comment (test individual comment analysis)
   - Sentiment Analysis - Post Comments (test bulk comment analysis)

4. **Analytics Tests**
   - Get Analytics Data (test analytics retrieval)
   - AI Insights (test AI-powered insights)

5. **Cleanup**
   - Delete Test Post (remove test data)

## Notes

- The collection includes automatic test scripts that validate responses
- Variables are automatically populated between requests
- Authentication is handled automatically once you login
- Test data is created and cleaned up automatically
- All requests include proper error handling and validation

## Troubleshooting

### Common Issues
1. **401 Unauthorized**: Make sure you've run the login request first
2. **404 Not Found**: Check that your Django server is running on the correct port
3. **500 Server Error**: Check Django server logs for detailed error information
4. **Variable Not Set**: Ensure requests are run in order so variables get populated

### Debug Tips
- Check the Postman console for detailed request/response information
- Verify environment variables are set correctly
- Ensure Django server is running with `python manage.py runserver`
- Check Django logs for backend errors
