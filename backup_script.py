#!/usr/bin/env python3
"""
Automated Database and Image Backup to Google Drive
Backs up SQLite database and uploaded images every 21 hours
Sends email notifications to hebtron25@gmail.com
"""

import os
import sqlite3
import shutil
import datetime
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import schedule
import logging
from pathlib import Path
import zipfile
import tempfile

# Google Drive API imports
try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.auth.transport.requests import Request
    import pickle
except ImportError:
    print("Google API libraries not installed. Install with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    exit(1)

# Configuration
DB_PATH = 'vts_database.db'
IMAGES_DIR = 'uploaded_accident_images'
BACKUP_DIR = 'backups'
GOOGLE_DRIVE_FOLDER_ID = None  # Will be set after folder creation
EMAIL_RECIPIENT = 'hebtron25@gmail.com'
BACKUP_INTERVAL_HOURS = 21

# Email configuration - fetched from secrets manager or env vars
SMTP_CREDENTIALS = None  # Will be loaded on demand

def get_smtp_config():
    """Fetch SMTP credentials from secrets manager or environment."""
    from secrets_utils import get_smtp_credentials
    creds = get_smtp_credentials()
    if creds:
        return creds
    else:
        # Fallback defaults (should be overridden by environment)
        return {
            'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('SMTP_PORT', '587')),
            'username': os.getenv('SMTP_USERNAME', ''),
            'password': os.getenv('SMTP_PASSWORD', '')
        }

SMTP_SERVER = None
SMTP_PORT = None
SMTP_USERNAME = 'your-email@gmail.com'  # Replace with your email
SMTP_PASSWORD = 'your-app-password'  # Replace with app password

# Google Drive API scopes
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Setup logging
logging.basicConfig(
    filename='backup.log',
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
            # Try to obtain client info from secrets manager or env
            from secrets_utils import get_google_credentials_json
            client_info = get_google_credentials_json()

            # Prefer service account key if provided
            if client_info and isinstance(client_info, dict) and 'type' in client_info and client_info.get('type') == 'service_account':
                from google.oauth2 import service_account
                creds = service_account.Credentials.from_service_account_info(client_info, scopes=SCOPES)
            elif client_info and isinstance(client_info, dict):
                # Perform interactive OAuth flow (saves token.pickle)
                try:
                    from google_auth_oauthlib.flow import InstalledAppFlow
                    flow = InstalledAppFlow.from_client_config(client_info, SCOPES)
                    creds = flow.run_local_server(port=0)
                    with open(token_path, 'wb') as token:
                        pickle.dump(creds, token)
                except Exception:
                    raise Exception("Could not perform OAuth flow. Ensure environment allows opening a browser, or provide a service account key via secrets manager.")
            else:
                raise Exception("Google Drive authentication not set up. Provide credentials via environment, AWS Secrets Manager, or Azure Key Vault.")

        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    return build('drive', 'v3', credentials=creds)

def create_backup_folder(service):
    """Create or get backup folder in Google Drive"""
    global GOOGLE_DRIVE_FOLDER_ID

    if GOOGLE_DRIVE_FOLDER_ID:
        return GOOGLE_DRIVE_FOLDER_ID

    # Check if folder already exists
    query = f"name='VTS_Backups' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, spaces='drive').execute()
    items = results.get('files', [])

    if items:
        GOOGLE_DRIVE_FOLDER_ID = items[0]['id']
        return GOOGLE_DRIVE_FOLDER_ID

    # Create new folder
    folder_metadata = {
        'name': 'VTS_Backups',
        'mimeType': 'application/vnd.google-apps.folder'
    }

    folder = service.files().create(body=folder_metadata, fields='id').execute()
    GOOGLE_DRIVE_FOLDER_ID = folder.get('id')
    return GOOGLE_DRIVE_FOLDER_ID

def create_database_backup():
    """Create a backup of the SQLite database"""
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database file {DB_PATH} not found")

    # Create backups directory if it doesn't exist
    os.makedirs(BACKUP_DIR, exist_ok=True)

    # Generate backup filename with timestamp
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f'vts_database_backup_{timestamp}.db'
    backup_path = os.path.join(BACKUP_DIR, backup_filename)

    # Create database backup
    shutil.copy2(DB_PATH, backup_path)

    logging.info(f"Database backup created: {backup_path}")
    return backup_path

def create_images_backup():
    """Create a compressed backup of uploaded images"""
    if not os.path.exists(IMAGES_DIR):
        logging.warning(f"Images directory {IMAGES_DIR} not found")
        return None

    # Create backups directory if it doesn't exist
    os.makedirs(BACKUP_DIR, exist_ok=True)

    # Generate backup filename with timestamp
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f'uploaded_images_backup_{timestamp}.zip'
    backup_path = os.path.join(BACKUP_DIR, backup_filename)

    # Create zip archive of images
    with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(IMAGES_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, IMAGES_DIR)
                zipf.write(file_path, arcname)

    logging.info(f"Images backup created: {backup_path}")
    return backup_path

def upload_to_google_drive(file_path, service):
    """Upload a file to Google Drive"""
    folder_id = create_backup_folder(service)

    file_metadata = {
        'name': os.path.basename(file_path),
        'parents': [folder_id]
    }

    media = MediaFileUpload(file_path, resumable=True)
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()

    logging.info(f"File uploaded to Google Drive: {file_path} (ID: {file.get('id')})")
    return file.get('id')

def send_email_notification(subject, body, attachment_paths=None):
    """Send email notification with optional attachments"""
    try:
        # Get SMTP credentials from secrets manager
        smtp_config = get_smtp_config()
        smtp_server = smtp_config.get('smtp_server')
        smtp_port = smtp_config.get('smtp_port', 587)
        smtp_username = smtp_config.get('username', '')
        smtp_password = smtp_config.get('password', '')

        if not smtp_username or not smtp_password:
            logging.warning("SMTP credentials not configured. Email notification skipped.")
            return

        msg = MIMEMultipart()
        msg['From'] = smtp_username
        msg['To'] = EMAIL_RECIPIENT
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        # Attach files if provided
        if attachment_paths:
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

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        text = msg.as_string()
        server.sendmail(SMTP_USERNAME, EMAIL_RECIPIENT, text)
        server.quit()

        logging.info(f"Email notification sent to {EMAIL_RECIPIENT}")

    except Exception as e:
        logging.error(f"Failed to send email notification: {e}")

def perform_backup():
    """Main backup function"""
    try:
        logging.info("Starting automated backup...")

        # Create backups
        db_backup = create_database_backup()
        images_backup = create_images_backup()

        # Upload to Google Drive
        service = get_google_drive_service()
        db_drive_id = upload_to_google_drive(db_backup, service)

        backup_files = [db_backup]
        drive_ids = [db_drive_id]

        if images_backup:
            images_drive_id = upload_to_google_drive(images_backup, service)
            backup_files.append(images_backup)
            drive_ids.append(images_drive_id)

        # Send email notification
        subject = "VTS Database Backup Completed"
        body = f"""VTS Database and Images Backup Completed Successfully

Backup Details:
- Database backup: {os.path.basename(db_backup)}
- Images backup: {os.path.basename(images_backup) if images_backup else 'No images to backup'}
- Google Drive Folder ID: {GOOGLE_DRIVE_FOLDER_ID}
- Backup Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Files have been uploaded to Google Drive and are available for download.
"""

        send_email_notification(subject, body, backup_files)

        # Clean up local backup files (keep last 5 backups)
        cleanup_old_backups()

        logging.info("Backup completed successfully")

    except Exception as e:
        error_msg = f"Backup failed: {str(e)}"
        logging.error(error_msg)

        # Send error notification
        send_email_notification(
            "VTS Backup Failed",
            f"Automated backup encountered an error:\n\n{error_msg}\n\nPlease check the system logs."
        )

def cleanup_old_backups():
    """Keep only the last 5 backup files locally"""
    try:
        backup_files = []
        for file in os.listdir(BACKUP_DIR):
            if file.startswith(('vts_database_backup_', 'uploaded_images_backup_')):
                backup_files.append(os.path.join(BACKUP_DIR, file))

        # Sort by modification time (newest first)
        backup_files.sort(key=os.path.getmtime, reverse=True)

        # Remove older backups (keep only 5 most recent)
        for old_file in backup_files[5:]:
            os.remove(old_file)
            logging.info(f"Cleaned up old backup: {old_file}")

    except Exception as e:
        logging.warning(f"Failed to cleanup old backups: {e}")

def setup_google_drive_auth():
    """Setup Google Drive authentication (run this once manually)"""
    print("Setting up Google Drive authentication...")
    print("Checking for credentials.json...")

    if os.path.exists('credentials.json'):
        print("✅ credentials.json found!")
        print("Attempting to authenticate with Google Drive...")

        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            from google.auth.transport.requests import Request
            import pickle

            creds = None
            token_path = 'token.pickle'

            if os.path.exists(token_path):
                with open(token_path, 'rb') as token:
                    creds = pickle.load(token)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    # Load credentials from file
                    from google_auth_oauthlib.flow import InstalledAppFlow
                    SCOPES = ['https://www.googleapis.com/auth/drive.file']
                    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                    creds = flow.run_local_server(port=0)

                # Save the credentials for the next run
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)

            # Test the connection
            service = build('drive', 'v3', credentials=creds)
            print("✅ Google Drive authentication successful!")
            print("You can now run backups that will upload to Google Drive.")

        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            print("Please check your credentials.json file and try again.")
            print("Make sure:")
            print("- credentials.json is valid")
            print("- Google Drive API is enabled in your project")
            print("- OAuth consent screen is configured")

    else:
        print("❌ credentials.json not found!")
        print("You'll need to:")
        print("1. Go to Google Cloud Console (https://console.cloud.google.com/)")
        print("2. Create a project and enable Google Drive API")
        print("3. Create OAuth2 credentials (Desktop application)")
        print("4. Download credentials.json and place it in the project root")
        print("5. Run this script again to authenticate")

def main():
    """Main function to run the backup scheduler"""
    print("VTS Automated Backup System")
    print("=" * 40)
    print(f"Database: {DB_PATH}")
    print(f"Images Directory: {IMAGES_DIR}")
    print(f"Backup Interval: {BACKUP_INTERVAL_HOURS} hours")
    print(f"Email Notifications: {EMAIL_RECIPIENT}")
    print()

    # Check if required files exist
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database file {DB_PATH} not found!")
        return

    # Setup Google Drive authentication if needed
    if not os.path.exists('token.pickle'):
        print("Google Drive authentication not set up.")
        setup_google_drive_auth()
        return

    # Schedule the backup
    schedule.every(BACKUP_INTERVAL_HOURS).hours.do(perform_backup)

    print(f"Backup scheduler started. Next backup in {BACKUP_INTERVAL_HOURS} hours.")
    print("Press Ctrl+C to stop.")

    # Run initial backup
    print("Running initial backup...")
    perform_backup()

    # Keep the script running
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        print("\nBackup scheduler stopped.")

if __name__ == "__main__":
    main()