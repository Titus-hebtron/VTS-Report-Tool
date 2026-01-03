#!/usr/bin/env python3
"""
Backup Management Page for VTS Report Tool
Allows Resident Engineer (re_admin) to view and download backups
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import glob
import zipfile
import io
import os

def backup_management_page():
    """Backup management page for resident engineer"""
    st.header("💾 Backup Management")

    # Check if user has permission (only re_admin)
    user_role = st.session_state.get("role", "")
    if user_role != "re_admin":
        st.error("❌ Access denied. Only Resident Engineer can access backup management.")
        return

    st.info("🔐 **Resident Engineer Access Only** - Manage database and image backups")

    # Create tabs for different backup operations
    tab1, tab2, tab3 = st.tabs(["📊 View Backups", "📥 Download Backups", "⚙️ Backup Settings"])

    with tab1:
        st.subheader("📊 Available Backups")

        # Check for backup files
        backup_dir = "backups"
        if not os.path.exists(backup_dir):
            st.warning("No backup directory found. Backups will be created automatically.")
        else:
            # Get all backup files
            db_backups = glob.glob(os.path.join(backup_dir, "vts_database_backup_*.db"))
            image_backups = glob.glob(os.path.join(backup_dir, "uploaded_images_backup_*.zip"))

            # Create backup info list
            backup_info = []

            # Process database backups
            for db_file in db_backups:
                filename = os.path.basename(db_file)
                # Extract timestamp from filename
                try:
                    timestamp_str = filename.replace("vts_database_backup_", "").replace(".db", "")
                    backup_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    if os.path.exists(db_file):
                        file_size = os.path.getsize(db_file) / (1024 * 1024)  # MB
                    else:
                        file_size = 0
                    backup_info.append({
                        "Type": "Database",
                        "Filename": filename,
                        "Date": backup_date.date(),
                        "Time": backup_date.time(),
                        "Size (MB)": round(file_size, 2),
                        "Path": db_file
                    })
                except ValueError as ve:
                    st.warning(f"Could not parse database backup filename: {filename}")
                except Exception as e:
                    st.error(f"Error processing backup file {filename}: {str(e)}")

            # Process image backups
            for img_file in image_backups:
                filename = os.path.basename(img_file)
                try:
                    timestamp_str = filename.replace("uploaded_images_backup_", "").replace(".zip", "")
                    backup_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    if os.path.exists(img_file):
                        file_size = os.path.getsize(img_file) / (1024 * 1024)  # MB
                    else:
                        file_size = 0
                    backup_info.append({
                        "Type": "Images",
                        "Filename": filename,
                        "Date": backup_date.date(),
                        "Time": backup_date.time(),
                        "Size (MB)": round(file_size, 2),
                        "Path": img_file
                    })
                except ValueError as ve:
                    st.warning(f"Could not parse image backup filename: {filename}")
                except Exception as e:
                    st.error(f"Error processing backup file {filename}: {str(e)}")

            if backup_info:
                # Sort by date (newest first)
                backup_info.sort(key=lambda x: (x["Date"], x["Time"]), reverse=True)

                # Display as dataframe
                df = pd.DataFrame(backup_info)
                st.dataframe(df[["Type", "Filename", "Date", "Time", "Size (MB)"]], use_container_width=True)

                # Show summary stats
                total_backups = len(backup_info)
                db_count = sum(1 for b in backup_info if b["Type"] == "Database")
                img_count = sum(1 for b in backup_info if b["Type"] == "Images")
                total_size = sum(b["Size (MB)"] for b in backup_info)

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Backups", total_backups)
                with col2:
                    st.metric("Database", db_count)
                with col3:
                    st.metric("Images", img_count)
                with col4:
                    st.metric("Total Size", f"{total_size:.1f} MB")
            else:
                st.info("No backup files found in the backups directory.")

    with tab2:
        st.subheader("📥 Download Backups")

        if not os.path.exists(backup_dir):
            st.warning("No backup directory found.")
        else:
            # Get backup files
            db_backups = sorted(glob.glob(os.path.join(backup_dir, "vts_database_backup_*.db")), reverse=True)
            image_backups = sorted(glob.glob(os.path.join(backup_dir, "uploaded_images_backup_*.zip")), reverse=True)

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("🗄️ Database Backups")
                if db_backups:
                    selected_db = st.selectbox(
                        "Select database backup to download:",
                        [os.path.basename(f) for f in db_backups],
                        key="db_backup_select"
                    )

                    if selected_db:
                        db_file_path = os.path.join(backup_dir, selected_db)
                        with open(db_file_path, "rb") as f:
                            db_data = f.read()

                        st.download_button(
                            label=f"📥 Download {selected_db}",
                            data=db_data,
                            file_name=selected_db,
                            mime="application/octet-stream",
                            key="db_download"
                        )

                        # Show file info
                        file_size = len(db_data) / (1024 * 1024)
                        st.info(f"File size: {file_size:.2f} MB")
                else:
                    st.info("No database backups available.")

            with col2:
                st.subheader("🖼️ Image Backups")
                if image_backups:
                    selected_img = st.selectbox(
                        "Select image backup to download:",
                        [os.path.basename(f) for f in image_backups],
                        key="img_backup_select"
                    )

                    if selected_img:
                        img_file_path = os.path.join(backup_dir, selected_img)
                        with open(img_file_path, "rb") as f:
                            img_data = f.read()

                        st.download_button(
                            label=f"📥 Download {selected_img}",
                            data=img_data,
                            file_name=selected_img,
                            mime="application/zip",
                            key="img_download"
                        )

                        # Show file info
                        file_size = len(img_data) / (1024 * 1024)
                        st.info(f"File size: {file_size:.2f} MB")
                else:
                    st.info("No image backups available.")

            # Option to download all latest backups as a bundle
            st.subheader("📦 Download Latest Bundle")
            if db_backups and image_backups:
                if st.button("Create & Download Backup Bundle"):
                    with st.spinner("Creating backup bundle..."):
                        # Get latest files
                        latest_db = db_backups[0]
                        latest_img = image_backups[0]

                        # Create in-memory ZIP
                        zip_buffer = io.BytesIO()
                        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                            # Add database backup
                            zip_file.write(latest_db, os.path.basename(latest_db))
                            # Add image backup
                            zip_file.write(latest_img, os.path.basename(latest_img))

                        zip_buffer.seek(0)
                        zip_data = zip_buffer.getvalue()

                        st.download_button(
                            label="📦 Download Backup Bundle",
                            data=zip_data,
                            file_name=f"vts_backup_bundle_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                            mime="application/zip",
                            key="bundle_download"
                        )

                        bundle_size = len(zip_data) / (1024 * 1024)
                        st.success(f"✅ Backup bundle created! Size: {bundle_size:.2f} MB")
            else:
                st.info("Need both database and image backups to create a bundle.")

    with tab3:
        st.subheader("⚙️ Backup Settings & Status")

        # Backup status
        st.subheader("📊 Backup Status")

        # Check if backup script exists
        if os.path.exists("backup_script.py"):
            st.success("✅ Backup script is available")
        else:
            st.error("❌ Backup script not found")

        # Check if required packages are installed
        try:
            import schedule
            st.success("✅ Schedule library is installed")
        except ImportError:
            st.error("❌ Schedule library not installed. Run: pip install schedule")

        try:
            from google.oauth2.credentials import Credentials
            st.success("✅ Google API client is installed")
        except ImportError:
            st.warning("⚠️ Google API client not installed. Google Drive features will be disabled.")
            st.info("To enable Google Drive backups, run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")

        # Check backup directory
        if os.path.exists(backup_dir):
            st.success(f"✅ Backup directory exists: {backup_dir}")
            # Show disk space info
            try:
                import shutil
                total, used, free = shutil.disk_usage(backup_dir)
                free_gb = free / (1024**3)
                st.info(f"💾 Available disk space: {free_gb:.2f} GB")
            except Exception as e:
                st.warning(f"Could not check disk space: {e}")
        else:
            st.warning(f"⚠️ Backup directory does not exist: {backup_dir}")
            if st.button("Create Backup Directory"):
                os.makedirs(backup_dir, exist_ok=True)
                st.success("✅ Backup directory created!")
                st.rerun()

        # Manual backup trigger
        st.subheader("🔧 Manual Backup")
        st.warning("⚠️ Manual backup may take several minutes and requires Google Drive authentication.")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🚀 Run Local Backup Only", type="secondary"):
                with st.spinner("Running local backup... This may take a few minutes."):
                    try:
                        # Import backup functions directly to avoid subprocess issues
                        import sqlite3
                        import shutil
                        import datetime as dt
                        import zipfile
                        import io

                        # Simple backup logic for manual trigger
                        DB_PATH = 'vts_database.db'
                        IMAGES_DIR = 'uploaded_accident_images'
                        BACKUP_DIR = 'backups'

                        # Create backups directory
                        os.makedirs(BACKUP_DIR, exist_ok=True)

                        # Generate backup filename
                        timestamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S')

                        # Database backup
                        if os.path.exists(DB_PATH):
                            db_backup = f'vts_database_backup_{timestamp}.db'
                            db_path = os.path.join(BACKUP_DIR, db_backup)
                            shutil.copy2(DB_PATH, db_path)
                            st.info(f"✅ Database backup created: {db_backup}")
                        else:
                            st.warning("Database file not found")

                        # Images backup
                        if os.path.exists(IMAGES_DIR):
                            img_backup = f'uploaded_images_backup_{timestamp}.zip'
                            img_path = os.path.join(BACKUP_DIR, img_backup)
                            with zipfile.ZipFile(img_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                                for root, dirs, files in os.walk(IMAGES_DIR):
                                    for file in files:
                                        file_path = os.path.join(root, file)
                                        arcname = os.path.relpath(file_path, IMAGES_DIR)
                                        zipf.write(file_path, arcname)
                            st.info(f"✅ Images backup created: {img_backup}")
                        else:
                            st.warning("Images directory not found")

                        st.success("✅ Local backup completed successfully!")
                        st.info("Backups are stored locally. For Google Drive upload and email notifications, use the full backup option.")
                        # Removed st.rerun() to prevent continuous rerunning

                    except Exception as e:
                        st.error(f"❌ Backup failed: {e}")
                        import traceback
                        with st.expander("View Error Details"):
                            st.code(traceback.format_exc(), language="text")

        with col2:
            # Check if enough time has passed since last manual Google Drive backup
            last_backup_file = "last_manual_gdrive_backup.txt"
            can_backup = True
            if os.path.exists(last_backup_file):
                try:
                    with open(last_backup_file, 'r') as f:
                        last_backup_time = datetime.datetime.fromisoformat(f.read().strip())
                    time_since_last = datetime.datetime.now() - last_backup_time
                    if time_since_last < datetime.timedelta(hours=3):
                        can_backup = False
                        remaining_time = datetime.timedelta(hours=3) - time_since_last
                        hours, remainder = divmod(remaining_time.seconds, 3600)
                        minutes = remainder // 60
                        st.warning(f"⚠️ Manual Google Drive backup can only be run once every 3 hours. Next available in {hours}h {minutes}m")
                except:
                    pass

            if can_backup and st.button("☁️ Run Full Backup to Google Drive", type="primary"):
                with st.spinner("Running full backup with Google Drive upload... This may take several minutes."):
                    try:
                        # Import backup functions from backup_script.py
                        import sqlite3
                        import shutil
                        import datetime as dt
                        import zipfile
                        import io
                        import smtplib
                        from email.mime.text import MIMEText
                        from email.mime.multipart import MIMEMultipart

                        # Google Drive imports - check if available
                        try:
                            from google.oauth2.credentials import Credentials
                            from googleapiclient.discovery import build
                            from googleapiclient.http import MediaFileUpload
                            from google.auth.transport.requests import Request
                            import pickle
                        except ImportError:
                            st.error("❌ Google API client not installed. Cannot perform Google Drive backup.")
                            raise ImportError("Google API client not available")

                        # Configuration
                        DB_PATH = 'vts_database.db'
                        IMAGES_DIR = 'uploaded_accident_images'
                        BACKUP_DIR = 'backups'
                        EMAIL_RECIPIENT = 'hebtron25@gmail.com'
                        SMTP_SERVER = 'smtp.gmail.com'
                        SMTP_PORT = 587
                        SMTP_USERNAME = 'your-email@gmail.com'  # Replace with your email
                        SMTP_PASSWORD = 'your-app-password'  # Replace with app password

                        # Create backups directory
                        os.makedirs(BACKUP_DIR, exist_ok=True)

                        # Generate backup filename
                        timestamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S')

                        # Database backup
                        if os.path.exists(DB_PATH):
                            db_backup = f'vts_database_backup_{timestamp}.db'
                            db_path = os.path.join(BACKUP_DIR, db_backup)
                            shutil.copy2(DB_PATH, db_path)
                            st.info(f"✅ Database backup created: {db_backup}")
                        else:
                            st.error("Database file not found")
                            raise FileNotFoundError("Database file not found")

                        # Images backup
                        images_backup = None
                        if os.path.exists(IMAGES_DIR):
                            img_backup = f'uploaded_images_backup_{timestamp}.zip'
                            img_path = os.path.join(BACKUP_DIR, img_backup)
                            with zipfile.ZipFile(img_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                                for root, dirs, files in os.walk(IMAGES_DIR):
                                    for file in files:
                                        file_path = os.path.join(root, file)
                                        arcname = os.path.relpath(file_path, IMAGES_DIR)
                                        zipf.write(file_path, arcname)
                            st.info(f"✅ Images backup created: {img_backup}")
                            images_backup = img_path

                        # Google Drive authentication
                        creds = None
                        token_path = 'token.pickle'

                        if os.path.exists(token_path):
                            with open(token_path, 'rb') as token:
                                creds = pickle.load(token)

                        if not creds or not creds.valid:
                            if creds and creds.expired and creds.refresh_token:
                                creds.refresh(Request())
                            else:
                                st.warning("⚠️ Google Drive authentication not configured")
                                st.info("""
**To enable Google Drive backups:**

1. Download `credentials.json` from Google Cloud Console:
   - Go to https://console.cloud.google.com/
   - Create a project or select existing one
   - Enable Google Drive API
   - Create OAuth 2.0 credentials (Desktop app type)
   - Download credentials and save as `credentials.json` in this directory

2. Run the authentication script (one time only):
   ```
   python backup_script.py --auth
   ```

3. Local backups are still working - use "Run Local Backup Only" button above

For now, your backups are saved locally in the `backups/` folder.
                                """)
                                raise Exception("Google Drive not authenticated. See instructions above.")

                        service = build('drive', 'v3', credentials=creds)

                        # Create or get backup folder
                        query = "name='VTS_Backups' and mimeType='application/vnd.google-apps.folder' and trashed=false"
                        results = service.files().list(q=query, spaces='drive').execute()
                        items = results.get('files', [])

                        if items:
                            folder_id = items[0]['id']
                        else:
                            # Create new folder
                            folder_metadata = {
                                'name': 'VTS_Backups',
                                'mimeType': 'application/vnd.google-apps.folder'
                            }
                            folder = service.files().create(body=folder_metadata, fields='id').execute()
                            folder_id = folder.get('id')

                        # Upload database backup
                        file_metadata = {
                            'name': os.path.basename(db_path),
                            'parents': [folder_id]
                        }
                        media = MediaFileUpload(db_path, resumable=True)
                        file = service.files().create(
                            body=file_metadata,
                            media_body=media,
                            fields='id'
                        ).execute()
                        st.info(f"✅ Database uploaded to Google Drive (ID: {file.get('id')})")

                        backup_files = [db_path]
                        drive_ids = [file.get('id')]

                        # Upload images backup if exists
                        if images_backup:
                            file_metadata = {
                                'name': os.path.basename(images_backup),
                                'parents': [folder_id]
                            }
                            media = MediaFileUpload(images_backup, resumable=True)
                            file = service.files().create(
                                body=file_metadata,
                                media_body=media,
                                fields='id'
                            ).execute()
                            st.info(f"✅ Images uploaded to Google Drive (ID: {file.get('id')})")
                            backup_files.append(images_backup)
                            drive_ids.append(file.get('id'))

                        # Send email notification
                        try:
                            msg = MIMEMultipart()
                            msg['From'] = SMTP_USERNAME
                            msg['To'] = EMAIL_RECIPIENT
                            msg['Subject'] = "VTS Manual Database Backup Completed"

                            body = f"""VTS Database and Images Backup Completed Successfully

Backup Details:
- Database backup: {os.path.basename(db_path)}
- Images backup: {os.path.basename(images_backup) if images_backup else 'No images to backup'}
- Google Drive Folder ID: {folder_id}
- Backup Time: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Files have been uploaded to Google Drive and are available for download.
"""
                            msg.attach(MIMEText(body, 'plain'))

                            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
                            server.starttls()
                            server.login(SMTP_USERNAME, SMTP_PASSWORD)
                            text = msg.as_string()
                            server.sendmail(SMTP_USERNAME, EMAIL_RECIPIENT, text)
                            server.quit()

                            st.info(f"✅ Email notification sent to {EMAIL_RECIPIENT}")

                        except Exception as e:
                            st.warning(f"Email notification failed: {e}")

                        # Record the backup time
                        with open("last_manual_gdrive_backup.txt", 'w') as f:
                            f.write(dt.datetime.now().isoformat())

                        st.success("✅ Full backup to Google Drive completed successfully!")
                        st.info("Backups are stored locally and uploaded to Google Drive with email notifications.")
                        # Removed st.rerun() to prevent continuous rerunning

                    except Exception as e:
                        st.error(f"❌ Full backup failed: {e}")
                        import traceback
                        with st.expander("View Error Details"):
                            st.code(traceback.format_exc(), language="text")

        # Backup schedule info
        st.subheader("⏰ Backup Schedule")
        st.info("""
        **Automated Backup Schedule:**
        - Runs every 5 hours automatically
        - Requires backup_scheduler.py to be running
        - Sends email notifications to hebtron25@gmail.com
        - Stores backups locally and uploads to Google Drive

        **Manual Google Drive Backup:**
        - Can only be run once every 3 hours
        - Includes full Google Drive upload and email notifications

        **To start automated backups:**
        ```bash
        python backup_scheduler.py
        ```

        **To run as Windows service:**
        Use NSSM or Windows Task Scheduler to run backup_scheduler.py at startup.
        """)

        # Google Drive status
        st.subheader("☁️ Google Drive Status")
        if os.path.exists("token.pickle"):
            st.success("✅ Google Drive authentication configured")
        else:
            st.warning("⚠️ Google Drive not authenticated. Run backup_script.py once to authenticate.")

        # Email configuration
        st.subheader("📧 Email Configuration")
        st.info("Email notifications are sent to: **hebtron25@gmail.com**")
        st.info("Configure SMTP settings in backup_script.py if needed.")

if __name__ == "__main__":
    # For testing standalone
    st.set_page_config(page_title="Backup Management", page_icon="💾")
    backup_management_page()