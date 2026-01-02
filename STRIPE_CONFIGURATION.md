# Stripe Payment Integration Guide for Thrive Travel App

## Overview

This guide provides step-by-step instructions for configuring Stripe payment integration in the Thrive Travel application. Stripe is used for processing subscription upgrades and handling refunds.

## Prerequisites

- Stripe account (sign up at [https://stripe.com](https://stripe.com))
- Python `stripe` package (should be installed via `pip install stripe`)
- Access to your backend `.env` or configuration file

## Step 1: Create a Stripe Account

1. Go to [https://stripe.com](https://stripe.com)
2. Click "Sign up" and create your account
3. Complete the account verification process
4. Navigate to the Stripe Dashboard

## Step 2: Get Your API Keys

### For Development/Testing

1. In the Stripe Dashboard, click on "Developers" in the left sidebar
2. Click on "API keys"
3. You'll see two types of keys:
   - **Publishable key** (starts with `pk_test_`): Used in frontend
   - **Secret key** (starts with `sk_test_`): Used in backend
4. Copy both keys (you'll need them in the next steps)

> **Note**: Test mode keys allow you to test payments without processing real transactions. Use test card numbers like `4242 4242 4242 4242` for testing.

### For Production

1. Toggle the "View test data" switch to OFF in the Stripe Dashboard
2. Navigate to "Developers" → "API keys"
3. Copy your live keys:
   - **Publishable key** (starts with `pk_live_`)
   - **Secret key** (starts with `sk_live_`)

> **Warning**: Never commit live API keys to version control!

## Step 3: Configure Backend Environment Variables

### Option A: Using .env File (Recommended)

1. Navigate to your backend directory:
   ```bash
   cd /home/vault/Documents/Bundle/backend
   ```

2. Open or create the `.env` file:
   ```bash
   nano .env
   ```

3. Add the following Stripe configuration:
   ```env
   # Stripe Configuration
   STRIPE_SECRET_KEY=sk_test_your_secret_key_here
   STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
   STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
   
   # Support Email (for contact form notifications)
   SUPPORT_EMAIL=support@thrivetravel.com
   
   # Frontend URL (for email links)
   FRONTEND_URL=http://localhost:3000
   ```

4. Replace the placeholder values with your actual Stripe keys

5. Save and close the file (Ctrl+X, then Y, then Enter in nano)

### Option B: Using config.py

1. Open `backend/config.py`:
   ```bash
   nano /home/vault/Documents/Bundle/backend/config.py
   ```

2. Add Stripe configuration to the `Config` class:
   ```python
   class Config:
       # ... existing configuration ...
       
       # Stripe Configuration
       STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY') or 'sk_test_your_key_here'
       STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY') or 'pk_test_your_key_here'
       STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET') or ''
       
       # Email Configuration
       SUPPORT_EMAIL = os.environ.get('SUPPORT_EMAIL') or 'support@thrivetravel.com'
       
       # Frontend URL
       FRONTEND_URL = os.environ.get('FRONTEND_URL') or 'http://localhost:3000'
   ```

## Step 4: Install Stripe Python Package

If not already installed, install the Stripe Python library:

```bash
cd /home/vault/Documents/Bundle/backend
pip install stripe
```

Or add to your `requirements.txt`:
```
stripe>=5.0.0
```

Then install:
```bash
pip install -r requirements.txt
```

## Step 5: Configure Frontend (Next.js)

### Install Stripe.js

```bash
cd /home/vault/Documents/Bundle/Thrive
npm install @stripe/stripe-js @stripe/react-stripe-js
```

### Create Stripe Configuration File

Create `Thrive/lib/stripe.ts`:

```typescript
import { loadStripe } from '@stripe/stripe-js';

// Load Stripe publishable key from environment variable
const stripePromise = loadStripe(
  process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY || ''
);

export default stripePromise;
```

### Add Environment Variable

Create or update `Thrive/.env.local`:

```env
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
NEXT_PUBLIC_API_URL=http://localhost:5000
```

## Step 6: Set Up Stripe Webhooks (Optional but Recommended)

Webhooks allow Stripe to notify your application about payment events.

### For Development (Using Stripe CLI)

1. Install Stripe CLI:
   ```bash
   # On Linux
   wget https://github.com/stripe/stripe-cli/releases/download/v1.19.0/stripe_1.19.0_linux_x86_64.tar.gz
   tar -xvf stripe_1.19.0_linux_x86_64.tar.gz
   sudo mv stripe /usr/local/bin/
   ```

2. Login to Stripe CLI:
   ```bash
   stripe login
   ```

3. Forward webhooks to your local server:
   ```bash
   stripe listen --forward-to localhost:5000/api/webhooks/stripe
   ```

4. Copy the webhook signing secret (starts with `whsec_`) and add it to your `.env`:
   ```env
   STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
   ```

### For Production

1. In Stripe Dashboard, go to "Developers" → "Webhooks"
2. Click "Add endpoint"
3. Enter your production URL: `https://yourdomain.com/api/webhooks/stripe`
4. Select events to listen for:
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
   - `charge.refunded`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
5. Copy the webhook signing secret and add it to your production environment variables

## Step 7: Test the Integration

### Test Subscription Upgrade

1. Start your backend server:
   ```bash
   cd /home/vault/Documents/Bundle/backend
   flask run --debug
   ```

2. Start your frontend server:
   ```bash
   cd /home/vault/Documents/Bundle/Thrive
   npm run dev
   ```

3. Login to your application
4. Navigate to the dashboard subscriptions page
5. Click "Upgrade" on a subscription tier
6. Use a test card number:
   - **Success**: `4242 4242 4242 4242`
   - **Decline**: `4000 0000 0000 0002`
   - **Requires Authentication**: `4000 0025 0000 3155`
   - Any future expiry date (e.g., 12/34)
   - Any 3-digit CVC
   - Any postal code

7. Verify the subscription upgrade was successful

### Test Refunds

1. Create a booking with a payment
2. Cancel the booking
3. Check that the refund is processed in Stripe Dashboard

## Step 8: Security Best Practices

### 1. Never Expose Secret Keys

- ❌ Never commit secret keys to Git
- ❌ Never use secret keys in frontend code
- ✅ Always use environment variables
- ✅ Add `.env` to `.gitignore`

### 2. Validate Webhook Signatures

The backend code already validates webhook signatures using `STRIPE_WEBHOOK_SECRET`. Make sure this is configured.

### 3. Use HTTPS in Production

Stripe requires HTTPS for production webhooks and payment processing.

### 4. Implement Idempotency

The backend uses Stripe's built-in idempotency for payment intents to prevent duplicate charges.

### 5. Handle Errors Gracefully

The backend includes comprehensive error handling for Stripe errors. Monitor logs for any issues.

## Step 9: Monitor Payments

### Stripe Dashboard

1. Go to [https://dashboard.stripe.com](https://dashboard.stripe.com)
2. View all payments in the "Payments" section
3. Check customer details in the "Customers" section
4. Monitor subscription status in "Subscriptions"

### Application Logs

Monitor your Flask application logs for Stripe-related events:

```bash
tail -f /path/to/your/logs/flask.log
```

## Troubleshooting

### Issue: "Payment processing is not configured"

**Solution**: Ensure `STRIPE_SECRET_KEY` is set in your environment variables or config file.

### Issue: "Invalid API key provided"

**Solution**: 
- Verify your API key is correct
- Make sure you're using the right key for your environment (test vs live)
- Check that there are no extra spaces or quotes in the key

### Issue: "No such customer"

**Solution**: This happens when a customer ID doesn't exist. The backend creates customers automatically, but if you're testing with old data, clear your database and try again.

### Issue: Webhook signature verification failed

**Solution**:
- Ensure `STRIPE_WEBHOOK_SECRET` is correctly set
- If using Stripe CLI, make sure it's running and forwarding to the correct URL
- In production, verify the webhook endpoint URL matches exactly

### Issue: "This payment requires authentication"

**Solution**: This is expected for certain test cards. Use the Stripe Elements UI to handle 3D Secure authentication, or use a different test card.

## Additional Resources

- [Stripe API Documentation](https://stripe.com/docs/api)
- [Stripe Python Library](https://stripe.com/docs/api/python)
- [Stripe Testing Guide](https://stripe.com/docs/testing)
- [Stripe Webhooks Guide](https://stripe.com/docs/webhooks)
- [Stripe Dashboard](https://dashboard.stripe.com)

## Support

If you encounter any issues:

1. Check the Stripe Dashboard for error messages
2. Review application logs for detailed error information
3. Consult the Stripe documentation
4. Contact Stripe support at [https://support.stripe.com](https://support.stripe.com)

## Next Steps

After configuring Stripe:

1. ✅ Test subscription upgrades with test cards
2. ✅ Test booking cancellations and refunds
3. ✅ Set up webhook endpoints for production
4. ✅ Configure production API keys when ready to go live
5. ✅ Implement additional payment features as needed (recurring billing, invoices, etc.)
