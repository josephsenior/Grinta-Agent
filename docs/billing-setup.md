# Billing Setup Guide

This guide explains how to set up billing functionality with Stripe integration.

## Overview

The billing system allows users to:
- Add credits to their account via Stripe payments
- View their current balance
- Check subscription status

## Prerequisites

1. A Stripe account (sign up at https://stripe.com)
2. Stripe API keys (available in Stripe Dashboard)

## Environment Variables

Set the following environment variables:

```bash
# Required: Stripe Secret Key (from Stripe Dashboard)
STRIPE_SECRET_KEY=sk_test_...  # Use sk_live_... for production

# Required: Stripe Webhook Secret (for webhook verification)
# Get this from Stripe Dashboard > Developers > Webhooks
STRIPE_WEBHOOK_SECRET=whsec_...

# Optional: Frontend URL (for redirect URLs)
FRONTEND_URL=http://localhost:3001  # Your frontend URL

# Optional: Enable billing feature flag
ENABLE_BILLING=true

# Optional: Custom billing storage path
BILLING_STORAGE_PATH=.forge/billing  # Default: .forge/billing
```

## Stripe Setup

### 1. Get API Keys

1. Go to [Stripe Dashboard](https://dashboard.stripe.com)
2. Navigate to **Developers** > **API keys**
3. Copy your **Secret key** (starts with `sk_test_` for test mode or `sk_live_` for production)
4. Set it as `STRIPE_SECRET_KEY` environment variable

### 2. Set Up Webhooks

1. Go to **Developers** > **Webhooks** in Stripe Dashboard
2. Click **Add endpoint**
3. Set the endpoint URL to: `https://your-domain.com/api/billing/webhook`
4. Select events to listen for:
   - `checkout.session.completed`
   - `payment_intent.succeeded`
5. Copy the **Signing secret** (starts with `whsec_`)
6. Set it as `STRIPE_WEBHOOK_SECRET` environment variable

### 3. Test Mode vs Production

- **Test Mode**: Use `sk_test_...` keys for development/testing
- **Production**: Use `sk_live_...` keys for live payments

## Installation

1. Install dependencies (Stripe is already added to `pyproject.toml`):

```bash
poetry install
# or
pip install stripe
```

## API Endpoints

### Get User Balance

```http
GET /api/billing/credits
Authorization: Bearer <token>
```

**Response:**
```json
{
  "credits": "100.00"
}
```

### Create Checkout Session

```http
POST /api/billing/create-checkout-session
Authorization: Bearer <token>
Content-Type: application/json

{
  "amount": 50  // Amount in USD (minimum 10, maximum 25000)
}
```

**Response:**
```json
{
  "redirect_url": "https://checkout.stripe.com/..."
}
```

### Get Subscription Access

```http
GET /api/billing/subscription-access
Authorization: Bearer <token>
```

**Response:**
```json
{
  "status": "ACTIVE",
  "start_at": "2024-01-01T00:00:00",
  "end_at": "2024-12-31T23:59:59",
  "created_at": "2024-01-01T00:00:00"
}
```

### Webhook Endpoint

```http
POST /api/billing/webhook
Stripe-Signature: <signature>
Content-Type: application/json

<stripe event payload>
```

This endpoint is called by Stripe to notify about payment events. It automatically:
- Updates user balance when payment is completed
- Processes subscription changes

## Storage

Billing data is stored in JSON files:
- **Balances**: `.forge/billing/balances.json`
- **Subscriptions**: `.forge/billing/subscriptions.json`

You can customize the storage path with `BILLING_STORAGE_PATH` environment variable.

## Testing

### Test with Stripe Test Cards

Use Stripe's test card numbers:
- **Success**: `4242 4242 4242 4242`
- **Decline**: `4000 0000 0000 0002`
- **Requires Authentication**: `4000 0025 0000 3155`

Use any future expiry date, any 3-digit CVC, and any ZIP code.

### Test Webhooks Locally

Use Stripe CLI to forward webhooks to your local server:

```bash
# Install Stripe CLI
# https://stripe.com/docs/stripe-cli

# Login to Stripe
stripe login

# Forward webhooks to local server
stripe listen --forward-to localhost:8000/api/billing/webhook
```

This will give you a webhook signing secret to use for local testing.

## Troubleshooting

### "Payment processing is not configured"

- Ensure `STRIPE_SECRET_KEY` is set
- Check that the key is valid (starts with `sk_test_` or `sk_live_`)

### Webhook signature verification fails

- Ensure `STRIPE_WEBHOOK_SECRET` is set correctly
- Verify the webhook endpoint URL in Stripe Dashboard matches your server
- For local testing, use Stripe CLI to get the correct signing secret

### Balance not updating after payment

- Check webhook logs in Stripe Dashboard
- Verify webhook endpoint is accessible
- Check server logs for webhook processing errors
- Ensure webhook events are enabled in Stripe Dashboard

## Security Notes

1. **Never commit API keys** to version control
2. Use environment variables or secure secret management
3. Always verify webhook signatures (handled automatically)
4. Use HTTPS in production for webhook endpoints
5. Regularly rotate API keys

## Production Checklist

- [ ] Set `STRIPE_SECRET_KEY` with production key (`sk_live_...`)
- [ ] Set `STRIPE_WEBHOOK_SECRET` from production webhook
- [ ] Configure webhook endpoint in Stripe Dashboard
- [ ] Enable `ENABLE_BILLING=true`
- [ ] Set `FRONTEND_URL` to production URL
- [ ] Test payment flow end-to-end
- [ ] Monitor webhook delivery in Stripe Dashboard
- [ ] Set up error alerting for failed payments

