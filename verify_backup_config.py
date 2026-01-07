#!/usr/bin/env python3
"""
Backup Configuration Verification Script

Run this script to verify your backup system configuration:
- Google Drive authentication
- SMTP credentials
- Service Account setup
- File permissions

Usage:
    python verify_backup_config.py
"""

import os
import sys
import json

def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def print_status(check_name, status, message=""):
    """Print check status"""
    icon = "✅" if status else "❌"
    print(f"{icon} {check_name}")
    if message:
        print(f"   → {message}")

def check_google_credentials():
    """Check Google Drive credentials configuration"""
    print_header("Google Drive Authentication")
    
    # Check for GOOGLE_APPLICATION_CREDENTIALS (Render Secret Files)
    app_creds = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if app_creds:
        print_status("GOOGLE_APPLICATION_CREDENTIALS", True, f"Set to: {app_creds}")
        
        # Check if file exists
        if os.path.exists(app_creds):
            print_status("Credentials file exists", True, f"File found at {app_creds}")
            try:
                with open(app_creds, 'r') as f:
                    creds = json.load(f)
                    if creds.get('type') == 'service_account':
                        print_status("Valid Service Account JSON", True)
                        print(f"   Service Account Email: {creds.get('client_email', 'N/A')}")
                        print(f"   Project ID: {creds.get('project_id', 'N/A')}")
                        return True, creds.get('client_email')
                    else:
                        print_status("Valid Service Account JSON", False, "Not a service account key")
            except json.JSONDecodeError:
                print_status("Valid JSON", False, "File is not valid JSON")
            except Exception as e:
                print_status("Read file", False, str(e))
        else:
            print_status("Credentials file exists", False, f"File not found: {app_creds}")
    else:
        print_status("GOOGLE_APPLICATION_CREDENTIALS", False, "Not set")
    
    # Check for GOOGLE_CREDENTIALS_JSON (inline)
    creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
    if creds_json:
        print_status("GOOGLE_CREDENTIALS_JSON", True, "Environment variable set")
        try:
            creds = json.loads(creds_json)
            if creds.get('type') == 'service_account':
                print_status("Valid Service Account JSON", True)
                print(f"   Service Account Email: {creds.get('client_email', 'N/A')}")
                return True, creds.get('client_email')
        except:
            print_status("Valid JSON", False, "Could not parse JSON")
    else:
        print_status("GOOGLE_CREDENTIALS_JSON", False, "Not set")
    
    # Check for local credentials.json
    if os.path.exists('credentials.json'):
        print_status("Local credentials.json", True, "Found (for development)")
        try:
            with open('credentials.json', 'r') as f:
                creds = json.load(f)
                if 'installed' in creds or 'web' in creds:
                    print_status("OAuth credentials", True, "For local development")
                elif creds.get('type') == 'service_account':
                    print_status("Service Account", True, creds.get('client_email'))
                    return True, creds.get('client_email')
        except:
            pass
    
    # Check for token.pickle
    if os.path.exists('token.pickle'):
        print_status("OAuth token.pickle", True, "Found (authenticated locally)")
    
    return False, None

def check_smtp_credentials():
    """Check SMTP credentials configuration"""
    print_header("SMTP Email Configuration")
    
    all_set = True
    
    # Check individual env vars
    smtp_server = os.getenv('SMTP_SERVER')
    smtp_port = os.getenv('SMTP_PORT')
    smtp_username = os.getenv('SMTP_USERNAME')
    smtp_password = os.getenv('SMTP_PASSWORD')
    
    print_status("SMTP_SERVER", bool(smtp_server), smtp_server or "Not set")
    print_status("SMTP_PORT", bool(smtp_port), smtp_port or "Not set")
    print_status("SMTP_USERNAME", bool(smtp_username), smtp_username or "Not set")
    print_status("SMTP_PASSWORD", bool(smtp_password), "***" if smtp_password else "Not set")
    
    if smtp_server and smtp_port and smtp_username and smtp_password:
        print("\n✅ All SMTP credentials configured!")
        return True
    
    # Check for JSON env var
    smtp_json = os.getenv('SMTP_CREDENTIALS_JSON')
    if smtp_json:
        print_status("SMTP_CREDENTIALS_JSON", True, "Set")
        try:
            creds = json.loads(smtp_json)
            if all(k in creds for k in ['smtp_server', 'smtp_port', 'username', 'password']):
                print_status("Valid SMTP JSON", True)
                return True
        except:
            print_status("Valid SMTP JSON", False)
    
    # Check for local .smtp_config
    if os.path.exists('.smtp_config'):
        print_status("Local .smtp_config", True, "Found (for development)")
        try:
            with open('.smtp_config', 'r') as f:
                creds = json.load(f)
                if all(k in creds for k in ['smtp_server', 'smtp_port', 'username', 'password']):
                    print_status("Valid SMTP config", True)
                    return True
        except:
            pass
    
    if not all([smtp_server, smtp_port, smtp_username, smtp_password]):
        print("\n⚠️  SMTP not fully configured. Email notifications will be skipped.")
    
    return False

def check_backup_directories():
    """Check backup-related directories"""
    print_header("Backup Directories & Files")
    
    # Check database
    if os.path.exists('vts_database.db'):
        print_status("Database file", True, "vts_database.db found")
    else:
        print_status("Database file", False, "vts_database.db not found (may be using PostgreSQL)")
    
    # Check images directory
    if os.path.exists('uploaded_accident_images'):
        image_count = len([f for f in os.listdir('uploaded_accident_images') if os.path.isfile(os.path.join('uploaded_accident_images', f))])
        print_status("Images directory", True, f"{image_count} files")
    else:
        print_status("Images directory", False, "uploaded_accident_images not found")
    
    # Check backups directory
    if os.path.exists('backups'):
        db_backups = len([f for f in os.listdir('backups') if f.startswith('vts_database_backup_')])
        img_backups = len([f for f in os.listdir('backups') if f.startswith('uploaded_images_backup_')])
        print_status("Backups directory", True, f"{db_backups} DB backups, {img_backups} image backups")
    else:
        print_status("Backups directory", False, "Will be created automatically")

def check_dependencies():
    """Check if required Python packages are installed"""
    print_header("Required Dependencies")
    
    packages = {
        'google-api-python-client': 'googleapiclient',
        'google-auth': 'google.auth',
        'schedule': 'schedule',
        'streamlit': 'streamlit'
    }
    
    for package_name, import_name in packages.items():
        try:
            __import__(import_name)
            print_status(package_name, True, "Installed")
        except ImportError:
            print_status(package_name, False, f"Not installed. Run: pip install {package_name}")

def test_google_auth():
    """Test Google Drive authentication"""
    print_header("Testing Google Drive Authentication")
    
    try:
        from secrets_utils import get_google_credentials_json
        from google.oauth2.service_account import Credentials as ServiceAccountCredentials
        from googleapiclient.discovery import build
        
        creds_json = get_google_credentials_json()
        
        if not creds_json:
            print_status("Load credentials", False, "No credentials found")
            return False
        
        print_status("Load credentials", True)
        
        if creds_json.get('type') == 'service_account':
            creds = ServiceAccountCredentials.from_service_account_info(
                creds_json,
                scopes=['https://www.googleapis.com/auth/drive']
            )
            print_status("Authenticate Service Account", True)
            
            # Try to build service
            service = build('drive', 'v3', credentials=creds)
            print_status("Build Drive service", True)
            
            # Try to list files (just to test connection)
            try:
                results = service.files().list(pageSize=1).execute()
                print_status("Connect to Google Drive", True)
                print("\n✅ Google Drive authentication working!")
                return True
            except Exception as e:
                print_status("Connect to Google Drive", False, str(e))
                print("\n⚠️  Authentication works, but couldn't access Drive.")
                print("   Make sure the service account has access to your Drive folders.")
                return False
        else:
            print("⚠️  Not a Service Account. OAuth flow needed (use Streamlit UI).")
            return False
            
    except Exception as e:
        print_status("Test authentication", False, str(e))
        return False

def main():
    """Main verification function"""
    print("\n" + "=" * 60)
    print("  VTS BACKUP CONFIGURATION VERIFICATION")
    print("=" * 60)
    
    # Run all checks
    google_ok, service_account_email = check_google_credentials()
    smtp_ok = check_smtp_credentials()
    check_backup_directories()
    check_dependencies()
    
    # Test authentication if credentials found
    if google_ok:
        test_ok = test_google_auth()
    else:
        test_ok = False
    
    # Final summary
    print_header("Summary")
    
    if google_ok:
        print("✅ Google Drive credentials configured")
        if service_account_email:
            print(f"\n📧 Service Account Email:")
            print(f"   {service_account_email}")
            print("\n🔔 IMPORTANT:")
            print("   Share your Google Drive 'VTS_Backups' folder with this email!")
            print("   Give it Editor access.")
    else:
        print("❌ Google Drive credentials NOT configured")
        print("\n📖 See RENDER_SECRET_FILES_SETUP.md for setup instructions")
    
    if smtp_ok:
        print("\n✅ SMTP credentials configured")
    else:
        print("\n⚠️  SMTP credentials incomplete (email notifications will be skipped)")
    
    if test_ok:
        print("\n✅ Successfully connected to Google Drive!")
    elif google_ok:
        print("\n⚠️  Could not connect to Google Drive")
        print("   Check that VTS_Backups folder is shared with service account")
    
    print("\n" + "=" * 60)
    
    # Exit code
    if google_ok and test_ok:
        print("✅ ALL CHECKS PASSED - Ready to backup!")
        return 0
    elif google_ok:
        print("⚠️  PARTIAL - Credentials configured but connection failed")
        return 1
    else:
        print("❌ FAILED - Please configure credentials")
        return 2

if __name__ == "__main__":
    sys.exit(main())