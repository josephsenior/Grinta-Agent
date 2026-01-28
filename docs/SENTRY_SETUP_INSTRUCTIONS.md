# Sentry Setup Instructions

## ✅ Installation Complete

Both Sentry SDKs have been successfully installed:
- ✅ **Backend:** `sentry-sdk` (Python) - Installed
- ✅ **Frontend:** `@sentry/react` (React) - Installed

## 📋 Next Steps: Configure Sentry

### Step 1: Create Sentry Account & Projects

1. **Sign up at https://sentry.io** (free tier available)
2. **Create two projects:**
   - **Backend Project:** Select "Python" → "FastAPI" as the platform
   - **Frontend Project:** Select "JavaScript" → "React" as the platform
3. **Get your DSNs:**
   - Each project will provide a DSN (Data Source Name)
   - Format: `https://xxx@xxx.ingest.sentry.io/xxx`
   - Copy both DSNs (backend and frontend)

### Step 2: Add Environment Variables

Add the following to your `.env` file (in the project root):

```bash
# Sentry Error Tracking Configuration

# Backend Sentry DSN
SENTRY_DSN=https://your-backend-dsn@sentry.io/project-id

# Frontend Sentry DSN (for Vite)
VITE_SENTRY_DSN=https://your-frontend-dsn@sentry.io/project-id

# Environment (production, staging, development)
SENTRY_ENVIRONMENT=production
VITE_SENTRY_ENVIRONMENT=production

# Release version (optional, but recommended)
SENTRY_RELEASE=1.0.0
VITE_SENTRY_RELEASE=1.0.0

# Sample rates (optional, defaults shown)
SENTRY_SAMPLE_RATE=1.0          # 100% of errors
SENTRY_TRACES_SAMPLE_RATE=0.1   # 10% of performance traces
VITE_SENTRY_SAMPLE_RATE=1.0
VITE_SENTRY_TRACES_SAMPLE_RATE=0.1
```

### Step 3: Verify Configuration

Run the verification script:

```bash
python backend/scripts/setup/setup_sentry.py --check
```

Expected output:
```
Checking Sentry configuration...

Environment Variables:
  SENTRY_DSN: ✓ Set
  SENTRY_ENVIRONMENT: production
  SENTRY_RELEASE: 1.0.0

✓ Sentry DSN is configured
```

### Step 4: Test Error Reporting (Optional)

Test that errors are being sent to Sentry:

```bash
python backend/scripts/setup/setup_sentry.py --test
```

This will send a test error to your Sentry dashboard. Check your Sentry project to verify it was received.

## 🔧 How It Works

### Backend (Python/FastAPI)

Sentry is automatically initialized in `forge/server/app.py` when:
- `SENTRY_DSN` environment variable is set
- Server starts up

**Features:**
- ✅ Automatic error capture
- ✅ Performance monitoring (10% of requests)
- ✅ FastAPI integration
- ✅ SQLAlchemy integration

### Frontend (React)

Sentry is automatically initialized in `frontend/src/entry.client.tsx` when:
- `VITE_SENTRY_DSN` environment variable is set
- Application runs in production mode

**Features:**
- ✅ Automatic error capture
- ✅ Performance monitoring (10% of transactions)
- ✅ Session replay (privacy-masked)
- ✅ User context tracking
- ✅ Network error filtering

## 📊 Monitoring

Once configured, you can:

1. **View errors in Sentry dashboard:**
   - Go to https://sentry.io/organizations/your-org/issues/
   - See real-time error tracking
   - Get alerts for new errors

2. **Set up alerts:**
   - Configure email/Slack notifications
   - Set thresholds for error rates
   - Get notified of critical issues

3. **Track releases:**
   - Monitor errors by version
   - See which releases have issues
   - Track error trends over time

## 🎯 Best Practices

1. **Start with high sample rates** (1.0) to catch all errors during beta
2. **Reduce sample rates** in production if volume is high
3. **Set up alerts** for critical errors
4. **Review errors regularly** to identify patterns
5. **Use releases** to track which version has issues

## 🚨 Troubleshooting

### "Sentry DSN not configured"
- Make sure `.env` file exists in project root
- Verify `SENTRY_DSN` and `VITE_SENTRY_DSN` are set
- Restart the server/frontend after adding env vars

### "sentry-sdk not installed"
- Run: `pip install sentry-sdk`
- Verify installation: `pip list | grep sentry`

### "Errors not appearing in Sentry"
- Check DSN is correct
- Verify environment variables are loaded
- Check Sentry project settings
- Look for errors in browser console (frontend)

### Frontend errors not captured
- Make sure `VITE_SENTRY_DSN` is set (not just `SENTRY_DSN`)
- Vite requires `VITE_` prefix for env vars
- Rebuild frontend after adding env vars: `pnpm run build`

## 📝 Notes

- Sentry only initializes in **production mode** for frontend
- Backend Sentry works in all environments
- Network errors are filtered out (user-side issues)
- Session replay is privacy-masked (text/media hidden)

---

**Status:** ✅ SDKs installed, ready for configuration
**Next:** Add DSNs to `.env` file and restart application

