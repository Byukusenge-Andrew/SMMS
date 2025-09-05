# Manual Stripe Payment Testing Guide

## ✅ Step 1: Verify Server is Running
Your Django server should be running at: http://127.0.0.1:8000/

## ✅ Step 2: Subscription Tiers Working
The test confirmed 5 subscription tiers are available:
- Starter: $0/month (Free tier)
- Basic Plan: $7.99/month, $79.90/year 
- Professional: $14.99/month, $149.90/year
- Enterprise: $19.99/month, $199.90/year
- Professional: $29/month, $290/year (duplicate - need to clean up)

## 🧪 Step 3: Test the API Endpoints

### Test Subscription Tiers (No Auth Required)
```bash
curl -X GET "http://127.0.0.1:8000/api/billing/api/subscription-tiers/" -H "Content-Type: application/json"
```

### Test Checkout Session (Requires Auth)
First, you need to create a user account and get authenticated.

#### Option A: Create User via Django Admin
1. Go to: http://127.0.0.1:8000/admin/
2. Login with your superuser account
3. Create a test user

#### Option B: Create User via API (if registration endpoint exists)
```bash
curl -X POST "http://127.0.0.1:8000/api/auth/register/" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com", 
    "password": "testpass123",
    "first_name": "Test",
    "last_name": "User"
  }'
```

#### Get Authentication Token
```bash
curl -X POST "http://127.0.0.1:8000/api/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test@example.com",
    "password": "testpass123"
  }'
```

#### Create Checkout Session
Replace `YOUR_TOKEN_HERE` with the token from login:
```bash
curl -X POST "http://127.0.0.1:8000/api/billing/stripe/checkout/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "tier_id": "TIER_ID_FROM_TIERS_RESPONSE",
    "billing_period": "monthly"
  }'
```

## 🔄 Step 4: Test Payment Flow

### Using Browser (Recommended)
1. **Get Checkout URL**: Use the checkout session API above or create a simple frontend
2. **Open Checkout**: Visit the returned checkout_url in your browser
3. **Test Payment**: Use Stripe test card numbers:
   - Success: `4242 4242 4242 4242`
   - Any future expiry date (e.g., 12/34)
   - Any 3-digit CVC (e.g., 123)
   - Any postal code

### Expected Flow:
1. ✅ Redirect to Stripe Checkout
2. ✅ Fill in test card details
3. ✅ Complete payment
4. ✅ Redirect back to your success URL
5. ✅ Webhook processes the payment
6. ✅ User subscription is activated

## 🔍 Step 5: Verify Results

### Check Subscription Status
```bash
curl -X GET "http://127.0.0.1:8000/api/billing/api/subscription-status/" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Check Django Admin
1. Go to: http://127.0.0.1:8000/admin/
2. Check `Billing > User subscriptions` 
3. Verify the subscription was created

### Check Stripe Dashboard
1. Login to your Stripe dashboard
2. Go to Payments > Customers
3. Verify the test customer and subscription

## 🛠️ Troubleshooting

### Common Issues:
1. **CORS Error**: Make sure CORS is configured for your frontend domain
2. **Webhook Not Working**: Ensure STRIPE_WEBHOOK_SECRET is set
3. **Authentication Issues**: Verify the auth endpoints match your authentication setup

### Debug Commands:
```bash
# Check Django logs
tail -f logs/django.log

# Test webhook locally (if using Stripe CLI)
stripe listen --forward-to localhost:8000/api/billing/stripe/webhook/

# Check database
python manage.py shell
>>> from apps.billing.models import UserSubscription
>>> UserSubscription.objects.all()
```

## 🎯 Next Steps After Testing

1. **Frontend Integration**: Create UI components for subscription selection
2. **Webhook Configuration**: Set up production webhook endpoint in Stripe
3. **Error Handling**: Add proper error pages and user feedback
4. **Email Notifications**: Send confirmation emails after successful payments
5. **Customer Portal**: Allow users to manage their subscriptions

## 📝 Test Checklist

- [ ] Subscription tiers API returns all plans
- [ ] User can authenticate and get token
- [ ] Checkout session creates successfully
- [ ] Stripe checkout page loads
- [ ] Test payment completes successfully
- [ ] Webhook processes payment
- [ ] User subscription is created in database
- [ ] Subscription status API shows active subscription
- [ ] Customer portal works for existing subscribers
