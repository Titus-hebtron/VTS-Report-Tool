#!/usr/bin/env python3
"""
Automated Database Restore from Google Drive
Restores the latest database backup from Google Drive every day at 06:00
Includes integrity checks and email notifications
"""

import os
import sqlite3
import shutil
import datetime
import time
import logging
from pathlib import Path

# Google Drive API imports
try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    from google.auth.transport.requests import Request
    import pickle
    import io
except ImportError:
    print("Google API libraries not installed. Install with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    exit(1)

# Email imports
try:
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
except ImportError:
    print("Email libraries not installed. Install with: pip install secure-smtplib")
    exit(1)

# Configuration
DB_PATH = 'vts_database.db'
BACKUP_DIR = 'backups'
RESTORE_DIR = 'restores'
GOOGLE_DRIVE_FOLDER_ID = None  # Will be set after finding folder
EMAIL_RECIPIENT = 'hebtron25@gmail.com'

# Email configuration
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USERNAME = 'your-email@gmail.com'  # Replace with your email
SMTP_PASSWORD = 'your-app-password'  # Replace with app password

# Google Drive API scopes
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Setup logging
logging.basicConfig(
    filename='restore.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_google_drive_service():
    """Authenticate and return Google Drive service"""
    creds = None
    token_path = 'token.pickle'

    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise Exception("Google Drive authentication not set up. Please run backup_script.py first.")

        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    return build('drive', 'v3', credentials=creds)

def find_backup_folder(service):
    """Find the VTS_Backups folder in Google Drive"""
    global GOOGLE_DRIVE_FOLDER_ID

    if GOOGLE_DRIVE_FOLDER_ID:
        return GOOGLE_DRIVE_FOLDER_ID

    # Search for the backup folder
    query = f"name='VTS_Backups' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, spaces='drive').execute()
    items = results.get('files', [])

    if not items:
        raise Exception("VTS_Backups folder not found in Google Drive. Please run backup_script.py first.")

    GOOGLE_DRIVE_FOLDER_ID = items[0]['id']
    return GOOGLE_DRIVE_FOLDER_ID

def get_latest_database_backup(service):
    """Get the latest database backup from Google Drive"""
    folder_id = find_backup_folder(service)

    # Search for database backup files
    query = f"'{folder_id}' in parents and name contains 'vts_database_backup_' and trashed=false"
    results = service.files().list(
        q=query,
        spaces='drive',
        orderBy='createdTime desc',
        pageSize=1
    ).execute()

    items = results.get('files', [])
    if not items:
        raise Exception("No database backup files found in Google Drive.")

    return items[0]  # Latest backup

def download_file(service, file_id, file_name):
    """Download a file from Google Drive"""
    request = service.files().get_media(fileId=file_id)

    # Create restore directory if it doesn't exist
    os.makedirs(RESTORE_DIR, exist_ok=True)

    file_path = os.path.join(RESTORE_DIR, file_name)

    with io.FileIO(file_path, 'wb') as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            logging.info(f"Download {int(status.progress() * 100)}%.")

    return file_path

def validate_database_backup(backup_path):
    """Validate that the downloaded backup is a valid SQLite database"""
    try:
        # Try to connect to the database
        conn = sqlite3.connect(backup_path)
        cursor = conn.cursor()

        # Check if it has the expected tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]

        # Expected tables (adjust based on your schema)
        expected_tables = ['users', 'contractors', 'vehicles', 'patrol_logs', 'idle_reports', 'incident_reports']

        missing_tables = [table for table in expected_tables if table not in table_names]
        if missing_tables:
            raise Exception(f"Backup missing expected tables: {missing_tables}")

        # Check if database is not corrupted
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        if result[0] != 'ok':
            raise Exception(f"Database integrity check failed: {result[0]}")

        conn.close()
        logging.info(f"Database backup validation successful: {backup_path}")
        return True

    except Exception as e:
        logging.error(f"Database backup validation failed: {e}")
        return False

def backup_current_database():
    """Create a backup of the current database before restoration"""
    if not os.path.exists(DB_PATH):
        logging.warning("Current database does not exist, skipping pre-restore backup")
        return None

    # Create backups directory if it doesn't exist
    os.makedirs(BACKUP_DIR, exist_ok=True)

    # Generate backup filename with timestamp
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f'pre_restore_backup_{timestamp}.db'
    backup_path = os.path.join(BACKUP_DIR, backup_filename)

    # Create backup
    shutil.copy2(DB_PATH, backup_path)

    logging.info(f"Pre-restore backup created: {backup_path}")
    return backup_path

def restore_database(backup_path):
    """Restore the database from backup"""
    try:
        # Create a backup of current database first
        pre_backup = backup_current_database()

        # Replace current database with backup
        shutil.copy2(backup_path, DB_PATH)

        logging.info(f"Database restored successfully from: {backup_path}")
        return True, pre_backup

    except Exception as e:
        logging.error(f"Database restoration failed: {e}")
        return False, None

def send_email_notification(subject, body, attachment_paths=None):
    """Send email notification with optional attachments"""
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USERNAME
        msg['To'] = EMAIL_RECIPIENT
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        # Attach files if provided
        if attachment_paths:
            from email.mime.base import MIMEBase
            from email import encoders
            for attachment_path in attachment_paths:
                if os.path.exists(attachment_path):
                    with open(attachment_path, 'rb') as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename={os.path.basename(attachment_path)}'
                        )
                        msg.attach(part)

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        text = msg.as_string()
        server.sendmail(SMTP_USERNAME, EMAIL_RECIPIENT, text)
        server.quit()

        logging.info(f"Email notification sent to {EMAIL_RECIPIENT}")

    except Exception as e:
        logging.error(f"Failed to send email notification: {e}")

def cleanup_old_restores():
    """Keep only the last 7 restore files locally"""
    try:
        restore_files = []
        for file in os.listdir(RESTORE_DIR):
            if file.startswith('vts_database_backup_'):
                restore_files.append(os.path.join(RESTORE_DIR, file))

        # Sort by modification time (newest first)
        restore_files.sort(key=os.path.getmtime, reverse=True)

        # Remove older restores (keep only 7 most recent)
        for old_file in restore_files[7:]:
            os.remove(old_file)
            logging.info(f"Cleaned up old restore: {old_file}")

    except Exception as e:
        logging.warning(f"Failed to cleanup old restores: {e}")

def perform_restore():
    """Main restore function"""
    try:
        logging.info("Starting automated database restore...")

        # Get Google Drive service
        service = get_google_drive_service()

        # Find latest backup
        latest_backup = get_latest_database_backup(service)
        logging.info(f"Found latest backup: {latest_backup['name']} (ID: {latest_backup['id']})")

        # Download the backup
        downloaded_path = download_file(service, latest_backup['id'], latest_backup['name'])
        logging.info(f"Downloaded backup to: {downloaded_path}")

        # Validate the backup
        if not validate_database_backup(downloaded_path):
            raise Exception("Downloaded backup failed validation")

        # Restore the database
        success, pre_backup = restore_database(downloaded_path)

        if success:
            # Send success notification
            subject = "VTS Database Restore Completed Successfully"
            body = f"""VTS Database Restore Completed Successfully

Restore Details:
- Backup File: {latest_backup['name']}
- Backup Date: {latest_backup['createdTime']}
- Restored At: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Pre-restore Backup: {pre_backup if pre_backup else 'None (first restore)'}

The database has been successfully restored from the latest Google Drive backup.
"""

            send_email_notification(subject, body)

            # Cleanup old restore files
            cleanup_old_restores()

            logging.info("Database restore completed successfully")
        else:
            raise Exception("Database restoration failed")

    except Exception as e:
        error_msg = f"Restore failed: {str(e)}"
        logging.error(error_msg)

        # Send error notification
        send_email_notification(
            "VTS Database Restore Failed",
            f"Automated database restore encountered an error:\n\n{error_msg}\n\nPlease check the system logs and restore manually if needed."
        )

def main():
    """Main function - run restore immediately"""
    print("VTS Automated Database Restore")
    print("=" * 40)
    print(f"Database: {DB_PATH}")
    print(f"Restore Directory: {RESTORE_DIR}")
    print(f"Email Notifications: {EMAIL_RECIPIENT}")
    print()

    # Check if required files exist
    if not os.path.exists('token.pickle'):
        print("❌ Google Drive authentication not set up. Please run backup_script.py first.")
        return

    # Run restore
    print("Running database restore...")
    perform_restore()
    print("Restore process completed. Check restore.log for details.")

if __name__ == "__main__":
    main()