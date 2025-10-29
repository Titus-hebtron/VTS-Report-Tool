#!/usr/bin/env python3
"""
Backup Management Page for VTS Report Tool
Allows Resident Engineer (re_admin) to view and download backups
"""

import streamlit as st
import os
import pandas as pd
from datetime import datetime, timedelta
import glob
import zipfile
import io

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
                    file_size = os.path.getsize(db_file) / (1024 * 1024)  # MB
                    backup_info.append({
                        "Type": "Database",
                        "Filename": filename,
                        "Date": backup_date.date(),
                        "Time": backup_date.time(),
                        "Size (MB)": round(file_size, 2),
                        "Path": db_file
                    })
                except Exception as e:
                    st.warning(f"Could not parse database backup filename: {filename}")

            # Process image backups
            for img_file in image_backups:
                filename = os.path.basename(img_file)
                try:
                    timestamp_str = filename.replace("uploaded_images_backup_", "").replace(".zip", "")
                    backup_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    file_size = os.path.getsize(img_file) / (1024 * 1024)  # MB
                    backup_info.append({
                        "Type": "Images",
                        "Filename": filename,
                        "Date": backup_date.date(),
                        "Time": backup_date.time(),
                        "Size (MB)": round(file_size, 2),
                        "Path": img_file
                    })
                except Exception as e:
                    st.warning(f"Could not parse image backup filename: {filename}")

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
            st.error("❌ Google API client not installed. Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")

        # Check backup directory
        if os.path.exists(backup_dir):
            st.success(f"✅ Backup directory exists: {backup_dir}")
            # Show disk space info
            try:
                import shutil
                total, used, free = shutil.disk_usage(backup_dir)
                free_gb = free / (1024**3)
                st.info(f"💾 Available disk space: {free_gb:.2f} GB")
            except:
                pass
        else:
            st.warning(f"⚠️ Backup directory does not exist: {backup_dir}")
            if st.button("Create Backup Directory"):
                os.makedirs(backup_dir, exist_ok=True)
                st.success("✅ Backup directory created!")
                st.rerun()

        # Manual backup trigger
        st.subheader("🔧 Manual Backup")
        st.warning("⚠️ Manual backup may take several minutes and requires Google Drive authentication.")

        if st.button("🚀 Run Manual Backup Now", type="primary"):
            with st.spinner("Running backup... This may take a few minutes."):
                try:
                    import subprocess
                    result = subprocess.run([
                        "python", "backup_script.py"
                    ], capture_output=True, text=True, timeout=600)  # 10 minute timeout

                    if result.returncode == 0:
                        st.success("✅ Manual backup completed successfully!")
                        st.info("Check your email (hebtron25@gmail.com) for backup confirmation.")
                        st.rerun()  # Refresh to show new backups
                    else:
                        st.error("❌ Manual backup failed!")
                        with st.expander("View Error Details"):
                            st.code(result.stderr, language="text")

                except subprocess.TimeoutExpired:
                    st.error("❌ Backup timed out after 10 minutes")
                except Exception as e:
                    st.error(f"❌ Backup failed: {e}")

        # Backup schedule info
        st.subheader("⏰ Backup Schedule")
        st.info("""
        **Automated Backup Schedule:**
        - Runs every 21 hours automatically
        - Requires backup_scheduler.py to be running
        - Sends email notifications to hebtron25@gmail.com
        - Stores backups locally and uploads to Google Drive

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