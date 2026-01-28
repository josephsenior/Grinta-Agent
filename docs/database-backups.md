# Database Backup Strategy

This document outlines the backup strategy for Forge's PostgreSQL database.

## Overview

Forge uses PostgreSQL for user storage in production. Regular backups are **critical** for data protection and disaster recovery.

## Backup Script

The backup script is located at `backend/scripts/database/backup_database.py`.

### Features

- ✅ Full database backups (custom format, compressed)
- ✅ Plain SQL backups (for easy inspection)
- ✅ Automated cleanup of old backups
- ✅ Restore functionality
- ✅ Backup listing

## Quick Start

### Create a Backup

```bash
# Set database credentials
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=forge
export DB_USER=postgres
export DB_PASSWORD=your_password

# Create backup
python backend/scripts/database/backup_database.py --backup
```

Backups are stored in `./backups/` by default (configurable via `BACKUP_DIR` env var).

### Restore from Backup

```bash
# List available backups
python scripts/backup_database.py --list

# Restore a specific backup
python backend/scripts/database/backup_database.py --restore backups/forge_backup_20250115_120000.sql
```

### Cleanup Old Backups

```bash
# Remove backups older than 30 days (default)
python backend/scripts/database/backup_database.py --cleanup

# Remove backups older than 7 days
python backend/scripts/database/backup_database.py --cleanup --days 7
```

## Automated Backups

### Cron Job (Linux/macOS)

Add to crontab for daily backups at 2 AM:

```bash
# Edit crontab
crontab -e

# Add this line (adjust paths as needed)
0 2 * * * cd /path/to/forge && /usr/bin/python3 backend/scripts/database/backup_database.py --backup >> /var/log/forge_backup.log 2>&1
```

### Windows Task Scheduler

#### Option 1: Automated Setup (Recommended)

Run the setup script as Administrator:

```powershell
# Right-click PowerShell and select "Run as Administrator"
cd C:\path\to\Forge
.\scripts\setup_windows_backup_task.ps1
```

Or use the batch file:
```cmd
# Right-click and select "Run as Administrator"
scripts\setup_windows_backup_task.bat
```

The script will:
- Create a scheduled task named "Forge-Database-Backup"
- Set it to run daily at 2:00 AM (configurable)
- Test the backup script
- Show you how to manage the task

#### Option 2: Manual Setup

1. Open Task Scheduler (search "Task Scheduler" in Start menu)
2. Click "Create Basic Task" in the right panel
3. **General Tab:**
   - Name: `Forge-Database-Backup`
   - Description: `Automated daily backup of Forge PostgreSQL database`
   - Check "Run whether user is logged on or not"
   - Check "Run with highest privileges"
4. **Trigger Tab:**
   - Select "Daily"
   - Set time: `2:00:00 AM`
   - Recur every: `1 days`
5. **Action Tab:**
   - Action: "Start a program"
   - Program/script: `python` (or full path: `C:\Python312\python.exe`)
   - Add arguments: `scripts\backup_database.py --backup`
   - Start in: `C:\path\to\Forge` (your project root)
6. **Conditions Tab:**
   - Uncheck "Start the task only if the computer is on AC power"
   - Check "Wake the computer to run this task" (optional)
7. **Settings Tab:**
   - Check "Allow task to be run on demand"
   - Check "Run task as soon as possible after a scheduled start is missed"
   - If the task fails, restart every: `1 minute`, Attempt to restart up to: `3 times`
8. Click "OK" and enter your password if prompted

#### Verify the Task

1. Open Task Scheduler
2. Navigate to: Task Scheduler Library → Forge-Database-Backup
3. Right-click → "Run" to test immediately
4. Check "Last Run Result" to verify it worked

### Docker/Container Environments

Add to your docker-compose.yml or Kubernetes CronJob:

```yaml
# docker-compose.yml
services:
  backup:
    image: postgres:15-alpine
    environment:
      - PGHOST=${DB_HOST}
      - PGPORT=${DB_PORT}
      - PGDATABASE=${DB_NAME}
      - PGUSER=${DB_USER}
      - PGPASSWORD=${DB_PASSWORD}
    volumes:
      - ./backups:/backups
    command: >
      sh -c "
        pg_dump -h $${PGHOST} -U $${PGUSER} -d $${PGDATABASE} -F c -f /backups/forge_backup_$$(date +%Y%m%d_%H%M%S).dump
      "
    restart: "no"
```

## Backup Retention Policy

**Recommended:**
- **Daily backups:** Keep for 30 days
- **Weekly backups:** Keep for 12 weeks (3 months)
- **Monthly backups:** Keep for 12 months (1 year)

**Implementation:**

```bash
# Daily cleanup (keep 30 days)
python backend/scripts/database/backup_database.py --cleanup --days 30

# Weekly cleanup (keep 90 days) - run weekly
python backend/scripts/database/backup_database.py --cleanup --days 90
```

## Backup Storage

### Local Storage

Backups are stored locally by default in `./backups/`.

**Pros:**
- Fast access
- No additional costs
- Simple setup

**Cons:**
- Not protected from disk failure
- Requires manual off-site backup

### Cloud Storage (Recommended for Production)

#### AWS S3

```bash
# After creating backup, upload to S3
aws s3 cp backups/forge_backup_*.sql s3://your-bucket/forge-backups/
```

#### Google Cloud Storage

```bash
# Upload to GCS
gsutil cp backups/forge_backup_*.sql gs://your-bucket/forge-backups/
```

#### Azure Blob Storage

```bash
# Upload to Azure
az storage blob upload --file backups/forge_backup_*.sql --container-name backups --name forge_backup_*.sql
```

### Encrypted Backups

For sensitive data, encrypt backups before storage:

```bash
# Encrypt backup
gpg --symmetric --cipher-algo AES256 backups/forge_backup_20250115_120000.sql

# Decrypt backup
gpg --decrypt backups/forge_backup_20250115_120000.sql.gpg > restore.sql
```

## Restore Procedures

### Full Database Restore

1. **Stop the application** (if running)
2. **Verify backup file exists**
3. **Restore from backup:**
   ```bash
   python backend/scripts/database/backup_database.py --restore backups/forge_backup_20250115_120000.sql
   ```
4. **Verify data integrity**
5. **Restart the application**

### Point-in-Time Recovery

PostgreSQL supports point-in-time recovery (PITR) with WAL archiving. This requires:
- Continuous archiving of WAL files
- Base backup + WAL files
- `recovery.conf` configuration

See [PostgreSQL PITR documentation](https://www.postgresql.org/docs/current/continuous-archiving.html) for details.

## Testing Backups

**Regularly test your backups!** A backup that can't be restored is useless.

### Monthly Test Procedure

1. Create a test database
2. Restore backup to test database
3. Verify data integrity
4. Test application against restored database
5. Document results

```bash
# Create test database
createdb forge_test

# Restore to test database
psql -d forge_test -f backups/forge_backup_20250115_120000.sql

# Verify
psql -d forge_test -c "SELECT COUNT(*) FROM users;"
```

## Monitoring

### Backup Success Monitoring

Monitor backup script execution:

```bash
# Check last backup time
ls -lt backups/ | head -2

# Check backup script logs
tail -f /var/log/forge_backup.log
```

### Alerting

Set up alerts for:
- Backup failures
- Backup age (if no backup in 25 hours, alert)
- Backup size anomalies (unusually small/large)

## Disaster Recovery Plan

### Scenario 1: Database Corruption

1. Stop application
2. Identify last known good backup
3. Restore from backup
4. Verify data integrity
5. Restart application
6. Investigate root cause

### Scenario 2: Accidental Data Deletion

1. Stop application immediately
2. Identify backup before deletion
3. Restore from backup
4. Verify data
5. Restart application

### Scenario 3: Complete Server Failure

1. Provision new server
2. Install PostgreSQL
3. Restore from most recent backup
4. Restore application
5. Verify functionality
6. Update DNS/load balancer

## Best Practices

1. ✅ **Automate backups** - Don't rely on manual backups
2. ✅ **Test restores regularly** - Monthly at minimum
3. ✅ **Store backups off-site** - Use cloud storage
4. ✅ **Encrypt sensitive backups** - Protect user data
5. ✅ **Monitor backup success** - Set up alerts
6. ✅ **Document procedures** - Keep runbook updated
7. ✅ **Version backups** - Keep multiple backup versions
8. ✅ **Regular cleanup** - Remove old backups automatically

## Troubleshooting

### Backup Fails: "pg_dump not found"

Install PostgreSQL client tools:
- Ubuntu/Debian: `sudo apt-get install postgresql-client`
- macOS: `brew install postgresql`
- Windows: Install PostgreSQL from https://www.postgresql.org/download/

### Backup Fails: "Authentication failed"

Verify database credentials:
```bash
export DB_PASSWORD=your_password
```

### Restore Fails: "Database is being accessed"

Stop the application before restoring:
```bash
# Stop Forge application
# Then restore
python backend/scripts/database/backup_database.py --restore backup.sql
```

## Additional Resources

- [PostgreSQL Backup Documentation](https://www.postgresql.org/docs/current/backup.html)
- [pg_dump Documentation](https://www.postgresql.org/docs/current/app-pgdump.html)
- [pg_restore Documentation](https://www.postgresql.org/docs/current/app-pgrestore.html)

