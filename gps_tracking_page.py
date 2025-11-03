import streamlit as st
import folium
from streamlit_folium import folium_static
import pandas as pd
from db_utils import get_sqlalchemy_engine, get_active_contractor
from datetime import datetime, timedelta
from sqlalchemy import text
import time
try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

def gps_tracking_page():
    st.header("🚗 GPS Vehicle Tracking")

    # Get contractor and role info
    contractor_id = get_active_contractor()
    user_role = st.session_state.get("role", "unknown")
    user_contractor = st.session_state.get("contractor", "")

    if not user_contractor:
        st.error("No contractor info found in session.")
        return

    # Check if user is from RE Office (can see all vehicles) or patrol role
    is_re_office = user_contractor.lower() == "re office"
    is_patrol = user_role.lower() == "patrol"

    # Display access level information
    if is_re_office:
        st.info("🔍 **RE Office Access**: You can view GPS data for all vehicles from all contractors.")
    elif is_patrol:
        st.info("🚔 **Patrol Officer Access**: You can activate and track patrol vehicles.")
    else:
        st.info(f"🏢 **{user_contractor} Access**: You can view GPS data for your contractor's vehicles only.")

    if not is_re_office and not contractor_id:
        st.error("No contractor selected. Please select a contractor first.")
        return

    # Get vehicles based on user permissions
    engine = get_sqlalchemy_engine()

    if is_re_office:
        vehicles_query = """
            SELECT v.id, v.plate_number, c.name as contractor_name
            FROM vehicles v
            JOIN contractors c ON v.contractor = c.name
            ORDER BY c.name, v.plate_number
        """
        vehicles_df = pd.read_sql(vehicles_query, engine)
        vehicles_df['display_name'] = vehicles_df['contractor_name'] + ' - ' + vehicles_df['plate_number']
    elif is_patrol:
        # Patrol officers can only see patrol vehicles from their contractor
        vehicles_query = """
            SELECT id, plate_number
            FROM vehicles
            WHERE contractor = (SELECT name FROM contractors WHERE id = %s)
            AND plate_number LIKE 'Patrol_%%'
            ORDER BY plate_number
        """
        vehicles_df = pd.read_sql(vehicles_query, engine, params=(contractor_id,))
        vehicles_df['display_name'] = vehicles_df['plate_number']
    else:
        vehicles_query = """
            SELECT id, plate_number
            FROM vehicles
            WHERE contractor = (SELECT name FROM contractors WHERE id = %s)
            ORDER BY plate_number
        """
        vehicles_df = pd.read_sql(vehicles_query, engine, params=(contractor_id,))
        vehicles_df['display_name'] = vehicles_df['plate_number']

    if vehicles_df.empty:
        st.warning("No vehicles found for your contractor.")
        return

    # Vehicle selection
    vehicle_options = ["Select a vehicle"] + vehicles_df['display_name'].tolist()
    selected_vehicle = st.selectbox("Select Vehicle to Track", vehicle_options)

    if selected_vehicle == "Select a vehicle":
        if is_patrol:
            st.info("Please select a patrol vehicle to activate GPS tracking.")
        else:
            st.info("Please select a vehicle to view its GPS tracking data.")
        return

    # Get vehicle ID first (needed for patrol activation)
    vehicle_row = vehicles_df[vehicles_df['display_name'] == selected_vehicle]
    if vehicle_row.empty:
        st.error("Vehicle not found.")
        return

    vehicle_id = vehicle_row['id'].iloc[0]
    actual_plate_number = vehicle_row['plate_number'].iloc[0]

    # For patrol officers, add activation button
    if is_patrol:
        st.subheader("🚔 Patrol Vehicle Activation")

        # Check current activation status - ensure table exists first
        try:
            # First ensure patrol_logs table exists
            create_table_query = """
                CREATE TABLE IF NOT EXISTS patrol_logs (
                    id SERIAL PRIMARY KEY,
                    vehicle_id INTEGER,
                    timestamp TIMESTAMP,
                    latitude REAL,
                    longitude REAL,
                    activity TEXT,
                    status TEXT DEFAULT 'offline',
                    speed REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            with engine.begin() as conn:
                conn.execute(text(create_table_query))

            # Check the most recent activation and deactivation records
            combined_query = """
                SELECT activity, status, timestamp
                FROM patrol_logs
                WHERE vehicle_id = %s
                AND (activity = 'activated' OR activity = 'deactivated')
                ORDER BY timestamp DESC
                LIMIT 10
            """
            combined_df = pd.read_sql(combined_query, engine, params=(vehicle_id,))

            # Determine current status based on the most recent action
            if not combined_df.empty:
                # Sort by timestamp descending to get the most recent first
                combined_df = combined_df.sort_values('timestamp', ascending=False)
                most_recent = combined_df.iloc[0]

                if most_recent['activity'] == 'activated' and most_recent['status'] == 'online':
                    current_status = 'online'
                    last_update = most_recent['timestamp']
                elif most_recent['activity'] == 'deactivated' and most_recent['status'] == 'offline':
                    current_status = 'offline'
                    last_update = most_recent['timestamp']
                else:
                    # If the most recent record is inconsistent, check the previous records
                    if len(combined_df) > 1:
                        previous = combined_df.iloc[1]
                        if previous['activity'] == 'activated' and previous['status'] == 'online':
                            current_status = 'online'
                            last_update = previous['timestamp']
                        else:
                            current_status = 'offline'
                            last_update = most_recent['timestamp']
                    else:
                        current_status = 'offline'
                        last_update = most_recent['timestamp']
            else:
                current_status = 'offline'
                last_update = None
        except Exception as e:
            # If table doesn't exist or other error, assume offline
            current_status = 'offline'
            last_update = None

        # Display current status
        if current_status == 'online':
            st.success(f"🟢 GPS tracking is ACTIVE for {selected_vehicle}")
            if last_update:
                st.info(f"Activated at: {last_update}")
        else:
            st.info(f"🔴 GPS tracking is INACTIVE for {selected_vehicle}")

        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            if current_status != 'online':
                if st.button("🟢 Activate GPS Tracking", type="primary"):
                    # Insert activation record
                    try:
                        with engine.begin() as conn:
                            conn.execute(text("""
                                INSERT INTO patrol_logs (vehicle_id, timestamp, latitude, longitude, activity, status, speed)
                                VALUES (:vehicle_id, :timestamp, :latitude, :longitude, :activity, :status, :speed)
                            """), {
                                "vehicle_id": vehicle_id,
                                "timestamp": datetime.now(),
                                "latitude": -1.2921,  # Nairobi default
                                "longitude": 36.8219,
                                "activity": "activated",
                                "status": "online",
                                "speed": 0.0
                            })
                        st.success(f"GPS tracking activated for {selected_vehicle}")
                        st.info("The vehicle GPS tracker is now active and will start recording location, speed, and idle time data.")
                        st.info("📍 **Tracking Features:**")
                        st.markdown("- Real-time location monitoring")
                        st.markdown("- Speed tracking (km/h)")
                        st.markdown("- Date and time stamps")
                        st.markdown("- Idle time detection and recording")
                        # GPS tracking remains active until manually deactivated
                        # No automatic timeout - stays active for 24+ hours
                        time.sleep(0.1)  # Brief pause to ensure DB commit
                        st.rerun()  # Refresh to show updated status
                    except Exception as e:
                        st.error(f"FATAL DB ERROR: Failed to activate GPS tracking: {e}")
                        # Don't rerun on failure

        with col2:
            if current_status == 'online':
                if st.button("🔴 Deactivate GPS Tracking"):
                    # Insert deactivation record
                    try:
                        with engine.begin() as conn:
                            conn.execute(text("""
                                INSERT INTO patrol_logs (vehicle_id, timestamp, latitude, longitude, activity, status, speed)
                                VALUES (:vehicle_id, :timestamp, :latitude, :longitude, :activity, :status, :speed)
                            """), {
                                "vehicle_id": vehicle_id,
                                "timestamp": datetime.now(),
                                "latitude": -1.2921,  # Nairobi default
                                "longitude": 36.8219,
                                "activity": "deactivated",
                                "status": "offline",
                                "speed": 0.0
                            })
                        st.warning(f"GPS tracking deactivated for {selected_vehicle}")
                        st.info("The vehicle GPS tracker has been stopped.")
                        # GPS tracking remains active until manually deactivated
                        # No automatic timeout - stays active for 24+ hours
                        time.sleep(0.1)  # Brief pause to ensure DB commit
                        st.rerun()  # Refresh to show updated status
                    except Exception as e:
                        st.error(f"FATAL DB ERROR: Failed to deactivate GPS tracking: {e}")
                        # Don't rerun on failure

    # Date range selection
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", datetime.now().date() - timedelta(days=1))
    with col2:
        end_date = st.date_input("End Date", datetime.now().date())

    if start_date > end_date:
        st.error("Start date cannot be after end date.")
        return

    # Time range
    col3, col4 = st.columns(2)
    with col3:
        start_time = st.time_input("Start Time", datetime.now().replace(hour=0, minute=0).time())
    with col4:
        end_time = st.time_input("End Time", datetime.now().time())

    # Combine date and time
    start_datetime = datetime.combine(start_date, start_time)
    end_datetime = datetime.combine(end_date, end_time)

    # Fetch GPS data (patrol logs) - create table if not exists
    try:
        # First ensure patrol_logs table exists
        create_table_query = """
            CREATE TABLE IF NOT EXISTS patrol_logs (
                id SERIAL PRIMARY KEY,
                vehicle_id INTEGER,
                timestamp TIMESTAMP,
                latitude REAL,
                longitude REAL,
                activity TEXT,
                status TEXT DEFAULT 'offline',
                speed REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        with engine.begin() as conn:
            conn.execute(text(create_table_query))

        # Now fetch GPS data
        gps_query = """
            SELECT timestamp, latitude, longitude, activity, speed
            FROM patrol_logs
            WHERE vehicle_id = %s
            AND timestamp BETWEEN %s AND %s
            ORDER BY timestamp ASC
        """
        gps_df = pd.read_sql(gps_query, engine, params=(vehicle_id, start_datetime, end_datetime))
    except Exception as e:
        if "does not exist" in str(e):
            st.info("Patrol logs table not found. Creating table...")
            # Create the table and return empty dataframe
            create_table_query = """
                CREATE TABLE IF NOT EXISTS patrol_logs (
                    id SERIAL PRIMARY KEY,
                    vehicle_id INTEGER,
                    timestamp TIMESTAMP,
                    latitude REAL,
                    longitude REAL,
                    activity TEXT,
                    status TEXT DEFAULT 'offline',
                    speed REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            with engine.begin() as conn:
                conn.execute(text(create_table_query))
            st.success("Patrol logs table created successfully!")
            gps_df = pd.DataFrame()  # Empty dataframe since no data exists yet
        else:
            st.error(f"Error accessing patrol logs: {e}")
            gps_df = pd.DataFrame()

    if gps_df.empty:
        st.warning(f"No GPS data found for {actual_plate_number} in the selected time range.")
        return

    # Display statistics
    st.subheader("📊 Tracking Statistics")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total GPS Points", len(gps_df))
    with col2:
        idle_points = len(gps_df[gps_df['activity'] == 'idle'])
        st.metric("Idle Points", idle_points)
    with col3:
        moving_points = len(gps_df[gps_df['activity'] == 'moving'])
        st.metric("Moving Points", moving_points)
    with col4:
        avg_speed = gps_df['speed'].mean()
        st.metric("Avg Speed (km/h)", f"{avg_speed:.1f}")

    # Create map
    st.subheader("🗺️ GPS Route Map")

    if gps_df['latitude'].notna().any() and gps_df['longitude'].notna().any():
        valid_gps = gps_df.dropna(subset=['latitude', 'longitude'])

        if not valid_gps.empty:
            center_lat = valid_gps['latitude'].iloc[0]
            center_lng = valid_gps['longitude'].iloc[0]

            m = folium.Map(location=[center_lat, center_lng], zoom_start=13)

            coordinates = [[row['latitude'], row['longitude']] for _, row in valid_gps.iterrows()]

            if len(coordinates) > 1:
                folium.PolyLine(coordinates, color='blue', weight=3, opacity=0.7).add_to(m)

            if coordinates:
                folium.Marker(
                    coordinates[0],
                    popup=f"Start: {valid_gps['timestamp'].iloc[0]}",
                    icon=folium.Icon(color='green', icon='play')
                ).add_to(m)

                folium.Marker(
                    coordinates[-1],
                    popup=f"End: {valid_gps['timestamp'].iloc[-1]}",
                    icon=folium.Icon(color='red', icon='stop')
                ).add_to(m)

            idle_data = valid_gps[valid_gps['activity'] == 'idle']
            for _, row in idle_data.iterrows():
                folium.Marker(
                    [row['latitude'], row['longitude']],
                    popup=f"Idle: {row['timestamp']}",
                    icon=folium.Icon(color='orange', icon='pause')
                ).add_to(m)

            folium_static(m)

            st.subheader("📈 Speed Over Time")
            if 'speed' in valid_gps.columns and valid_gps['speed'].notna().any():
                if PLOTLY_AVAILABLE:
                    fig = px.line(
                        valid_gps,
                        x='timestamp',
                        y='speed',
                        title=f'Speed Tracking for {actual_plate_number}',
                        labels={'timestamp': 'Time', 'speed': 'Speed (km/h)'}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.line_chart(valid_gps.set_index('timestamp')['speed'])

            st.subheader("📋 Activity Summary")
            activity_counts = gps_df['activity'].value_counts()
            if PLOTLY_AVAILABLE:
                fig_pie = px.pie(
                    values=activity_counts.values,
                    names=activity_counts.index,
                    title=f'Activity Distribution for {actual_plate_number}'
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.bar_chart(activity_counts)

        else:
            st.warning("No valid GPS coordinates found for the selected vehicle and time range.")
    else:
        st.warning("No GPS data with valid coordinates found.")

    with st.expander("📋 Raw GPS Data"):
        st.dataframe(gps_df)

if __name__ == "__main__":
    gps_tracking_page()