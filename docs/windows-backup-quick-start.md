# Windows Backup Quick Start

## ✅ PostgreSQL Found!

Your PostgreSQL installation was found at:
**`C:\Program Files\PostgreSQL\18\bin`**

## Quick Setup

### Step 1: Add to .env File

Add this line to your `.env` file:

```bash
POSTGRES_BIN=C:\Program Files\PostgreSQL\18\bin
```

This tells the backup script where to find `pg_dump.exe`.

### Step 2: Test Backup

```powershell
python backend/scripts/database/backup_database.py --backup
```

Expected output:
```
✓ Created SQL backup: backups\forge_backup_YYYYMMDD_HHMMSS.sql
✓ Backup created successfully
```

### Step 3: Set Up Automated Backups

Run the setup script as **Administrator**:

```powershell
# Right-click PowerShell → "Run as Administrator"
cd C:\Users\GIGABYTE\Desktop\Forge
.\scripts\setup_windows_backup_task.ps1
```

This will:
- Create a scheduled task named "Forge-Database-Backup"
- Set it to run daily at 2:00 AM
- Test the backup script

### Step 4: Verify

```powershell
# List backups
python backend/scripts/database/backup_database.py --list

# Check scheduled task
# Open Task Scheduler → Task Scheduler Library → Forge-Database-Backup
```

## Alternative: Add to PATH (Optional)

If you prefer to add PostgreSQL to your system PATH:

1. Open **System Properties** → **Environment Variables**
2. Edit **Path** in **System variables**
3. Add: `C:\Program Files\PostgreSQL\18\bin`
4. Restart your terminal/PowerShell

Then you can remove `POSTGRES_BIN` from `.env` (it will be found automatically).

## Troubleshooting

**Backup fails with "pg_dump not found":**
- Make sure `POSTGRES_BIN` is set in `.env` or PATH
- Verify: `Test-Path "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe"`

**Scheduled task doesn't run:**
- Check Task Scheduler → History tab for errors
- Make sure Python is in PATH for the scheduled task
- Verify `.env` file is in the project root

## Next Steps

- ✅ Backup script tested and working
- ⏭️ Set up scheduled task (run setup script as Admin)
- ⏭️ Configure cloud storage upload (optional)
- ⏭️ Set up backup monitoring (optional)

See `docs/DATABASE_BACKUPS.md` for complete documentation.

