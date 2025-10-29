# VTS Automated Backup System

This system provides automated backups of your VTS database and uploaded images to Google Drive with email notifications.

## Features

- **Database Backup**: SQLite database backup with timestamp
- **Image Backup**: Compressed ZIP archive of all uploaded accident images
- **Google Drive Upload**: Automatic upload to dedicated Google Drive folder
- **Email Notifications**: Success/failure notifications sent to hebtron25@gmail.com
- **Automated Scheduling**: Runs every 21 hours automatically
- **Local Cleanup**: Keeps only last 5 backup files locally

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements_backup.txt
```

Or run the setup script:
```bash
setup_backup.bat
```

### 2. Google Drive Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Google Drive API
4. Create OAuth 2.0 credentials (Desktop application type)
5. Download `credentials.json` and place it in the project root directory
6. Run the backup script once to authenticate:
   ```bash
   python backup_script.py
   ```
   This will open a browser for authentication and create `token.pickle`

### 3. Email Setup

For Gmail notifications, you need to:

1. Enable 2-factor authentication on your Gmail account
2. Generate an App Password:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate a password for "Mail"
3. Update the email configuration in `backup_script.py`:
   ```python
   SMTP_USERNAME = 'your-gmail@gmail.com'
   SMTP_PASSWORD = 'your-app-password'  # Not your regular password!
   ```

### 4. Running the Backup

#### Manual Backup
```bash
python backup_script.py
```

#### Automated Scheduler
```bash
python backup_scheduler.py
```

#### Windows Task Scheduler (Recommended for Production)

1. Open Task Scheduler
2. Create a new task:
   - Name: VTS Backup
   - Trigger: Daily, every 21 hours
   - Action: Start a program
   - Program: `python.exe`
   - Arguments: `backup_scheduler.py`
   - Start in: `D:\gps-report-tool` (your project directory)

#### Windows Service (Alternative)

Use NSSM (Non-Sucking Service Manager):
```bash
nssm install VTSBackup "C:\Python313\python.exe" "D:\gps-report-tool\backup_scheduler.py"
nssm start VTSBackup
```

## Configuration

Edit `backup_script.py` to customize:

```python
# File paths
DB_PATH = 'vts_database.db'
IMAGES_DIR = 'uploaded_accident_images'
BACKUP_DIR = 'backups'

# Backup settings
BACKUP_INTERVAL_HOURS = 21
EMAIL_RECIPIENT = 'hebtron25@gmail.com'

# Email settings (update these!)
SMTP_USERNAME = 'your-email@gmail.com'
SMTP_PASSWORD = 'your-app-password'
```

## Backup Process

1. **Database Backup**: Creates a copy of `vts_database.db` with timestamp
2. **Image Backup**: Compresses `uploaded_accident_images/` into ZIP file
3. **Google Drive Upload**: Uploads both files to "VTS_Backups" folder
4. **Email Notification**: Sends success/failure report to hebtron25@gmail.com
5. **Cleanup**: Removes old local backups (keeps last 5)

## Monitoring

- Check `backup.log` for detailed logs
- Check `backup_scheduler.log` for scheduler activity
- Email notifications will alert you of any issues

## Troubleshooting

### Google Drive Authentication Issues
- Delete `token.pickle` and re-run authentication
- Ensure `credentials.json` is in the project root
- Check Google Cloud Console API permissions

### Email Issues
- Verify App Password is correct (not regular password)
- Check Gmail security settings
- Ensure less secure app access is enabled (if using regular password)

### Permission Issues
- Ensure write permissions to backup directory
- Run as administrator if needed

## Security Notes

- Never commit `credentials.json`, `token.pickle`, or email passwords to Git
- Use App Passwords for Gmail instead of regular passwords
- Regularly rotate API credentials
- Monitor Google Drive storage usage

## File Structure

```
project/
├── backup_script.py          # Main backup logic
├── backup_scheduler.py       # Scheduler service
├── setup_backup.bat         # Setup script
├── requirements_backup.txt  # Python dependencies
├── credentials.json         # Google API credentials (create manually)
├── token.pickle            # OAuth token (generated)
├── backup.log              # Backup logs
├── backup_scheduler.log    # Scheduler logs
└── backups/                # Local backup storage
    ├── vts_database_backup_20231029_120000.db
    └── uploaded_images_backup_20231029_120000.zip