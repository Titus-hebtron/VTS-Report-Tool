# vts_report_tool.py
import streamlit as st
import os
import pandas as pd
import datetime
import io
from sqlalchemy import text
from db_utils import get_sqlalchemy_engine, get_user, verify_password, get_contractor_id
from breaks_pickups_page import breaks_pickups_page
from streamlit_folium import st_folium
import folium
from streamlit_autorefresh import st_autorefresh

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="VTS REPORT TOOL",
    layout="wide",
    page_icon="Kenhalogo.png" if os.path.exists("Kenhalogo.png") else None
)

# PWA Support - Add manifest and meta tags
st.markdown("""
<link rel="manifest" href="pwa_manifest.json">
<meta name="theme-color" content="#004080">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="VTS Reports">
""", unsafe_allow_html=True)

# Logo & Title
if os.path.exists("Kenhalogo.png"):
    st.image("Kenhalogo.png", width='stretch')
st.markdown("<h1 style='text-align: center; color: #004080;'>VTS REPORT TOOL</h1>", unsafe_allow_html=True)
st.markdown("<hr style='border:2px solid #004080'>", unsafe_allow_html=True)

# ---------------- SESSION STATE ----------------
if "login_state" not in st.session_state:
    st.session_state["login_state"] = False
    st.session_state["user_name"] = None
    st.session_state["contractor"] = None
    st.session_state["role"] = None

# ---------------- LOGIN PAGE ----------------
if not st.session_state["login_state"]:
    # Layout with columns for better appearance
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("""
        <div style='text-align: center; padding: 50px;'>
            <h1 style='color: #004080;'>Welcome to VTS Report Tool 🚓📊</h1>
            <p style='font-size: 18px; color: #666;'>Your smart platform for vehicle tracking and reporting. With VTS you can:</p>
            <ul style='text-align: left; font-size: 16px; color: #666; list-style-type: none; padding-left: 20px;'>
                <li>📍 Track vehicles in real-time with live updates.</li>
                <li>📑 Generate, view, and manage patrol reports easily.</li>
                <li>🔒 Keep data secure with role-based login.</li>
                <li>📊 Boost efficiency through automated reports and analytics.</li>
                <li>🌐 Access the system anywhere, anytime.</li>
            </ul>
            <p style='font-size: 16px; color: #666;'>Login now to manage your fleet operations with efficiency, accuracy, and security.</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("### 🔑 Login")
        contractor_options = ["Wizpro", "Paschal", "RE Office", "Avators"]
        contractor = st.selectbox("Select Contractor", contractor_options)

        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            
            import bcrypt

            engine = get_sqlalchemy_engine()
            conn = engine.raw_connection()
            cur = conn.cursor()

            cur.execute("SELECT u.id, u.password_hash, u.role FROM users u JOIN contractors c ON u.contractor_id = c.id WHERE c.name = %s AND u.username = %s",
                        (contractor, username))
            user = cur.fetchone()

            cur.close()
            conn.close()

            if user and bcrypt.checkpw(password.encode('utf-8'), user[1].encode('utf-8')):
                st.session_state["login_state"] = True
                st.session_state["user_name"] = username
                role = "re_admin" if contractor == "RE Office" else user[2]
                st.session_state["role"] = role
                st.session_state["contractor"] = contractor
                st.session_state["contractor_id"] = get_contractor_id(contractor)
                st.success(f"✅ Logged in as {username} ({role})")
                st.rerun()
            else:
                st.error("❌ Invalid login credentials")

    st.markdown("""
    <div style='text-align: center; color: gray; font-size: 12px; margin-top: 50px;'>2025/2026 Hebtron Technologies</div>
    """, unsafe_allow_html=True)
    st.stop()

# ---------------- MAIN APP ----------------
st.sidebar.title(f"👋 Welcome, {st.session_state['user_name']}")
st.sidebar.write(f"**Role:** {st.session_state['role']}")

# Contractor handling
if st.session_state["role"] == "re_admin":
    st.sidebar.subheader("🔄 Switch Contractor")
    contractor = st.sidebar.selectbox("Select Contractor", ["Wizpro", "Paschal", "Avators"], key="contractor_switch")
    st.session_state["active_contractor"] = get_contractor_id(contractor)
else:
    contractor = st.session_state["contractor"]

st.sidebar.write(f"**Contractor:** {contractor}")

# Downloads
st.sidebar.subheader("📥 Downloads")

if st.sidebar.button("📱 Download Mobile App"):
    st.session_state["show_mobile_download"] = True
    st.rerun()

if st.sidebar.button("🌐 Download Web App"):
    st.session_state["show_web_download"] = True
    st.rerun()

# Logout
if st.sidebar.button("🚪 Logout"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ---- FETCH VEHICLES ----
def get_vehicles_for_contractor(contractor):
    engine = get_sqlalchemy_engine()
    query = text("""
        SELECT id, plate_number 
        FROM vehicles 
        WHERE contractor = :contractor 
        ORDER BY plate_number
    """)
    with engine.begin() as conn:
        result = conn.execute(query, {"contractor": contractor})
        return [{"id": row[0], "plate_number": row[1]} for row in result.fetchall()]

# Web App Download Section
if st.session_state.get("show_web_download", False):
    st.header("🌐 Download Web App")
    st.write("Get the complete VTS Report Tool as a downloadable web application!")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("💻 Standalone Executable")
        st.write("Download a single executable file that runs the entire web app:")
        st.info("Run `python web_app_packager.py` and choose option 1 to create the executable")
        st.code("python web_app_packager.py", language="bash")
        st.warning("Executable creation requires PyInstaller and may take several minutes")

    with col2:
        st.subheader("🐍 Python Web Package")
        st.write("Download the complete Python package:")

        # Create web app package ZIP
        import zipfile
        import io

        def create_web_zip():
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Core files
                core_files = [
                    'vts_report_tool.py', 'api.py', 'db_utils.py', 'schema.sql',
                    'web_app_packager.py', 'Kenhalogo.png', 'README.md', 'pwa_manifest.json'
                ]
                for file in core_files:
                    if os.path.exists(file):
                        zip_file.write(file)

                # Directories
                dirs_to_include = ['dejavu-fonts-ttf-2.37']
                for dir_name in dirs_to_include:
                    if os.path.exists(dir_name):
                        for root, dirs, files in os.walk(dir_name):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path)
                                zip_file.write(file_path, arcname)

                # Create requirements.txt in ZIP
                requirements_content = '''streamlit>=1.28.0
pandas>=2.0.0
psycopg2-binary>=2.9.0
bcrypt>=4.0.0
sqlalchemy>=2.0.0
folium>=0.14.0
streamlit-folium>=0.17.0
streamlit-autorefresh>=1.0.0
Pillow>=10.0.0
matplotlib>=3.7.0
seaborn>=0.12.0
fastapi>=0.104.0
uvicorn>=0.24.0
python-jose[cryptography]>=3.5.0
passlib[bcrypt]>=1.7.0
python-multipart>=0.0.6'''
                zip_file.writestr('requirements.txt', requirements_content)

                # Create run script in ZIP
                run_script_content = '''#!/usr/bin/env python3
"""
VTS Report Tool Launcher
Run this script to start the web application
"""

import subprocess
import sys
import os

def main():
    print("🚀 VTS Report Tool Web App")
    print("=" * 40)

    # Check if required packages are installed
    try:
        import streamlit
        import pandas
        import fastapi
        print("✅ Required packages are installed")
    except ImportError:
        print("❌ Installing required packages...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Packages installed successfully")

    print("\\n🌐 Starting web application...")
    print("The app will open in your default browser.")
    print("Press Ctrl+C to stop the server.\\n")

    try:
        # Start the Streamlit app
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            "vts_report_tool.py",
            "--server.port", "8501",
            "--server.address", "localhost"
        ])
    except KeyboardInterrupt:
        print("\\n\\n👋 VTS Report Tool stopped.")
    except Exception as e:
        print(f"\\n❌ Error starting app: {e}")

if __name__ == "__main__":
    main()'''
                zip_file.writestr('run_app.py', run_script_content)

                # Create README in ZIP
                readme_content = '''# VTS Report Tool - Web App Package

This is a standalone web application package for the VTS Report Tool.

## 🚀 Quick Start

### Option 1: Run with Python Script (Recommended)
```bash
python run_app.py
```

### Option 2: Manual Start
```bash
# Install dependencies
pip install -r requirements.txt

# Start the web app
streamlit run vts_report_tool.py
```

## 📋 Requirements

- Python 3.8 or higher
- Internet connection for map features
- PostgreSQL database (configure in db_utils.py)

## 🔧 Configuration

1. Set up your PostgreSQL database
2. Update database connection in `db_utils.py`
3. Run the application

## 🌐 Access

Once started, the app will be available at: http://localhost:8501

## 📱 Mobile App

For mobile access, download the mobile app source code from the web interface and build it with Flutter.

## 🆘 Support

Contact: hebtron25@gmail.com'''
                zip_file.writestr('PACKAGE_README.md', readme_content)

            zip_buffer.seek(0)
            return zip_buffer.getvalue()

        web_zip_data = create_web_zip()
        st.download_button(
            label="📦 Download Web App Package",
            data=web_zip_data,
            file_name="vts_web_app_package.zip",
            mime="application/zip"
        )

    st.subheader("🚀 Quick Start Guide")
    st.markdown("""
    ### For Python Package:
    1. Download the ZIP above
    2. Extract the files
    3. Run: `python run_app.py`
    4. Open browser to http://localhost:8501

    ### For Standalone Executable:
    1. Run: `python web_app_packager.py` (choose option 1)
    2. Find executable in `dist/` folder
    3. Double-click to run

    ### 🌟 PWA Features:
    - **Install as App**: Click browser menu → "Install VTS Report Tool"
    - **Offline Access**: Works without internet (except maps)
    - **Native App Feel**: Runs fullscreen like a mobile app
    - **Auto-Updates**: Gets latest features automatically

    ### Features Included:
    - ✅ Complete web interface
    - ✅ User authentication
    - ✅ Vehicle tracking
    - ✅ Patrol logs with maps
    - ✅ Incident reporting
    - ✅ All analysis tools
    - ✅ Mobile app download
    - ✅ **PWA capabilities** (installable, offline-ready)
    """)

    if st.button("Back to Main App"):
        st.session_state["show_web_download"] = False
        st.rerun()

    st.stop()  # Don't show the rest of the app

# Mobile App Download Section
if st.session_state.get("show_mobile_download", False):
    st.header("📱 Download Mobile App")
    st.write("Get the VTS Report Tool mobile app for Android and iOS!")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📱 Android APK")
        st.write("Download the Android APK file:")

        apk_path = "mobile_app/build/app/outputs/flutter-apk/app-release.apk"
        if os.path.exists(apk_path):
            with open(apk_path, "rb") as f:
                apk_data = f.read()
            st.download_button(
                label="📥 Download Android APK",
                data=apk_data,
                file_name="vts_report_tool.apk",
                mime="application/vnd.android.package-archive"
            )
        else:
            st.warning("APK file not found. Please build the app first.")
            st.code("cd mobile_app && flutter build apk --release", language="bash")
            if st.button("Build Android APK"):
                st.info("Building APK... This may take a few minutes.")
                # Note: In a real deployment, you would run the build command here
                st.error("Build functionality requires server-side execution. Please run the build command manually.")

    with col2:
        st.subheader("🍎 iOS App")
        st.write("iOS app requires Xcode and Apple Developer account:")
        st.info("iOS apps must be distributed through the App Store. Build and submit using:")
        st.code("flutter build ios --release", language="bash")
        st.write("Then archive in Xcode and upload to App Store Connect.")
        st.warning("Direct download not available for iOS - must go through App Store.")

    st.subheader("🚀 Complete Setup Procedure")

    # Download source code
    import zipfile
    import io

    def create_zip_download():
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add mobile_app directory contents
            for root, dirs, files in os.walk('mobile_app'):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, 'mobile_app')
                    zip_file.write(file_path, arcname)
        zip_buffer.seek(0)
        return zip_buffer.getvalue()

    zip_data = create_zip_download()
    st.download_button(
        label="📦 Download Mobile App Source Code",
        data=zip_data,
        file_name="vts_mobile_app.zip",
        mime="application/zip"
    )

    st.markdown("""
    ### 📋 Step-by-Step Procedure:

    #### 1. Deploy the API Server
    ```bash
    # On your server (Linux/Windows/Mac):
    python api.py
    # Or for production:
    uvicorn api:app --host 0.0.0.0 --port 8000
    ```

    #### 2. Configure Mobile App
    - Download the source code above
    - Extract the ZIP file
    - Open `mobile_app/lib/config.dart`
    - Change `apiBaseUrl` to your server URL:
    ```dart
    const String apiBaseUrl = 'http://your-server-ip:8000';
    // Or for HTTPS:
    const String apiBaseUrl = 'https://your-domain.com/api';
    ```

    #### 3. Build the Mobile App
    ```bash
    cd mobile_app
    flutter pub get
    flutter build apk --release  # For Android
    flutter build ios --release  # For iOS
    ```

    #### 4. Install and Use
    - **Android**: Install the APK file on your device
    - **iOS**: Archive in Xcode and distribute via TestFlight/App Store

    ### 🔗 Server Connection
    The mobile app will automatically connect to your configured server URL for:
    - User authentication
    - Vehicle data
    - Patrol logs
    - Incident reports
    """)

    st.info("📱 **APK Location**: After building, find the APK at `mobile_app/build/app/outputs/flutter-apk/app-release.apk`")
    st.info("🍎 **iOS**: Requires macOS with Xcode. Build and distribute through App Store Connect.")

    st.write("The mobile app provides:")
    st.markdown("""
    - ✅ Login with your existing credentials
    - ✅ View patrol logs for vehicles
    - ✅ Interactive map with patrol locations
    - ✅ Access to incident reports
    - ✅ Offline-capable interface
    """)

    if st.button("Back to Main App"):
        st.session_state["show_mobile_download"] = False
        st.rerun()

    st.stop()  # Don't show the rest of the app when showing download page

vehicle_list = get_vehicles_for_contractor(contractor)
if not vehicle_list:
    st.warning(f"No vehicles found for contractor {contractor}")
    patrol_vehicle_options = ["Replacement Car"]
    selected_vehicle = None
else:
    patrol_vehicle_options = [v["plate_number"] for v in vehicle_list]
    selected_vehicle = st.sidebar.selectbox("🚗 Select Vehicle", patrol_vehicle_options)

# ---- LOAD PATROL LOGS ----
if selected_vehicle:
    vehicle_id = next((v["id"] for v in vehicle_list if v["plate_number"] == selected_vehicle), None)
    if vehicle_id:
        engine = get_sqlalchemy_engine()
        logs_query = """
            SELECT timestamp, latitude, longitude, activity
            FROM patrol_logs
            WHERE vehicle_id = %(vehicle_id)s
            ORDER BY timestamp DESC
        """
        with engine.begin() as conn:
            patrol_logs = pd.read_sql(logs_query, conn, params={"vehicle_id": vehicle_id})

        if patrol_logs.empty:
            st.info(f"No patrol logs found for {selected_vehicle}")
        else:
            st.subheader(f"📋 Patrol Logs for {selected_vehicle}")
            st.dataframe(patrol_logs, width='stretch')

            st.subheader(f"🗺️ Map View for {selected_vehicle}")

            if patrol_logs.iloc[0]["latitude"] and patrol_logs.iloc[0]["longitude"]:
                start_lat = patrol_logs.iloc[0]["latitude"]
                start_lon = patrol_logs.iloc[0]["longitude"]
            else:
                start_lat, start_lon = -1.2921, 36.8219

            patrol_map = folium.Map(location=[start_lat, start_lon], zoom_start=12)

            for _, row in patrol_logs.iterrows():
                if row["latitude"] and row["longitude"]:
                    popup_text = f"""
                    <b>Time:</b> {row['timestamp']}<br>
                    <b>Activity:</b> {row['activity']}
                    """
                    folium.Marker(
                        [row["latitude"], row["longitude"]],
                        popup=popup_text,
                        tooltip=row["activity"] if row["activity"] else "Log Point",
                        icon=folium.Icon(color="blue", icon="car", prefix="fa")
                    ).add_to(patrol_map)

            st_folium(patrol_map, width="100%", height=500)

# ---- ROLE BASED PAGES ----
role = st.session_state["role"]
contractor = st.session_state.get("contractor", "").lower()

if role == "admin":
    allowed_pages = ["Incident Report", "Idle Time Analyzer", "View Idle Reports",
                     "Breaks & Pickups", "Search Page"]
elif role == "control":
    allowed_pages = ["Incident Report", "Idle Time Analyzer", "View Idle Reports",
                     "Breaks & Pickups", "Search Page"]
elif role == "patrol":
    allowed_pages = ["Incident Report", "Breaks & Pickups"]
elif role == "re_admin":
    # RE admin has access to all pages
    allowed_pages = ["Incident Report", "Idle Time Analyzer", "View Idle Reports",
                     "Report Search", "Breaks & Pickups", "Search Page", "Accident Analysis"]
else:
    allowed_pages = []

# Add Paschal Parking Analyzer for Paschal contractor
if contractor == "paschal":
    allowed_pages.append("Paschal Parking Analyzer")

page = st.sidebar.radio("📑 Go to", allowed_pages, key="page_selector")

# ---- PAGE ROUTER ----
if page == "Incident Report":
    from incident_report import incident_report_page
    incident_report_page(patrol_vehicle_options)
elif page == "Idle Time Analyzer":
    from idle_time_analyzer_page import idle_time_analyzer_page
    idle_time_analyzer_page()
elif page == "Paschal Parking Analyzer":
    from paschal_parking_analyzer import paschal_parking_analyzer_page
    paschal_parking_analyzer_page()
elif page == "View Idle Reports":
    from idle_time_analyzer_page import view_idle_reports_page
    view_idle_reports_page()
elif page == "Report Search":
    from report_search import report_search_page
    report_search_page()
elif page == "Breaks & Pickups":
    breaks_pickups_page()
elif page == "Search Page":
    from search_page import search_page
    search_page()
elif page == "Accident Analysis":
    from accident_analysis import accident_analysis_page
    accident_analysis_page()

# ---------------- FOOTER ----------------
st.markdown("""
<div style='text-align: center; color: gray; font-size: 12px;'>© 2025 Hebtron Technologies</div>
<div style='text-align: center; color: blue; font-size: 12px;'>Contact : hebtron25@gmail.com</div>
""", unsafe_allow_html=True)
