# Environment Variables Reference

Complete reference for all environment variables used by Forge.

## Quick Reference

### Required for Production

```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=forge
DB_USER=postgres
DB_PASSWORD=your_secure_password

# Authentication (if enabled)
AUTH_ENABLED=true
JWT_SECRET=your_jwt_secret_key_here

# Redis (recommended for production)
REDIS_URL=redis://localhost:6379
```

### Optional but Recommended

```bash
# Error Tracking
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
SENTRY_ENVIRONMENT=production
SENTRY_RELEASE=1.0.0

# GitHub Integration
GITHUB_PERSONAL_ACCESS_TOKEN=your_github_token

# User Storage
USER_STORAGE_TYPE=database  # or "file" for development
```

---

## Categories

### Database Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DB_HOST` | Yes (if using database) | `localhost` | PostgreSQL host |
| `DB_PORT` | No | `5432` | PostgreSQL port |
| `DB_NAME` | Yes (if using database) | `forge` | Database name |
| `DB_USER` | Yes (if using database) | `postgres` | Database user |
| `DB_PASSWORD` | Yes (if using database) | - | Database password |
| `USER_STORAGE_TYPE` | No | `file` | Storage type: `database` or `file` |

### Authentication

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AUTH_ENABLED` | No | `false` | Enable JWT authentication |
| `JWT_SECRET` | Yes (if AUTH_ENABLED) | - | Secret key for JWT tokens |
| `JWT_ALGORITHM` | No | `HS256` | JWT algorithm |
| `JWT_EXPIRATION_HOURS` | No | `24` | JWT token expiration (hours) |

### Rate Limiting & Quotas

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `RATE_LIMITING_ENABLED` | No | `true` | Enable rate limiting |
| `COST_QUOTA_ENABLED` | No | `true` | Enable cost-based quotas |
| `DEFAULT_QUOTA_PLAN` | No | `free` | Default quota plan: `free`, `pro`, `enterprise`, `unlimited` |
| `AUTH_RATE_LIMITING_ENABLED` | No | `true` | Enable auth endpoint rate limiting |
| `AUTH_LOGIN_ATTEMPTS_PER_15MIN` | No | `5` | Max login attempts per 15 minutes |
| `AUTH_REGISTER_ATTEMPTS_PER_HOUR` | No | `3` | Max registration attempts per hour |
| `AUTH_PASSWORD_RESET_PER_HOUR` | No | `3` | Max password reset attempts per hour |

### Redis Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | No | - | Redis connection URL (e.g., `redis://localhost:6379`) |
| `REDIS_HOST` | No | - | Redis host (alternative to REDIS_URL) |
| `REDIS_PORT` | No | `6379` | Redis port (if using REDIS_HOST) |
| `REDIS_PASSWORD` | No | - | Redis password |
| `REDIS_POOL_SIZE` | No | `10` | Redis connection pool size |
| `REDIS_TIMEOUT` | No | `5.0` | Redis connection timeout (seconds) |
| `REDIS_QUOTA_FALLBACK` | No | `true` | Fallback to in-memory if Redis unavailable |

### Error Tracking (Sentry)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SENTRY_DSN` | No | - | Sentry DSN for backend error tracking |
| `SENTRY_FRONTEND_DSN` | No | - | Sentry DSN for frontend error tracking |
| `SENTRY_ENVIRONMENT` | No | `production` | Environment name (production, staging, development) |
| `SENTRY_RELEASE` | No | `unknown` | Release version |
| `SENTRY_SAMPLE_RATE` | No | `1.0` | Error sampling rate (0.0-1.0) |
| `SENTRY_TRACES_SAMPLE_RATE` | No | `0.1` | Performance trace sampling rate (0.0-1.0) |

**Frontend (Vite):**
- `VITE_SENTRY_DSN` - Sentry DSN for frontend
- `VITE_SENTRY_ENVIRONMENT` - Environment name
- `VITE_SENTRY_RELEASE` - Release version
- `VITE_SENTRY_SAMPLE_RATE` - Error sampling rate
- `VITE_SENTRY_TRACES_SAMPLE_RATE` - Trace sampling rate

### Monitoring & Observability

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OBSERVABILITY_ENABLED` | No | `true` | Enable observability middleware |
| `ALERTING_ENABLED` | No | `false` | Enable alerting |
| `OTEL_ENABLED` | No | `false` | Enable OpenTelemetry tracing |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | No | - | OpenTelemetry endpoint |

### Server Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `HOST` | No | `0.0.0.0` | Server host |
| `PORT` | No | `3000` | Server port |
| `WORKERS` | No | `4` | Number of worker processes (Gunicorn) |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Security

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CSP_POLICY` | No | `strict` | Content Security Policy (strict/permissive) |
| `CSRF_PROTECTION_ENABLED` | No | `true` | Enable CSRF protection |
| `PERMITTED_CORS_ORIGINS` | No | - | Comma-separated list of allowed CORS origins |

### GitHub Integration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITHUB_PERSONAL_ACCESS_TOKEN` | No | - | GitHub personal access token |

### Runtime Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SANDBOX_RUNTIME_CONTAINER_IMAGE` | No | `forge-runtime:latest` | Runtime container image |
| `WORKSPACE_BASE` | No | `./workspace` | Workspace base directory |
| `DESIRED_NUM_WARM_SERVERS` | No | `2` | Number of warm runtime servers |
| `INIT_PLUGIN_TIMEOUT` | No | `60` | Plugin initialization timeout (seconds) |

### Backup Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BACKUP_DIR` | No | `./backups` | Directory for database backups |
| `BACKUP_RETENTION_DAYS` | No | `30` | Days to keep backups before cleanup |

---

## Environment-Specific Examples

### Development

```bash
# .env.development
DB_HOST=localhost
DB_PORT=5432
DB_NAME=forge_dev
DB_USER=postgres
DB_PASSWORD=dev_password
USER_STORAGE_TYPE=file  # Use file storage for dev
AUTH_ENABLED=false
LOG_LEVEL=DEBUG
```

### Staging

```bash
# .env.staging
DB_HOST=staging-db.example.com
DB_PORT=5432
DB_NAME=forge_staging
DB_USER=forge_staging
DB_PASSWORD=staging_secure_password
USER_STORAGE_TYPE=database
AUTH_ENABLED=true
JWT_SECRET=staging_jwt_secret
REDIS_URL=redis://staging-redis.example.com:6379
SENTRY_DSN=https://staging-dsn@sentry.io/project-id
SENTRY_ENVIRONMENT=staging
LOG_LEVEL=INFO
```

### Production

```bash
# .env.production
DB_HOST=prod-db.example.com
DB_PORT=5432
DB_NAME=forge_prod
DB_USER=forge_prod
DB_PASSWORD=production_very_secure_password
USER_STORAGE_TYPE=database
AUTH_ENABLED=true
JWT_SECRET=production_very_secure_jwt_secret
REDIS_URL=redis://prod-redis.example.com:6379
REDIS_PASSWORD=redis_secure_password
SENTRY_DSN=https://prod-dsn@sentry.io/project-id
SENTRY_ENVIRONMENT=production
SENTRY_RELEASE=1.0.0
LOG_LEVEL=WARNING
COST_QUOTA_ENABLED=true
DEFAULT_QUOTA_PLAN=free
RATE_LIMITING_ENABLED=true
AUTH_RATE_LIMITING_ENABLED=true
```

---

## Validation

### Startup Validation

The application validates critical environment variables on startup. Missing required variables will cause the application to fail with a clear error message.

### Configuration Check Script

```bash
# Check configuration
python scripts/check_config.py
```

---

## Security Best Practices

1. **Never commit `.env` files** - Add to `.gitignore`
2. **Use secret management** - Use AWS Secrets Manager, HashiCorp Vault, or similar in production
3. **Rotate secrets regularly** - Change JWT secrets, database passwords periodically
4. **Use different secrets per environment** - Never reuse production secrets in staging/dev
5. **Limit access** - Only grant access to environment variables to authorized personnel

---

## Troubleshooting

### "Database connection failed"

Check:
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` are set correctly
- Database is running and accessible
- Network connectivity to database

### "Redis connection failed"

Check:
- `REDIS_URL` is set correctly
- Redis is running
- Network connectivity to Redis
- Application will fallback to in-memory if Redis unavailable

### "Authentication failed"

Check:
- `AUTH_ENABLED=true` if authentication is required
- `JWT_SECRET` is set and matches across instances
- Token expiration settings

---

## Additional Resources

- [Database Setup Guide](DATABASE_SETUP.md)
- [Production Deployment Guide](production_deployment.md)
- [Security Documentation](security.md)

