import streamlit as st
import pandas as pd
from db_utils import get_sqlalchemy_engine, get_active_contractor
from datetime import datetime, timedelta
import time
from streamlit_folium import folium_static
import folium

try:
    from streamlit_autorefresh import st_autorefresh
    AUTOREFRESH_AVAILABLE = True
except ImportError:
    AUTOREFRESH_AVAILABLE = False

def realtime_gps_monitoring_page():
    # Auto-refresh every 30 seconds (if available)
    if AUTOREFRESH_AVAILABLE:
        st_autorefresh(interval=30 * 1000, key="gps_monitoring_refresh")

    st.header("🗺️ Real-Time GPS Fleet Monitoring")

    # Get contractor and role info
    contractor_id = get_active_contractor()
    user_role = st.session_state.get("role", "unknown")
    user_contractor = st.session_state.get("contractor", "")

    # Check if user is from RE Office (can see all vehicles)
    is_re_office = user_contractor.lower() == "re office"

    # Display access level information
    if is_re_office:
        st.info("🔍 **RE Office Access**: Monitoring all vehicles from all contractors in real-time.")
    else:
        st.info(f"🏢 **{user_contractor} Access**: Monitoring your contractor's vehicles in real-time.")

    # Get all vehicles with their latest GPS status
    engine = get_sqlalchemy_engine()

    if is_re_office:
        # RE Office sees vehicles from Wizpro and Paschal contractors only
        # Always show vehicles even without GPS data - they should be visible on map
        try:
            vehicles_query = """
                SELECT
                    v.id,
                    v.plate_number,
                    c.name as contractor_name,
                    COALESCE(latest_gps.latitude, -1.2921) as latitude,
                    COALESCE(latest_gps.longitude, 36.8219) as longitude,
                    latest_gps.timestamp as last_update,
                    COALESCE(latest_gps.activity, 'stationary') as activity,
                    COALESCE(latest_gps.status, 'offline') as status
                FROM vehicles v
                JOIN contractors c ON v.contractor = c.name
                LEFT JOIN patrol_logs latest_gps ON latest_gps.vehicle_id = v.id
                    AND latest_gps.timestamp = (
                        SELECT MAX(timestamp)
                        FROM patrol_logs
                        WHERE vehicle_id = v.id
                        AND timestamp > datetime('now', '-24 hours')  -- Extended to 24 hours
                    )
                WHERE c.name IN ('Wizpro', 'Paschal')
                ORDER BY c.name, v.plate_number
            """
            vehicles_df = pd.read_sql(vehicles_query, engine)
        except Exception as e:
            # If patrol_logs table doesn't exist, show vehicles without GPS data
            if "does not exist" in str(e) or "UndefinedTable" in str(e):
                vehicles_query = """
                    SELECT
                        v.id,
                        v.plate_number,
                        c.name as contractor_name,
                        -1.2921 as latitude,
                        36.8219 as longitude,
                        NULL as last_update,
                        'stationary' as activity,
                        'offline' as status
                    FROM vehicles v
                    JOIN contractors c ON v.contractor = c.name
                    WHERE c.name IN ('Wizpro', 'Paschal')
                    ORDER BY c.name, v.plate_number
                """
                vehicles_df = pd.read_sql(vehicles_query, engine)
            else:
                raise e
    else:
        # Other contractors see only their vehicles
        # Always show vehicles even without GPS data
        try:
            vehicles_query = """
                SELECT
                    v.id,
                    v.plate_number,
                    COALESCE(latest_gps.latitude, -1.2921) as latitude,
                    COALESCE(latest_gps.longitude, 36.8219) as longitude,
                    latest_gps.timestamp as last_update,
                    COALESCE(latest_gps.activity, 'stationary') as activity,
                    COALESCE(latest_gps.status, 'offline') as status
                FROM vehicles v
                LEFT JOIN patrol_logs latest_gps ON latest_gps.vehicle_id = v.id
                    AND latest_gps.timestamp = (
                        SELECT MAX(timestamp)
                        FROM patrol_logs
                        WHERE vehicle_id = v.id
                        AND timestamp > datetime('now', '-24 hours')  -- Extended to 24 hours
                    )
                WHERE v.contractor = (SELECT name FROM contractors WHERE id = %s)
                ORDER BY v.plate_number
            """
            vehicles_df = pd.read_sql(vehicles_query, engine, params=(contractor_id,))
        except Exception as e:
            # If patrol_logs table doesn't exist, show vehicles without GPS data
            if "does not exist" in str(e) or "UndefinedTable" in str(e):
                vehicles_query = """
                    SELECT
                        v.id,
                        v.plate_number,
                        -1.2921 as latitude,
                        36.8219 as longitude,
                        NULL as last_update,
                        'stationary' as activity,
                        'offline' as status
                    FROM vehicles v
                    WHERE v.contractor = (SELECT name FROM contractors WHERE id = %s)
                    ORDER BY v.plate_number
                """
                vehicles_df = pd.read_sql(vehicles_query, engine, params=(contractor_id,))
            else:
                raise e

    if vehicles_df.empty:
        st.warning("No vehicles found.")
        return

    # Display statistics
    st.subheader("📊 Fleet Status Overview")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_vehicles = len(vehicles_df)
        st.metric("Total Vehicles", total_vehicles)
    with col2:
        online_count = len(vehicles_df[vehicles_df['status'] == 'online'])
        st.metric("Online Now", online_count, delta=f"{online_count}/{total_vehicles}")
    with col3:
        offline_count = len(vehicles_df[vehicles_df['status'] == 'offline'])
        st.metric("Offline", offline_count)
    with col4:
        active_tracking = len(vehicles_df[
            (vehicles_df['status'] == 'online') &
            (vehicles_df['activity'].isin(['moving', 'idle']))
        ])
        st.metric("Actively Tracking", active_tracking)

    # Create OpenStreetMap with Folium
    st.subheader("🗺️ Live Vehicle Locations")

    # Calculate center point
    valid_coords = vehicles_df[
        (vehicles_df['latitude'] != -1.2921) &
        (vehicles_df['longitude'] != 36.8219) &
        (vehicles_df['latitude'].notna()) &
        (vehicles_df['longitude'].notna())
    ]

    if not valid_coords.empty:
        center_lat = valid_coords['latitude'].mean()
        center_lng = valid_coords['longitude'].mean()
    else:
        # Default to Nairobi, Kenya
        center_lat = -1.2921
        center_lng = 36.8219

    # Create folium map
    m = folium.Map(location=[center_lat, center_lng], zoom_start=12)

    # Add vehicle markers
    for _, vehicle in vehicles_df.iterrows():
        if is_re_office:
            vehicle_name = f"{vehicle['contractor_name']} - {vehicle['plate_number']}"
        else:
            vehicle_name = vehicle['plate_number']

        status = vehicle['status']
        activity = vehicle.get('activity', 'Unknown')
        last_update = vehicle.get('last_update', 'Never')

        # Choose marker color based on status
        if status == 'online':
            marker_color = 'green'
            icon_type = 'play'
        else:
            marker_color = 'red'
            icon_type = 'stop'

        # Create popup content
        popup_content = f"""
        <div style="font-family: Arial, sans-serif; font-size: 14px; max-width: 250px;">
            <strong>{vehicle_name}</strong><br>
            <span style="color: {'green' if status == 'online' else 'red'}; font-weight: bold;">
                {'🟢 Online' if status == 'online' else '🔴 Offline'}
            </span><br>
            <strong>Activity:</strong> {activity}<br>
            <strong>Last Update:</strong> {str(last_update) if last_update != 'Never' else 'Never'}
        </div>
        """

        folium.Marker(
            [vehicle['latitude'], vehicle['longitude']],
            popup=popup_content,
            tooltip=vehicle_name,
            icon=folium.Icon(color=marker_color, icon=icon_type, prefix='fa')
        ).add_to(m)

    # Display the map
    folium_static(m, width="100%", height=600)

    # Vehicle status table
    st.subheader("📋 Vehicle Status Details")

    # Format the dataframe for display
    display_df = vehicles_df.copy()
    display_df['last_update'] = display_df['last_update'].fillna('Never')
    display_df['status_display'] = display_df['status'].apply(lambda x: "🟢 Online" if x == "online" else "🔴 Offline")
    display_df['activity'] = display_df['activity'].fillna('Unknown')

    if is_re_office:
        display_cols = ['contractor_name', 'plate_number', 'status_display', 'activity', 'last_update']
        display_names = ['Contractor', 'Vehicle', 'Status', 'Activity', 'Last Update']
    else:
        display_cols = ['plate_number', 'status_display', 'activity', 'last_update']
        display_names = ['Vehicle', 'Status', 'Activity', 'Last Update']

    st.dataframe(
        display_df[display_cols],
        column_config={
            col: st.column_config.TextColumn(col, width="medium")
            for col in display_cols
        },
        use_container_width=True,
        hide_index=True
    )

    # Auto-refresh indicator
    if AUTOREFRESH_AVAILABLE:
        st.success("🔄 **Auto-refresh Active**: Map and status update every 30 seconds")
    else:
        st.warning("⚠️ **Manual Refresh Only**: Install streamlit-autorefresh for auto-updates")

    # Add manual refresh button
    if st.button("🔄 Refresh Now"):
        st.rerun()


if __name__ == "__main__":
    realtime_gps_monitoring_page()