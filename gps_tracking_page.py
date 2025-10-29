import streamlit as st
import folium
from streamlit_folium import folium_static
import pandas as pd
from db_utils import get_sqlalchemy_engine, get_active_contractor
from datetime import datetime, timedelta
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

    # Check if user is from RE Office (can see all vehicles)
    is_re_office = user_contractor.lower() == "re office"

    # Display access level information
    if is_re_office:
        st.info("🔍 **RE Office Access**: You can view GPS data for all vehicles from all contractors.")
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
    else:
        vehicles_query = """
            SELECT id, plate_number
            FROM vehicles
            WHERE contractor = (SELECT name FROM contractors WHERE id = ?)
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
        st.info("Please select a vehicle to view its GPS tracking data.")
        return

    # Get vehicle ID
    vehicle_row = vehicles_df[vehicles_df['display_name'] == selected_vehicle]
    if vehicle_row.empty:
        st.error("Vehicle not found.")
        return

    vehicle_id = vehicle_row['id'].iloc[0]
    actual_plate_number = vehicle_row['plate_number'].iloc[0]

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

    # Fetch GPS data (patrol logs)
    gps_query = """
        SELECT timestamp, latitude, longitude, activity, speed
        FROM patrol_logs
        WHERE vehicle_id = ?
        AND timestamp BETWEEN ? AND ?
        ORDER BY timestamp ASC
    """
    gps_df = pd.read_sql(gps_query, engine, params=(vehicle_id, start_datetime, end_datetime))

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