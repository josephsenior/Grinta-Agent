# Error Tracking Setup (Sentry)

This guide explains how to set up and configure Sentry for error tracking in Forge.

## Overview

Sentry provides:
- **Error tracking** - Capture and track errors in real-time
- **Performance monitoring** - Track application performance
- **Release tracking** - Monitor errors by release version
- **User context** - See which users are affected by errors

## Quick Setup

### 1. Create Sentry Account

1. Sign up at https://sentry.io
2. Create a new organization (if needed)
3. Create two projects:
   - **Backend** (Python/Django)
   - **Frontend** (React)

### 2. Get Your DSN

After creating projects, you'll get a DSN (Data Source Name) for each:
- Backend DSN: `https://xxx@xxx.ingest.sentry.io/xxx`
- Frontend DSN: `https://xxx@xxx.ingest.sentry.io/xxx`

### 3. Configure Environment Variables

#### Backend

Add to your `.env` file:

```bash
SENTRY_DSN=https://your-backend-dsn@sentry.io/project-id
SENTRY_ENVIRONMENT=production
SENTRY_RELEASE=1.0.0
SENTRY_SAMPLE_RATE=1.0
SENTRY_TRACES_SAMPLE_RATE=0.1
```

#### Frontend

Add to your `.env` file (or build-time variables):

```bash
VITE_SENTRY_DSN=https://your-frontend-dsn@sentry.io/project-id
VITE_SENTRY_ENVIRONMENT=production
VITE_SENTRY_RELEASE=1.0.0
VITE_SENTRY_SAMPLE_RATE=1.0
VITE_SENTRY_TRACES_SAMPLE_RATE=0.1
```

### 4. Install Sentry SDK (Backend)

```bash
pip install sentry-sdk
```

### 5. Install Sentry SDK (Frontend)

```bash
cd frontend
pnpm add @sentry/react
```

### 6. Verify Setup

```bash
# Check configuration
python backend/scripts/setup/setup_sentry.py --check

# Test error reporting
python backend/scripts/setup/setup_sentry.py --test
```

## Backend Configuration

### Automatic Initialization

Sentry is automatically initialized in `forge/server/app.py` if `SENTRY_DSN` is set.

### Manual Initialization (if needed)

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
    release=os.getenv("SENTRY_RELEASE", "unknown"),
    traces_sample_rate=0.1,
    integrations=[
        FastApiIntegration(),
        SqlalchemyIntegration(),
    ],
)
```

## Frontend Configuration

### Automatic Initialization

Sentry is automatically initialized in `frontend/src/entry.client.tsx` if `VITE_SENTRY_DSN` is set.

### Features

- ✅ Automatic error capture
- ✅ Performance monitoring (10% of transactions)
- ✅ Session replay (masked for privacy)
- ✅ User context tracking
- ✅ Release tracking

## Configuration Options

### Sample Rates

**Error Sampling (`SENTRY_SAMPLE_RATE`):**
- `1.0` = 100% of errors (recommended for production)
- `0.5` = 50% of errors
- `0.1` = 10% of errors

**Performance Tracing (`SENTRY_TRACES_SAMPLE_RATE`):**
- `0.1` = 10% of transactions (recommended)
- `1.0` = 100% (high volume, may be expensive)
- `0.0` = Disabled

### Environments

Set `SENTRY_ENVIRONMENT` to distinguish between:
- `production` - Live production environment
- `staging` - Staging environment
- `development` - Development environment

### Releases

Set `SENTRY_RELEASE` to track errors by version:
- `1.0.0` - Semantic version
- `git-commit-hash` - Git commit hash
- `build-number` - CI/CD build number

## Error Filtering

### Backend

Errors are automatically filtered to exclude:
- Network errors (likely user-side issues)
- Common non-actionable errors

### Frontend

Errors are filtered in `frontend/src/utils/sentry.ts`:
- Network errors (Failed to fetch, etc.)
- Common browser errors

## Monitoring

### Sentry Dashboard

Access your Sentry dashboard at:
- https://sentry.io/organizations/your-org/issues/

### Key Metrics to Monitor

1. **Error Rate** - Should be < 5%
2. **Error Volume** - Track spikes
3. **Affected Users** - How many users are impacted
4. **Performance** - P95/P99 latency

### Alerts

Configure alerts in Sentry for:
- **Critical errors** - Immediate notification
- **Error spikes** - Alert when errors increase significantly
- **New issues** - Alert when new error types appear

## Best Practices

1. ✅ **Set appropriate sample rates** - Balance between coverage and cost
2. ✅ **Use environments** - Separate production/staging/dev
3. ✅ **Track releases** - Know which version has issues
4. ✅ **Set up alerts** - Get notified of critical issues
5. ✅ **Review regularly** - Check Sentry dashboard daily
6. ✅ **Filter noise** - Exclude non-actionable errors
7. ✅ **Add context** - Include user info, request data

## Troubleshooting

### "Sentry not capturing errors"

Check:
- `SENTRY_DSN` is set correctly
- Sentry SDK is installed
- DSN format is correct (starts with `https://`)

### "Too many errors in Sentry"

- Reduce `SENTRY_SAMPLE_RATE`
- Add more error filtering
- Check for common non-actionable errors

### "Performance impact"

- Reduce `SENTRY_TRACES_SAMPLE_RATE`
- Disable session replay if not needed
- Use async error reporting

## Additional Resources

- [Sentry Documentation](https://docs.sentry.io/)
- [Sentry Python SDK](https://docs.sentry.io/platforms/python/)
- [Sentry React SDK](https://docs.sentry.io/platforms/javascript/guides/react/)

