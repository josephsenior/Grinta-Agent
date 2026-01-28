# Database Scripts

Scripts for database setup, backup, and management.

## Scripts

- **`setup_database.py`** - Create database and run migrations
- **`backup_database.py`** - Backup and restore PostgreSQL database
- **`verify_database.py`** - Verify database setup and connectivity
- **`query_users_sql.py`** - Query users directly from PostgreSQL
- **`list_users.py`** - List all users in the database
- **`check_storage_config.py`** - Check user storage configuration

## Usage

```bash
# Setup database
python backend/scripts/database/setup_database.py

# Backup database
python backend/scripts/database/backup_database.py --backup

# Verify database
python backend/scripts/database/verify_database.py

# Query users
python backend/scripts/database/query_users_sql.py
```
