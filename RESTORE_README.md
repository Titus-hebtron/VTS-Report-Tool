# VTS Automated Database Restore System

This system provides automated daily database restoration from Google Drive backups at 06:00 every morning, ensuring data recovery in case of data loss.

## Features

- **Daily Automatic Restore**: Runs every day at 06:00
- **Google Drive Integration**: Downloads latest backup from Google Drive
- **Database Integrity Checks**: Validates backup before restoration
- **Pre-restore Backup**: Creates backup of current database before restoration
- **Email Notifications**: Success/failure notifications sent to hebtron25@gmail.com
- **Web Interface**: Manual restore and backup info available in VTS app

## How It Works

1. **Daily at 06:00**: `restore_scheduler.py` triggers the restore process
2. **Download Latest Backup**: Downloads the most recent database backup from Google Drive
3. **Integrity Validation**: Checks database integrity and required tables
4. **Pre-restore Backup**: Creates a backup of current database (safety measure)
5. **Database Replacement**: Replaces current database with downloaded backup
6. **Email Notification**: Sends success/failure report to hebtron25@gmail.com

## Setup Instructions

### 1. Prerequisites

Ensure backup system is set up first:
```bash
# Install dependencies
pip install -r requirements_backup.txt

# Run backup script once to authenticate with Google Drive
python backup_script.py
```

### 2. Email Configuration

Update email settings in `restore_script.py`:
```python
SMTP_USERNAME = 'your-email@gmail.com'  # Replace with your email
SMTP_PASSWORD = 'your-app-password'    # Replace with app password
```

### 3. Running the Restore System

#### Manual Restore (Testing)
```bash
python restore_script.py
```

#### Automated Daily Restore
```bash
python restore_scheduler.py
```

#### Windows Task Scheduler (Recommended for Production)

1. Open Task Scheduler
2. Create a new task:
   - Name: VTS Daily Restore
   - Trigger: Daily at 06:00
   - Action: Start a program
   - Program: `python.exe`
   - Arguments: `restore_scheduler.py`
   - Start in: `D:\gps-report-tool`

#### Windows Service (Alternative)

Use NSSM:
```bash
nssm install VTSDailyRestore "C:\Python313\python.exe" "D:\gps-report-tool\restore_scheduler.py"
nssm start VTSDailyRestore
```

## Safety Features

### Database Integrity Checks
- Validates SQLite database structure
- Checks for required tables (users, contractors, vehicles, etc.)
- Runs `PRAGMA integrity_check` to ensure database is not corrupted

### Pre-restore Backup
- Creates timestamped backup of current database before restoration
- Stored in `backups/` directory with filename: `pre_restore_backup_YYYYMMDD_HHMMSS.db`

### Rollback Capability
- If restore fails, original database remains intact
- Pre-restore backup can be manually restored if needed

## Monitoring

### Log Files
- `restore.log`: Detailed restore operation logs
- `restore_scheduler.log`: Scheduler activity logs

### Email Notifications
- **Success**: Confirmation with restore details
- **Failure**: Error details with troubleshooting information

### Web Interface
- **Backup Management Page**: Available to Resident Engineer in VTS app
- **Manual Restore**: Trigger restore manually from web interface
- **Backup Info**: View latest backup details from Google Drive

## File Structure

```
project/
├── restore_script.py          # Main restore logic
├── restore_scheduler.py       # Daily scheduler
├── backup_management.py       # Web interface for restores
├── restores/                  # Downloaded restore files (auto-cleaned)
├── backups/                   # Local backup storage
│   ├── pre_restore_backup_*.db    # Pre-restore safety backups
│   └── vts_database_backup_*.db   # Regular backups
├── restore.log               # Restore operation logs
└── restore_scheduler.log     # Scheduler logs
```

## Configuration

Edit `restore_script.py` to customize:

```python
# File paths
DB_PATH = 'vts_database.db'
RESTORE_DIR = 'restores'

# Email configuration
SMTP_USERNAME = 'your-email@gmail.com'
SMTP_PASSWORD = 'your-app-password'
EMAIL_RECIPIENT = 'hebtron25@gmail.com'

# Required database tables (for validation)
REQUIRED_TABLES = ['users', 'contractors', 'vehicles', 'patrol_logs', 'idle_reports', 'incident_reports']
```

## Troubleshooting

### Restore Fails - No Backup Found
- Ensure backup system is running and creating backups
- Check Google Drive authentication (`token.pickle` exists)
- Verify "VTS_Backups" folder exists in Google Drive

### Database Integrity Check Fails
- Backup file may be corrupted
- Check `restore.log` for specific error details
- Manual intervention may be required

### Email Notifications Not Working
- Verify SMTP credentials
- Check Gmail app password setup
- Ensure firewall allows SMTP connections

### Permission Issues
- Ensure write permissions to database and restore directories
- Run as administrator if needed

## Security Considerations

- Database backups contain sensitive information
- Google Drive folder should be private
- Email credentials should use app passwords, not regular passwords
- Regularly rotate API credentials and app passwords

## Integration with Backup System

The restore system works seamlessly with the backup system:

1. **Backup System** (every 21 hours):
   - Creates database and image backups
   - Uploads to Google Drive
   - Sends backup notifications

2. **Restore System** (daily at 06:00):
   - Downloads latest database backup
   - Validates and restores database
   - Sends restore notifications

This ensures your VTS database is automatically backed up frequently and restored daily, providing robust data protection and recovery capabilities.