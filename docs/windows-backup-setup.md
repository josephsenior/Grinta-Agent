# Windows Database Backup Setup Guide

This guide will help you set up automated database backups on Windows.

## Prerequisites

### 1. PostgreSQL Client Tools

The backup script requires `pg_dump` which comes with PostgreSQL. You have two options:

#### Option A: Full PostgreSQL Installation (Recommended)

If you don't have PostgreSQL installed:

1. **Download PostgreSQL:**
   - Go to https://www.postgresql.org/download/windows/
   - Download the installer (latest version recommended)

2. **Install PostgreSQL:**
   - Run the installer
   - During installation, make sure to install:
     - ✅ PostgreSQL Server
     - ✅ Command Line Tools (includes pg_dump)
   - Note the installation path (usually `C:\Program Files\PostgreSQL\15\bin`)

3. **Add to PATH (if not automatic):**
   - Open System Properties → Environment Variables
   - Add to PATH: `C:\Program Files\PostgreSQL\15\bin` (adjust version number)
   - Restart your terminal/PowerShell

4. **Verify installation:**
   ```powershell
   pg_dump --version
   psql --version
   ```

#### Option B: PostgreSQL Client Only (Lighter)

If you only need the backup tools (not the full server):

1. **Download PostgreSQL Binaries:**
   - Download from: https://www.enterprisedb.com/download-postgresql-binaries
   - Extract to a folder (e.g., `C:\PostgreSQL\bin`)

2. **Add to PATH:**
   - Add `C:\PostgreSQL\bin` to your system PATH
   - Restart terminal

3. **Verify:**
   ```powershell
   pg_dump --version
   ```

### 2. Verify Database Connection

Make sure your database is running and accessible:

```powershell
# Test connection (will prompt for password)
psql -h localhost -p 5432 -U postgres -d forge
```

If connection works, you're ready for backups!

## Setup Automated Backups

### Step 1: Test Backup Script

First, verify the backup script works:

```powershell
# Make sure you're in the project root
cd C:\Users\GIGABYTE\Desktop\Forge

# Test backup
python scripts/backup_database.py --backup
```

Expected output:
```
Creating database backup...
Backup directory: backups
Running pg_dump...
✓ Created SQL backup: backups\forge_backup_20250115_120000.sql
✓ Backup created successfully: backups\forge_backup_20250115_120000.dump
  Size: 0.XX MB
  Format: Custom (compressed)
```

### Step 2: Set Up Scheduled Task

#### Automated Setup (Easiest)

1. **Right-click PowerShell** and select **"Run as Administrator"**

2. **Navigate to project:**
   ```powershell
   cd C:\Users\GIGABYTE\Desktop\Forge
   ```

3. **Run setup script:**
   ```powershell
   .\scripts\setup_windows_backup_task.ps1
   ```

The script will:
- ✅ Create a scheduled task named "Forge-Database-Backup"
- ✅ Set it to run daily at 2:00 AM
- ✅ Test the backup script
- ✅ Show you how to manage the task

#### Manual Setup (Alternative)

If you prefer to set it up manually:

1. **Open Task Scheduler:**
   - Press `Win + R`
   - Type: `taskschd.msc`
   - Press Enter

2. **Create Basic Task:**
   - Click "Create Basic Task" in the right panel
   - Name: `Forge-Database-Backup`
   - Description: `Automated daily backup of Forge PostgreSQL database`

3. **Set Trigger:**
   - Trigger: Daily
   - Start time: `2:00:00 AM`
   - Recur every: `1 days`

4. **Set Action:**
   - Action: Start a program
   - Program/script: `python` (or full path like `C:\Python312\python.exe`)
   - Add arguments: `scripts\backup_database.py --backup`
   - Start in: `C:\Users\GIGABYTE\Desktop\Forge`

5. **Configure Settings:**
   - General tab: Check "Run whether user is logged on or not"
   - General tab: Check "Run with highest privileges"
   - Conditions tab: Uncheck "Start only if on AC power"
   - Settings tab: Check "Allow task to be run on demand"

6. **Save and test:**
   - Click OK
   - Right-click the task → "Run" to test immediately

### Step 3: Verify Backup Works

1. **List backups:**
   ```powershell
   python scripts/backup_database.py --list
   ```

2. **Test restore (optional):**
   ```powershell
   # List backups first
   python scripts/backup_database.py --list
   
   # Restore from a backup (use actual filename)
   python scripts/backup_database.py --restore backups\forge_backup_20250115_120000.sql
   ```

3. **Check scheduled task:**
   - Open Task Scheduler
   - Navigate to: Task Scheduler Library → Forge-Database-Backup
   - Check "Last Run Result" (should be 0x0 if successful)

## Troubleshooting

### "pg_dump not found"

**Solution:** Install PostgreSQL client tools (see Prerequisites above)

**Quick check:**
```powershell
where pg_dump
```

If not found, add PostgreSQL bin directory to PATH.

### "Authentication failed"

**Solution:** Check your `.env` file has correct database credentials:
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=forge
DB_USER=postgres
DB_PASSWORD=your_password
```

### "Database connection failed"

**Solution:** 
1. Make sure PostgreSQL is running
2. Check connection: `psql -h localhost -U postgres -d forge`
3. Verify firewall allows connections on port 5432

### Task runs but backup fails

**Check task history:**
1. Open Task Scheduler
2. Find "Forge-Database-Backup"
3. Click "History" tab
4. Look for error messages

**Common issues:**
- Python not in PATH → Use full path to python.exe
- Working directory wrong → Set "Start in" to project root
- Environment variables not loaded → Task needs to load .env file

### Backup file is empty or very small

**Possible causes:**
- Database is empty (normal for new installations)
- Only schema backed up (no data)
- Backup format issue

**Check backup content:**
```powershell
# View SQL backup (first 50 lines)
Get-Content backups\forge_backup_*.sql -Head 50
```

## Managing Backups

### List All Backups

```powershell
python scripts/backup_database.py --list
```

### Cleanup Old Backups

```powershell
# Remove backups older than 30 days (default)
python scripts/backup_database.py --cleanup

# Remove backups older than 7 days
python scripts/backup_database.py --cleanup --days 7
```

### Manual Backup

```powershell
# Create backup now
python scripts/backup_database.py --backup
```

### Restore from Backup

```powershell
# List available backups
python scripts/backup_database.py --list

# Restore specific backup
python scripts/backup_database.py --restore backups\forge_backup_20250115_120000.sql
```

## Backup Storage

### Local Storage (Default)

Backups are stored in `./backups/` directory by default.

**Pros:**
- Fast access
- No additional costs
- Simple setup

**Cons:**
- Not protected from disk failure
- Requires manual off-site backup

### Cloud Storage (Recommended for Production)

After backup, upload to cloud storage:

#### AWS S3
```powershell
# Install AWS CLI first: https://aws.amazon.com/cli/
aws s3 cp backups\forge_backup_*.sql s3://your-bucket/forge-backups/
```

#### Google Cloud Storage
```powershell
# Install gcloud CLI first
gsutil cp backups\forge_backup_*.sql gs://your-bucket/forge-backups/
```

#### Azure Blob Storage
```powershell
# Install Azure CLI first
az storage blob upload --file backups\forge_backup_*.sql --container-name backups
```

## Monitoring

### Check Last Backup

```powershell
# List backups (sorted by date, newest first)
python scripts/backup_database.py --list
```

### Check Task Status

1. Open Task Scheduler
2. Navigate to: Task Scheduler Library → Forge-Database-Backup
3. Check:
   - **Last Run Time:** When backup last ran
   - **Last Run Result:** 0x0 = success, other = error
   - **Next Run Time:** When next backup is scheduled

### Set Up Alerts (Optional)

You can create a PowerShell script to check backup status and send alerts:

```powershell
# Check if backup exists from last 25 hours
$backups = Get-ChildItem backups\forge_backup_*.sql | Sort-Object LastWriteTime -Descending
$latest = $backups[0]
$age = (Get-Date) - $latest.LastWriteTime

if ($age.TotalHours -gt 25) {
    # Send alert (email, Slack, etc.)
    Write-Host "WARNING: No backup in last 25 hours!"
}
```

## Next Steps

1. ✅ Install PostgreSQL client tools
2. ✅ Test backup script
3. ✅ Set up scheduled task
4. ✅ Verify backups are created
5. ⏭️ Set up cloud storage upload (optional)
6. ⏭️ Configure backup monitoring (optional)

---

**Need Help?** Check `docs/DATABASE_BACKUPS.md` for more details.

