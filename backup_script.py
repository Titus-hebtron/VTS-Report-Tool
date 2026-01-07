#!/usr/bin/env python3
"""
Automated Database and Image Backup to Google Drive
Backs up SQLite database and uploaded images every 21 hours
Sends email notifications to hebtron25@gmail.com

PRODUCTION READY:
- Service Account authentication for Render
- OAuth fallback for local development
- Secrets manager integration
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
import json

# Google Drive API imports
try:
    from google.oauth2.credentials import Credentials
    from google.oauth2.service_account import Credentials as ServiceAccountCredentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.auth.transport.requests import Request
    import pickle
    GOOGLE_API_AVAILABLE = True
except ImportError:
    print("Google API libraries not installed. Install with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    GOOGLE_API_AVAILABLE = False

# Configuration
DB_PATH = 'vts_database.db'
IMAGES_DIR = 'uploaded_accident_images'
BACKUP_DIR = 'backups'
GOOGLE_DRIVE_FOLDER_ID = None  # Will be set after folder creation
EMAIL_RECIPIENT = 'hebtron25@gmail.com'
BACKUP_INTERVAL_HOURS = 21

# Google Drive API scopes - FULL DRIVE ACCESS for Service Account
SCOPES = ['https://www.googleapis.com/auth/drive']

# Setup logging
logging.basicConfig(
    filename='backup.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_smtp_config():
    """Fetch SMTP credentials from secrets manager or environment."""
    try:
        from secrets_utils import get_smtp_credentials
        creds = get_smtp_credentials()
        if creds:
            return creds
    except Exception as e:
        logging.warning(f"Could not load SMTP credentials from secrets_utils: {e}")
    
    # Fallback to environment variables
    return {
        'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
        'smtp_port': int(os.getenv('SMTP_PORT', '587')),
        'username': os.getenv('SMTP_USERNAME', ''),
        'password': os.getenv('SMTP_PASSWORD', '')
    }

def get_google_drive_service():
    """
    Authenticate and return Google Drive service.
    
    PRODUCTION (Render/Cloud): Uses Service Account via:
      - GOOGLE_APPLICATION_CREDENTIALS (file path - Render Secret Files)
      - GOOGLE_CREDENTIALS_JSON (inline JSON string)
    LOCAL DEVELOPMENT: Uses OAuth with token.pickle file
    """
    if not GOOGLE_API_AVAILABLE:
        raise Exception("Google API libraries not installed")
    
    creds = None
    
    # ✅ PRIORITY 1: Service Account (Production - Render)
    try:
        from secrets_utils import get_google_credentials_json
        credentials_json = get_google_credentials_json()
        
        if credentials_json and isinstance(credentials_json, dict):
            # Check if it's a service account key
            if credentials_json.get('type') == 'service_account':
                logging.info("Using Service Account authentication")
                creds = ServiceAccountCredentials.from_service_account_info(
                    credentials_json,
                    scopes=SCOPES
                )
                logging.info("✅ Service Account authentication successful")
                return build('drive', 'v3', credentials=creds)
    except Exception as e:
        logging.warning(f"Service Account authentication failed: {e}")
    
    # ✅ PRIORITY 2: OAuth (Local Development)
    token_path = 'token.pickle'
    
    if os.path.exists(token_path):
        try:
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
            logging.info("Loaded OAuth credentials from token.pickle")
        except Exception as e:
            logging.warning(f"Could not load token.pickle: {e}")
            creds = None
    
    # Refresh or authenticate
    if creds and creds.valid:
        logging.info("✅ OAuth credentials are valid")
        return build('drive', 'v3', credentials=creds)
    
    if creds and creds.expired and hasattr(creds, 'refresh_token') and creds.refresh_token:
        try:
            logging.info("Refreshing expired OAuth token...")
            creds.refresh(Request())
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
            logging.info("✅ OAuth token refreshed")
            return build('drive', 'v3', credentials=creds)
        except Exception as e:
            logging.error(f"Failed to refresh OAuth token: {e}")
    
    # Try to get credentials and perform OAuth flow (local development only)
    try:
        from secrets_utils import get_google_credentials_json
        from google_auth_oauthlib.flow import InstalledAppFlow
        
        credentials_json = get_google_credentials_json()
        
        if credentials_json and isinstance(credentials_json, dict):
            # OAuth client configuration
            if 'installed' in credentials_json or 'web' in credentials_json:
                logging.info("Attempting OAuth flow (requires browser)...")
                flow = InstalledAppFlow.from_client_config(credentials_json, SCOPES)
                creds = flow.run_local_server(port=0)
                
                # Save credentials
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
                
                logging.info("✅ OAuth authentication successful")
                return build('drive', 'v3', credentials=creds)
    except Exception as e:
        logging.error(f"OAuth flow failed: {e}")
    
    # If we get here, authentication failed
    raise Exception(
        "Google Drive authentication failed. "
        "For Render: Set GOOGLE_CREDENTIALS_JSON with Service Account key. "
        "For local: Run backup_management.py to authenticate via browser."
    )

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
        logging.info(f"Found existing backup folder: {GOOGLE_DRIVE_FOLDER_ID}")
        return GOOGLE_DRIVE_FOLDER_ID

    # Create new folder
    folder_metadata = {
        'name': 'VTS_Backups',
        'mimeType': 'application/vnd.google-apps.folder'
    }

    folder = service.files().create(body=folder_metadata, fields='id').execute()
    GOOGLE_DRIVE_FOLDER_ID = folder.get('id')
    logging.info(f"Created new backup folder: {GOOGLE_DRIVE_FOLDER_ID}")
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
        server.sendmail(smtp_username, EMAIL_RECIPIENT, text)
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
    """Setup Google Drive authentication (run this once manually for local dev)"""
    print("Setting up Google Drive authentication...")
    print("=" * 50)
    
    # Check for Service Account (Production)
    try:
        from secrets_utils import get_google_credentials_json
        creds_json = get_google_credentials_json()
        
        if creds_json and creds_json.get('type') == 'service_account':
            print("✅ Service Account detected!")
            print(f"   Service Account Email: {creds_json.get('client_email')}")
            print("\n🔔 IMPORTANT: Share your Google Drive 'VTS_Backups' folder with:")
            print(f"   {creds_json.get('client_email')}")
            print("   (Give Editor access)")
            
            # Test authentication
            try:
                service = get_google_drive_service()
                print("\n✅ Service Account authentication successful!")
                print("   You can now run backups that will upload to Google Drive.")
                return
            except Exception as e:
                print(f"\n❌ Service Account test failed: {e}")
                return
    except Exception as e:
        print(f"⚠️  Could not check Service Account: {e}")
    
    # OAuth setup (Local Development)
    print("\n📋 For LOCAL DEVELOPMENT:")
    print("1. Get credentials.json from Google Cloud Console")
    print("2. Place it in project root")
    print("3. Run backup to trigger OAuth browser authentication")
    
    if os.path.exists('credentials.json'):
        print("\n✅ credentials.json found!")
        print("Attempting OAuth authentication...")

        try:
            service = get_google_drive_service()
            print("✅ Google Drive authentication successful!")
            print("You can now run backups that will upload to Google Drive.")

        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            print("\nPlease check:")
            print("- credentials.json is valid")
            print("- Google Drive API is enabled")
            print("- OAuth consent screen is configured")

    else:
        print("\n❌ credentials.json not found!")
        print("See GOOGLE_DRIVE_AUTH_SETUP.md for setup instructions")

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
        print(f"WARNING: Database file {DB_PATH} not found!")
        print("Will attempt backup when database is available.")

    # Check Google Drive authentication
    try:
        service = get_google_drive_service()
        print("✅ Google Drive authenticated")
    except Exception as e:
        print(f"⚠️  Google Drive authentication not configured: {e}")
        print("Run with --setup flag to configure authentication")
        return

    # Schedule the backup
    schedule.every(BACKUP_INTERVAL_HOURS).hours.do(perform_backup)

    print(f"\n✅ Backup scheduler started")
    print(f"⏰ Next backup in {BACKUP_INTERVAL_HOURS} hours")
    print("Press Ctrl+C to stop.")

    # Run initial backup
    print("\n🚀 Running initial backup...")
    perform_backup()

    # Keep the script running
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        print("\n\nBackup scheduler stopped.")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--setup':
        setup_google_drive_auth()
    else:
        main()