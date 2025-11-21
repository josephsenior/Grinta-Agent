# Database Setup Guide

This guide explains how to set up PostgreSQL for user storage in Forge.

## Quick Start

### 1. Install PostgreSQL

**Windows:**
- Download from [PostgreSQL Downloads](https://www.postgresql.org/download/windows/)
- Or use Chocolatey: `choco install postgresql`

**macOS:**
```bash
brew install postgresql@15
brew services start postgresql@15
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

### 2. Create Database and User

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE forge;

# Create user (optional, or use existing postgres user)
CREATE USER forge WITH PASSWORD 'forge';
GRANT ALL PRIVILEGES ON DATABASE forge TO forge;

# Exit psql
\q
```

### 3. Configure Environment Variables

Create or update your `.env` file:

```bash
# User Storage Configuration
USER_STORAGE_TYPE=database  # Use "database" for PostgreSQL, "file" for file-based storage

# Database Connection
DB_HOST=localhost
DB_PORT=5432
DB_NAME=forge
DB_USER=forge
DB_PASSWORD=forge
```

### 4. Run Migrations

```bash
# From the project root
python -m forge.storage.user.migrations.run_migrations
```

Or using Poetry:

```bash
poetry run python -m forge.storage.user.migrations.run_migrations
```

### 5. Verify Setup

The migrations will create the `users` table with all necessary indexes. You can verify:

```bash
psql -U forge -d forge -c "\dt users"
psql -U forge -d forge -c "\d users"
```

## Storage Backend Options

### File-Based Storage (Default)
- **Use case**: Development, testing, single-user deployments
- **Configuration**: `USER_STORAGE_TYPE=file` or leave unset
- **Storage location**: `.forge/users/users.json`

### Database Storage (Recommended for Production)
- **Use case**: Production, multi-user, SaaS deployments
- **Configuration**: `USER_STORAGE_TYPE=database`
- **Database**: PostgreSQL (configured via `DB_*` environment variables)

## Migration from File to Database

If you have existing users in file storage and want to migrate to database:

1. **Export users from file storage** (if needed, users will be created on first login)
2. **Set up database** (follow steps above)
3. **Change `USER_STORAGE_TYPE=database`**
4. **Restart the application**

Users will be created in the database on their next login/registration.

## Troubleshooting

### Connection Errors

**Error: "connection refused"**
- Make sure PostgreSQL is running: `pg_isready` or `sudo systemctl status postgresql`
- Check host/port in environment variables

**Error: "database does not exist"**
- Create the database: `createdb -U postgres forge`

**Error: "password authentication failed"**
- Check `DB_USER` and `DB_PASSWORD` in your `.env` file
- Verify user exists: `psql -U postgres -c "\du"`

### Migration Errors

**Error: "relation already exists"**
- The table already exists. This is safe to ignore, or drop and recreate:
  ```sql
  DROP TABLE IF EXISTS users CASCADE;
  ```

**Error: "permission denied"**
- Grant proper permissions:
  ```sql
  GRANT ALL PRIVILEGES ON DATABASE forge TO forge;
  GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO forge;
  ```

## Production Considerations

1. **Connection Pooling**: The implementation uses asyncpg connection pooling (2-10 connections)
2. **Backups**: Set up regular PostgreSQL backups
3. **Monitoring**: Monitor database performance and connection pool usage
4. **Security**: Use strong passwords and consider SSL connections for production
5. **Scaling**: For high-traffic scenarios, consider read replicas or connection pooler (PgBouncer)

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `USER_STORAGE_TYPE` | `file` | Storage backend: `file` or `database` |
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_NAME` | `forge` | Database name |
| `DB_USER` | `forge` | Database user |
| `DB_PASSWORD` | `forge` | Database password |

