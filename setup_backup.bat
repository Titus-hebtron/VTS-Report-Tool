@echo off
echo Setting up VTS Automated Backup System
echo ======================================

echo Installing required Python packages...
pip install -r requirements_backup.txt

echo.
echo Google Drive Setup Instructions:
echo ================================
echo 1. Go to Google Cloud Console (https://console.cloud.google.com/)
echo 2. Create a new project or select existing one
echo 3. Enable Google Drive API
echo 4. Create OAuth 2.0 credentials (Desktop application)
echo 5. Download credentials.json and place it in the project root
echo 6. Run the backup script once to authenticate: python backup_script.py
echo.
echo Email Setup Instructions:
echo ========================
echo 1. For Gmail: Enable 2-factor authentication
echo 2. Generate an App Password
echo 3. Update SMTP_USERNAME and SMTP_PASSWORD in backup_script.py
echo.
echo To run the backup manually: python backup_script.py
echo To run the scheduler: python backup_scheduler.py
echo.
echo To install as Windows service (optional):
echo - Use NSSM (Non-Sucking Service Manager) or Windows Task Scheduler
echo - Schedule backup_scheduler.py to run at startup
echo.
pause