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

try:
    from streamlit_autorefresh import st_autorefresh
    AUTOREFRESH_AVAILABLE = True
except ImportError:
    AUTOREFRESH_AVAILABLE = False

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="VTS REPORT TOOL",
    layout="wide",
    page_icon="Kenhalogo.png" if os.path.exists("Kenhalogo.png") else None
)

# ---------------- DATABASE INITIALIZATION ----------------
def init_database_if_needed():
    """Initialize database tables if they don't exist"""
    from db_utils import init_database

    # Initialize database tables and data
    try:
        init_database()

        # Always ensure vehicles exist (in case they were deleted or missing)
        # Note: The patrol cars being monitored through GPRS are the five vehicles from the two contractors:
        # Wizpro (3 vehicles + recovery car) and Paschal (2 vehicles + recovery car)
        # The recovery cars serve as additional slots for backup vehicles
        from db_utils import get_sqlalchemy_engine, USE_SQLITE
        from sqlalchemy import text

        engine = get_sqlalchemy_engine()
        with engine.begin() as conn:
            # Total of 8 vehicles: 3 Wizpro, 2 Paschal, 3 Avators
            vehicles = [
                ('KDG 320Z', 'Wizpro'), ('KDS 374F', 'Wizpro'), ('KDK 825Y', 'Wizpro'),
                ('KDC 873G', 'Paschal'), ('KDD 500X', 'Paschal'),
                ('KAV 444A', 'Avators'), ('KAV 555A', 'Avators'), ('KAV 666A', 'Avators')
            ]
            # Use raw cursor for vehicle insertion to avoid SQLAlchemy parameter issues
            cursor = conn.connection.cursor()
            for plate_number, contractor in vehicles:
                if USE_SQLITE:
                    cursor.execute("INSERT OR IGNORE INTO vehicles (plate_number, contractor) VALUES (?, ?)",
                                  (plate_number, contractor))
                else:
                    cursor.execute("INSERT INTO vehicles (plate_number, contractor) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                                  (plate_number, contractor))

            # Add sample idle reports for testing (only if table is empty)
            try:
                if USE_SQLITE:
                    cursor.execute("SELECT COUNT(*) FROM idle_reports")
                else:
                    cursor.execute("SELECT COUNT(*) FROM idle_reports")
                count = cursor.fetchone()[0]

                if count == 0:  # Only add sample data if table is empty
                    from datetime import datetime
                    idle_reports = [
                        ('KDG 320Z', datetime(2024, 10, 1, 8, 0, 0), datetime(2024, 10, 1, 8, 30, 0), 30.0, 'Nairobi CBD', -1.2864, 36.8172, 'Traffic congestion', 'admin', 1),
                        ('KDS 374F', datetime(2024, 10, 1, 9, 15, 0), datetime(2024, 10, 1, 9, 45, 0), 30.0, 'Westlands', -1.2630, 36.8065, 'Waiting for client', 'admin', 1),
                        ('KDC 873G', datetime(2024, 10, 1, 10, 0, 0), datetime(2024, 10, 1, 10, 20, 0), 20.0, 'Kilimani', -1.2910, 36.7844, 'Break time', 'admin', 2),
                        ('KDD 500X', datetime(2024, 10, 1, 11, 30, 0), datetime(2024, 10, 1, 12, 0, 0), 30.0, 'Karen', -1.3168, 36.7073, 'Lunch break', 'admin', 2),
                        ('KAV 444A', datetime(2024, 10, 1, 14, 0, 0), datetime(2024, 10, 1, 14, 25, 0), 25.0, 'Parklands', -1.2640, 36.8261, 'Vehicle maintenance', 'admin', 4),
                    ]
                    for vehicle, idle_start, idle_end, duration, location, lat, lon, description, uploaded_by, contractor_id in idle_reports:
                        if USE_SQLITE:
                            cursor.execute("""
                                INSERT OR IGNORE INTO idle_reports
                                (vehicle, idle_start, idle_end, idle_duration_min, location_address, latitude, longitude, description, uploaded_by, contractor_id, uploaded_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (vehicle, idle_start, idle_end, duration, location, lat, lon, description, uploaded_by, contractor_id, datetime.now()))
                        else:
                            cursor.execute("""
                                INSERT INTO idle_reports
                                (vehicle, idle_start, idle_end, idle_duration_min, location_address, latitude, longitude, description, uploaded_by, contractor_id, uploaded_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT DO NOTHING
                            """, (vehicle, idle_start, idle_end, duration, location, lat, lon, description, uploaded_by, contractor_id, datetime.now()))
            except Exception as e:
                st.warning(f"Could not check idle_reports table: {e}")

            cursor.close()

    except Exception as e:
        st.error(f"❌ Database initialization failed: {e}")

# Initialize database on app startup
print("🚀 Starting VTS Report Tool...")
init_database_if_needed()

# PWA Support - Add manifest, meta tags, and service worker
st.markdown("""
<link rel="manifest" href="/static/pwa_manifest.json">
<meta name="theme-color" content="#004080">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="VTS Reports">
<meta name="mobile-web-app-capable" content="yes">
<meta name="msapplication-TileColor" content="#004080">
<meta name="msapplication-config" content="/browserconfig.xml">
""", unsafe_allow_html=True)

# Register Service Worker
st.markdown("""
<script>
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('/static/sw.js')
            .then(function(registration) {
                console.log('SW registered: ', registration);
            })
            .catch(function(registrationError) {
                console.log('SW registration failed: ', registrationError);
            });
    });
}
</script>
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
    st.session_state["selected_vehicle"] = None

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
            from db_utils import USE_SQLITE

            engine = get_sqlalchemy_engine()
            conn = engine.raw_connection()
            cur = conn.cursor()

            if USE_SQLITE:
                # SQLite uses ?
                cur.execute("SELECT u.id, u.password_hash, u.role FROM users u JOIN contractors c ON u.contractor_id = c.id WHERE c.name = ? AND u.username = ?",
                            (contractor, username))
            else:
                # PostgreSQL uses %s
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

# PWA Install Button
import streamlit.components.v1 as components

pwa_install_html = """
<div id="install-container" style="margin-bottom: 10px;">
    <button id="install-btn" style="
        background: #004080;
        color: white;
        border: none;
        padding: 12px 15px;
        border-radius: 5px;
        cursor: pointer;
        width: 100%;
        font-size: 14px;
        font-weight: bold;
        margin-bottom: 8px;
    ">
        📱 Install VTS Report Tool
    </button>
    <button id="manual-install-btn" style="
        background: #28a745;
        color: white;
        border: none;
        padding: 8px 12px;
        border-radius: 3px;
        cursor: pointer;
        width: 100%;
        font-size: 12px;
    ">
        🔧 Manual Install Instructions
    </button>
    <div id="manual-instructions" style="display: none; margin-top: 10px; padding: 10px; background: #f8f9fa; border-radius: 3px; font-size: 12px;">
        <strong>Manual Installation:</strong><br>
        1. Open Chrome menu (⋮)<br>
        2. Click "Install VTS Report Tool"<br>
        3. Or click "Add to Home Screen"<br>
        <em>Note: May not work on localhost</em>
    </div>
</div>
<script>
let deferredPrompt;

window.addEventListener('beforeinstallprompt', (e) => {
    console.log('beforeinstallprompt event fired');
    e.preventDefault();
    deferredPrompt = e;
    // Keep button visible since PWA is supported
});

document.addEventListener('DOMContentLoaded', function() {
    const installBtn = document.getElementById('install-btn');
    const manualBtn = document.getElementById('manual-install-btn');
    const instructions = document.getElementById('manual-instructions');

    installBtn.addEventListener('click', async () => {
        if (deferredPrompt) {
            deferredPrompt.prompt();
            const { outcome } = await deferredPrompt.userChoice;
            console.log('User response to install prompt:', outcome);
            deferredPrompt = null;
            installBtn.textContent = '✅ Installed!';
            installBtn.disabled = true;
        } else {
            // Fallback for when PWA prompt is not available
            alert('PWA installation not available. Try manual installation or use Chrome on a proper domain.');
        }
    });

    manualBtn.addEventListener('click', () => {
        instructions.style.display = instructions.style.display === 'none' ? 'block' : 'none';
    });
});

window.addEventListener('appinstalled', (evt) => {
    console.log('PWA was installed successfully');
    const installBtn = document.getElementById('install-btn');
    installBtn.textContent = '✅ Installed!';
    installBtn.disabled = true;
});
</script>
"""

components.html(pwa_install_html, height=60)

if st.sidebar.button("📦 Download Web App Package"):
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
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id, plate_number
            FROM vehicles
            WHERE contractor = :contractor
            ORDER BY plate_number
        """), {"contractor": contractor})
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

        # Create web app package ZIP on disk
        zip_path = "downloads/vts_web_app_package.zip"

        if not os.path.exists(zip_path) or st.button("🔄 Regenerate Package"):
            import zipfile

            with st.spinner("Creating web app package..."):
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    # Core files
                    core_files = [
                        'vts_report_tool.py', 'api.py', 'db_utils.py', 'schema.sql',
                        'web_app_packager.py', 'Kenhalogo.png', 'README.md'
                    ]
                    for file in core_files:
                        if os.path.exists(file):
                            zip_file.write(file)

                    # Directories
                    dirs_to_include = ['dejavu-fonts-ttf-2.37', 'static']
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
            "--server.address", "localhost",
            "--browser.gatherUsageStats", "false"
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

## 📱 PWA Installation

This web app supports Progressive Web App (PWA) installation for native app-like experience on mobile and desktop devices.

## 🆘 Support

Contact: hebtron25@gmail.com'''
                    zip_file.writestr('PACKAGE_README.md', readme_content)

            st.success("✅ Web app package created successfully!")

        # Provide download link
        if os.path.exists(zip_path):
            with open(zip_path, "rb") as f:
                zip_data = f.read()
            st.download_button(
                label="📦 Download Web App Package",
                data=zip_data,
                file_name="vts_web_app_package.zip",
                mime="application/zip"
            )
            st.info(f"📁 Package size: {len(zip_data) / (1024*1024):.1f} MB")
        else:
            st.error("❌ Package file not found. Click 'Regenerate Package' to create it.")

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
    - **Install as App**: Use the "📱 Install VTS Report Tool" button in the sidebar, or click browser menu → "Install VTS Report Tool"
    - **Offline Access**: Core functionality works without internet (except maps and API calls)
    - **Native App Feel**: Runs fullscreen like a mobile app
    - **Auto-Updates**: Gets latest features automatically
    - **Background Sync**: Queues actions when offline and syncs when back online
    - **Push Notifications**: Receive updates (when implemented)

    ### 🔧 Troubleshooting PWA Installation:
    If the install button doesn't appear in Chrome:
    1. **Restart Chrome completely** (close all windows and reopen)
    2. Make sure you're using Chrome browser (not Edge in IE mode)
    3. The app must be running on localhost or HTTPS
    4. Try refreshing the page and waiting a few seconds
    5. Check Chrome settings:
       - Go to `chrome://flags/#enable-desktop-pwas` and enable it
       - For local development: `chrome://flags/#allow-insecure-localhost` and enable it
    6. Open browser DevTools (F12) → Console tab to check for errors
    7. Look for "SW registered" and "beforeinstallprompt event fired" messages

    ### Features Included:
    - ✅ Complete web interface
    - ✅ User authentication
    - ✅ Vehicle tracking
    - ✅ Patrol logs with maps
    - ✅ Incident reporting
    - ✅ All analysis tools
    - ✅ **PWA capabilities** (installable, offline-ready)
    """)

    if st.button("Back to Main App"):
        st.session_state["show_web_download"] = False
        st.rerun()

    st.stop()  # Don't show the rest of the app


vehicle_list = get_vehicles_for_contractor(contractor)
if not vehicle_list:
    st.warning(f"No vehicles found for contractor {contractor}")
    patrol_vehicle_options = ["Replacement Car"]
    selected_vehicle = None
else:
    # Get unique vehicle plates only (remove duplicates)
    all_plates = [v["plate_number"] for v in vehicle_list]
    patrol_vehicle_options = sorted(list(set(all_plates)))

    # Use persistent vehicle selection
    if st.session_state.get("selected_vehicle") and st.session_state["selected_vehicle"] in patrol_vehicle_options:
        default_index = patrol_vehicle_options.index(st.session_state["selected_vehicle"])
    else:
        default_index = 0

    selected_vehicle = st.sidebar.selectbox(
        "🚗 Select Vehicle",
        patrol_vehicle_options,
        index=default_index,
        key="vehicle_selector"
    )

    # Update session state when vehicle changes
    if selected_vehicle != st.session_state.get("selected_vehicle"):
        st.session_state["selected_vehicle"] = selected_vehicle

# ---- LOAD PATROL LOGS ----
if selected_vehicle:
    vehicle_id = next((v["id"] for v in vehicle_list if v["plate_number"] == selected_vehicle), None)
    if vehicle_id:
        engine = get_sqlalchemy_engine()
        with engine.begin() as conn:
            # Check if patrol_logs table exists first
            try:
                patrol_logs = pd.read_sql("""
                    SELECT timestamp, latitude, longitude, activity, speed
                    FROM patrol_logs
                    WHERE vehicle_id = %s
                    ORDER BY timestamp DESC
                """, conn, params=(vehicle_id,))
            except Exception as e:
                if "does not exist" in str(e):
                    st.info(f"Patrol logs table not found. Please ensure database is properly initialized.")
                    patrol_logs = pd.DataFrame()  # Empty dataframe
                else:
                    st.error(f"Error loading patrol logs: {e}")
                    patrol_logs = pd.DataFrame()  # Empty dataframe

        if patrol_logs.empty:
            st.info(f"No patrol logs found for {selected_vehicle}")
        else:
            st.subheader(f"📋 Patrol Logs for {selected_vehicle}")
            st.dataframe(patrol_logs, width='stretch')

            st.subheader(f"🗺️ Map View for {selected_vehicle}")

            if not patrol_logs.empty and patrol_logs.iloc[0]["latitude"] and patrol_logs.iloc[0]["longitude"]:
                start_lat = patrol_logs.iloc[0]["latitude"]
                start_lon = patrol_logs.iloc[0]["longitude"]
            else:
                start_lat, start_lon = -1.2921, 36.8219

            patrol_map = folium.Map(location=[start_lat, start_lon], zoom_start=12)

            for _, row in patrol_logs.iterrows():
                if row["latitude"] and row["longitude"]:
                    popup_text = f"""
                    <b>Time:</b> {row['timestamp']}<br>
                    <b>Activity:</b> {row['activity']}<br>
                    <b>Speed:</b> {row.get('speed', 'N/A')} km/h
                    """
                    folium.Marker(
                        [row["latitude"], row["longitude"]],
                        popup=popup_text,
                        tooltip=f"{row['activity']} - {row.get('speed', 'N/A')} km/h" if row["activity"] else "Log Point",
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
                     "Breaks & Pickups", "Search Page", "GPS Tracking", "Real-Time GPS"]
elif role == "contractor":
    allowed_pages = ["Incident Report", "GPS Tracking", "Real-Time GPS"]
elif role == "admin":
    allowed_pages = ["Incident Report", "Idle Time Analyzer", "View Idle Reports",
                     "Breaks & Pickups", "Search Page", "GPS Tracking", "Real-Time GPS"]
elif role == "patrol":
    allowed_pages = ["Incident Report", "Breaks & Pickups", "GPS Tracking", "Real-Time GPS"]
elif role == "re_admin":
    # RE admin has access to all pages including backup management and system manager
    allowed_pages = ["Incident Report", "Idle Time Analyzer", "View Idle Reports",
                     "Report Search", "Breaks & Pickups", "Search Page", "Accident Analysis", "GPS Tracking", "Real-Time GPS", "Backup Management", "System Manager"]
else:
    allowed_pages = []

# Add Paschal Parking Analyzer for Paschal contractor
if contractor == "paschal":
    allowed_pages.append("Paschal Parking Analyzer")

page = st.sidebar.radio("📑 Go to", allowed_pages, key="page_selector")

# ---- PAGE ROUTER ----
# Clear previous page content to prevent overshadowing
st.empty()

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
elif page == "GPS Tracking":
    from gps_tracking_page import gps_tracking_page
    gps_tracking_page()
elif page == "Real-Time GPS":
    # Show GPS monitoring page first
    from realtime_gps_monitoring import realtime_gps_monitoring_page
    realtime_gps_monitoring_page()

    # Add Google Maps integration below the existing map
    st.markdown("---")
    st.subheader("🌐 Google Maps View")

    # Get current vehicle locations for Google Maps
    engine = get_sqlalchemy_engine()
    contractor_id = get_active_contractor()

    if contractor_id:
        try:
            with engine.begin() as conn:
                # Get latest GPS data for all vehicles
                vehicles_query = """
                    SELECT v.plate_number, v.contractor,
                           COALESCE(p.latitude, -1.2921) as latitude,
                           COALESCE(p.longitude, 36.8219) as longitude,
                           COALESCE(p.status, 'offline') as status,
                           COALESCE(p.activity, 'unknown') as activity,
                           p.timestamp as last_update
                    FROM vehicles v
                    LEFT JOIN patrol_logs p ON v.id = p.vehicle_id
                        AND p.timestamp = (
                            SELECT MAX(timestamp)
                            FROM patrol_logs
                            WHERE vehicle_id = v.id
                            AND timestamp > datetime('now', '-10 minutes')
                        )
                    WHERE v.contractor_id = ?
                    ORDER BY v.contractor, v.plate_number
                """
                result = conn.execute(text(vehicles_query), (contractor_id,))
                vehicles_data = result.fetchall()

                if vehicles_data:
                    # Create Google Maps HTML with markers
                    map_html = f"""
                    <div style="width: 100%; height: 500px;">
                        <iframe
                            width="100%"
                            height="500"
                            frameborder="0"
                            style="border:0"
                            src="https://www.google.com/maps/embed/v1/view?key=AIzaSyBFw0Qbyq9zTFTd-tUY6dO4r7Kj7qfJfFg&center=-1.2921,36.8219&zoom=12"
                            allowfullscreen>
                        </iframe>
                    </div>
                    <p style="text-align: center; color: #666; font-size: 14px; margin-top: 10px;">
                        📍 Google Maps integration - Full interactive map with satellite view available
                    </p>
                    """

                    # Display Google Maps
                    import streamlit.components.v1 as components
                    components.html(map_html, height=550)

                    # Show vehicle status summary below map
                    st.subheader("📊 Vehicle Status Summary")

                    # Create a summary table
                    summary_data = []
                    for plate, contractor, lat, lng, status, activity, last_update in vehicles_data:
                        summary_data.append({
                            "Vehicle": plate,
                            "Status": "🟢 Online" if status == "online" else "🔴 Offline",
                            "Activity": activity.title(),
                            "Last Update": str(last_update)[:19] if last_update else "Never",
                            "Location": f"{lat:.4f}, {lng:.4f}"
                        })

                    if summary_data:
                        import pandas as pd
                        summary_df = pd.DataFrame(summary_data)
                        st.dataframe(summary_df, use_container_width=True, hide_index=True)

                else:
                    st.info("No vehicle data available for Google Maps view.")

        except Exception as e:
            st.warning(f"Could not load Google Maps data: {e}")
            st.info("The standard Folium map above is still available.")
    else:
        st.info("Please select a contractor to view Google Maps.")
elif page == "Accident Analysis":
    from accident_analysis import accident_analysis_page
    accident_analysis_page()
elif page == "Backup Management":
    try:
        from backup_management import backup_management_page
        backup_management_page()
    except Exception as e:
        st.error(f"❌ Error loading Backup Management: {e}")
        st.info("💡 This feature requires additional setup. Please contact the administrator.")
elif page == "System Manager":
    try:
        from system_manager import system_manager_page
        system_manager_page()
    except Exception as e:
        st.error(f"❌ Error loading System Manager: {e}")
        st.info("💡 This feature requires additional setup. Please contact the administrator.")
        import traceback
        with st.expander("View Error Details"):
            st.code(traceback.format_exc())

# ---------------- FOOTER ----------------
st.markdown("""
<div style='text-align: center; color: gray; font-size: 12px;'>© 2025 Hebtron Technologies</div>
<div style='text-align: center; color: blue; font-size: 12px;'>Contact : hebtron25@gmail.com</div>
""", unsafe_allow_html=True)
