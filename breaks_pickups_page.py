import streamlit as st
import os
import pandas as pd
import datetime
import io
from db_utils import get_sqlalchemy_engine
from sqlalchemy import text
import folium
from streamlit_folium import st_folium
from streamlit_autorefresh import st_autorefresh



# ------------------------ HELPER FUNCTIONS ------------------------
def get_vehicles_for_logged_in_contractor():
    """
    Returns a list of plate_numbers of vehicles assigned to the logged-in contractor.
    Uses st.session_state['contractor'] to filter vehicles.
    """
    contractor = st.session_state.get('contractor')
    if not contractor:
        st.error("❌ No contractor found. Please log in.")
        return []

    engine = get_sqlalchemy_engine()
    query = text("""
        SELECT plate_number
        FROM vehicles
        WHERE contractor = :contractor
        ORDER BY plate_number
    """)

    try:
        with engine.begin() as conn:
            result = conn.execute(query, {"contractor": contractor})
            vehicles = [row[0] for row in result.fetchall()]

        if not vehicles:
            st.warning(f"⚠️ No vehicles found for contractor: {contractor}")
        return vehicles

    except Exception as e:
        st.error(f"❌ Error fetching vehicles: {e}")
        return []


def show_live_map_for_contractor(refresh_interval=5000):
    contractor = st.session_state['contractor']

    # Auto-refresh the map
    st_autorefresh(interval=refresh_interval, key="live_map_refresh")

    engine = get_sqlalchemy_engine()
    query = text("""
        SELECT plate_number, latitude, longitude, status
        FROM vehicles
        WHERE contractor = :contractor
    """)
    with engine.begin() as conn:
        result = conn.execute(query, {"contractor": contractor})
        vehicles = result.fetchall()

    if not vehicles:
        st.info("No vehicles found for your contractor.")
        return

    # Center map on first vehicle
    first_vehicle = vehicles[0]
    m = folium.Map(location=[first_vehicle[1], first_vehicle[2]], zoom_start=12)  # latitude, longitude

    for v in vehicles:
        status_color = "green" if v[3] == "online" else "red"  # status
        folium.Marker(
            location=[v[1], v[2]],  # latitude, longitude
            popup=f"{v[0]} ({v[3]})",  # plate_number, status
            icon=folium.Icon(color=status_color, icon="car", prefix="fa")
        ).add_to(m)

    st_folium(m, width=700, height=500)

# ------------------------ BREAKS & PICKUPS PAGE ------------------------
def breaks_pickups_page():
    st.header("🚓 Breaks & Pickups")

    contractor = st.session_state['contractor']
    st.info(f"Logged in as: **{contractor}**")

    patrol_vehicle_options = get_vehicles_for_logged_in_contractor()
    if not patrol_vehicle_options:
        st.warning("No vehicles found for your contractor.")
        st.stop()

    # ---------------- Break Form ----------------
    st.subheader("🛑 Record a Break")
    with st.form("break_form"):
        break_vehicle = st.selectbox("Select Patrol Vehicle", patrol_vehicle_options)
        break_driver = st.text_input("Driver Name")
        break_reason = st.text_area("Reason for Break")
        break_date = st.date_input("Break Date")
        break_start_time = st.time_input("Break Start Time")
        break_end_time = st.time_input("Break End Time")

        break_start = datetime.datetime.combine(break_date, break_start_time)
        break_end = datetime.datetime.combine(break_date, break_end_time)

        break_submit = st.form_submit_button("Save Break")
        if break_submit:
            from db_utils import get_contractor_id
            contractor_id = get_contractor_id(contractor)

            engine = get_sqlalchemy_engine()
            with engine.begin() as conn:
                conn.execute(
                    text("""
                        INSERT INTO breaks (vehicle, reason, break_start, break_end, break_date, contractor_id)
                        VALUES (:vehicle, :reason, :break_start, :break_end, :break_date, :contractor_id)
                    """),
                    {
                        "vehicle": break_vehicle,
                        "reason": break_reason,
                        "break_start": break_start,
                        "break_end": break_end,
                        "break_date": break_date,
                        "contractor_id": contractor_id
                    }
                )
            st.success("✅ Break record saved!")

    # ---------------- Pickup Form ----------------
    st.subheader("📦 Record a Pickup")
    with st.form("pickup_form"):
        pickup_vehicle = st.selectbox("Select Patrol Vehicle for Pickup", patrol_vehicle_options)
        pickup_driver = st.text_input("Pickup Driver Name")
        pickup_description = st.text_input("Pickup Description")
        pickup_date = st.date_input("Pickup Date")
        pickup_start_time = st.time_input("Pickup Start Time")
        pickup_end_time = st.time_input("Pickup End Time")

        pickup_start = datetime.datetime.combine(pickup_date, pickup_start_time)
        pickup_end = datetime.datetime.combine(pickup_date, pickup_end_time)

        pickup_photo = st.file_uploader("Upload Pickup Photo", type=['jpg', 'jpeg', 'png'])

        pickup_submit = st.form_submit_button("Save Pickup")
        if pickup_submit:
            from db_utils import get_contractor_id
            contractor_id = get_contractor_id(contractor)

            engine = get_sqlalchemy_engine()
            with engine.begin() as conn:
                result = conn.execute(
                    text("""
                        INSERT INTO pickups (vehicle, description, pickup_start, pickup_end, pickup_date, contractor_id)
                        VALUES (:vehicle, :description, :pickup_start, :pickup_end, :pickup_date, :contractor_id)
                    """),
                    {
                        "vehicle": pickup_vehicle,
                        "description": pickup_description,
                        "pickup_start": pickup_start,
                        "pickup_end": pickup_end,
                        "pickup_date": pickup_date,
                        "contractor_id": contractor_id
                    }
                )
                # For SQLite, get the last inserted row id
                result = conn.execute(text("SELECT last_insert_rowid()"))
                pickup_id = result.fetchone()[0]

            if pickup_photo:
                photo_bytes = pickup_photo.read()
                contractor_folder = os.path.join("pickup_images", contractor.replace(" ", "_"))
                os.makedirs(contractor_folder, exist_ok=True)
                photo_path = os.path.join(contractor_folder, f"{pickup_id}_{pickup_photo.name}")
                with open(photo_path, "wb") as f:
                    f.write(photo_bytes)

                st.image(photo_bytes, caption="Uploaded Pickup Photo", width='stretch')

            st.success("✅ Pickup record saved!")

    # ---------------- View Reports ----------------
    st.subheader("📊 View Breaks & Pickups Report")
    vehicle_filter = st.selectbox("Select Vehicle", patrol_vehicle_options, key="combined_filter")
    week_start = st.date_input("Week Start Date", key="combined_week_start")
    week_end = st.date_input("Week End Date", key="combined_week_end")

    if st.button("🔍 View Combined Report"):
        engine = get_sqlalchemy_engine()

        from db_utils import get_contractor_id
        contractor_id = get_contractor_id(contractor)

        pickup_query = """
            SELECT *
            FROM pickups
            WHERE vehicle = ?
            AND contractor_id = ?
            AND pickup_date BETWEEN ? AND ?
            ORDER BY pickup_date DESC
        """
        with engine.connect() as conn:
            pickups_df = pd.read_sql_query(pickup_query, conn, params=[
                vehicle_filter, contractor_id, week_start, week_end
            ])

            break_query = """
                SELECT *
                FROM breaks
                WHERE vehicle = ?
                AND contractor_id = ?
                AND break_date BETWEEN ? AND ?
                ORDER BY break_date DESC
            """
            breaks_df = pd.read_sql_query(break_query, conn, params=[
                vehicle_filter, contractor_id, week_start, week_end
            ])

        if not pickups_df.empty or not breaks_df.empty:
            if not pickups_df.empty:
                pickups_df['Pickup Time'] = pickups_df['pickup_end'].fillna(pickups_df['pickup_start'])
                st.subheader("📦 Pickups")
                st.dataframe(pickups_df)

            if not breaks_df.empty:
                st.subheader("🛑 Breaks")
                st.dataframe(breaks_df)

            # Excel Download
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                if not pickups_df.empty:
                    pickups_df.to_excel(writer, sheet_name="Pickups", index=False)
                if not breaks_df.empty:
                    breaks_df.to_excel(writer, sheet_name="Breaks", index=False)
            st.download_button(
                label="📥 Download Combined Report",
                data=output.getvalue(),
                file_name=f"{vehicle_filter}_breaks_pickups_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("No breaks or pickups found for the selected filters.")

    # ---------------- Live Map ----------------
    # Live GPS tracking is not available in this version
    # Vehicle locations are only available from uploaded idle/parking reports
    st.subheader("🗺️ Live Vehicle Map")
    st.info("🚫 Live GPS tracking is not available in this version. Vehicle locations are only available from uploaded idle/parking reports.")
    # refresh_sec = st.slider("Map refresh interval (seconds)", 1, 30, 5)
    # show_live_map_for_contractor(refresh_interval=refresh_sec*1000)
