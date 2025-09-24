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
st.set_page_config(page_title="VTS REPORT TOOL", layout="wide")

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
if role == "admin":
    allowed_pages = ["Incident Report", "Idle Time Analyzer", "View Idle Reports",
                     "Report Search", "Breaks & Pickups", "Search Page"]
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

page = st.sidebar.radio("📑 Go to", allowed_pages, key="page_selector")

# ---- PAGE ROUTER ----
if page == "Incident Report":
    from incident_report import incident_report_page
    incident_report_page(patrol_vehicle_options)
elif page == "Idle Time Analyzer":
    from idle_time_analyzer_page import idle_time_analyzer_page
    idle_time_analyzer_page()
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
