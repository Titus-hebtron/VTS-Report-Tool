import streamlit as st
import pandas as pd
from datetime import timedelta
from db_utils import save_idle_report, get_idle_reports, get_connection

def clean_data(df):
    df = df.dropna(how='all')
    for col in df.columns:
        if 'time' in col.lower() or 'date' in col.lower():
            try:
                df[col] = pd.to_datetime(df[col])
            except Exception:
                pass
    return df

def find_idle_times(df, vehicle_col, time_col, speed_col, idle_threshold=5):
    idle_report = []
    for vehicle_id, group in df.groupby(vehicle_col):
        group = group.sort_values(time_col).copy()
        # Convert speed to numeric, treat non-numeric as 0 (idle)
        group['speed_val'] = pd.to_numeric(group[speed_col], errors='coerce').fillna(0)
        # Idle if speed <= 2 or NaN
        group['is_idle'] = (group['speed_val'] <= 2) | group['speed_val'].isna()
        # Find idle periods using vectorized operations
        group['idle_start'] = group[time_col].where(group['is_idle'] & ~group['is_idle'].shift(1, fill_value=False), pd.NaT)
        group['idle_end'] = group[time_col].where(group['is_idle'] & ~group['is_idle'].shift(-1, fill_value=False), pd.NaT)
        # Forward fill idle_start for consecutive idle rows
        group['idle_start'] = group['idle_start'].fillna(method='ffill')
        # Filter to rows where idle_end is set
        idle_periods = group.dropna(subset=['idle_end'])
        for _, row in idle_periods.iterrows():
            idle_duration = (row['idle_end'] - row['idle_start']).total_seconds() / 60
            if idle_duration > idle_threshold:
                idle_report.append({
                    'vehicle': vehicle_id,
                    'idle_start': row['idle_start'],
                    'idle_end': row['idle_end'],
                    'idle_duration_min': round(idle_duration, 2)
                })
    return pd.DataFrame(idle_report)

def idle_time_analyzer_page():
    st.header("Idle Time Analyzer")
    st.info("Upload an Excel or CSV file downloaded from your GPS website to analyze idle time.")

    uploaded_file = st.file_uploader('Upload Excel or CSV file', type=['csv', 'xlsx'])
    if uploaded_file:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        df = clean_data(df)
        st.write('Cleaned Data:', df.head())

        columns = df.columns.tolist()
        vehicle_col = st.selectbox('Select vehicle ID column', columns, key="vehicle_col")
        time_col = st.selectbox('Select timestamp column', columns, key="time_col")
        speed_col = st.selectbox('Select speed column (0 = idle)', columns, key="speed_col")
        threshold = st.number_input('Idle threshold (minutes)', min_value=1, value=5, key="idle_threshold")

        # Use session_state to store the last analysis
        if 'idle_df' not in st.session_state:
            st.session_state['idle_df'] = pd.DataFrame()

        if st.button('Analyze Idle Times'):
            idle_df = find_idle_times(df, vehicle_col, time_col, speed_col, idle_threshold=threshold)
            st.session_state['idle_df'] = idle_df
            st.write('Idle Periods (> threshold):', idle_df)
            st.download_button('Download Idle Report', idle_df.to_csv(index=False), file_name='idle_report.csv')

        # Show results and save button if analysis has been done
        idle_df = st.session_state.get('idle_df', pd.DataFrame())
        if not idle_df.empty:
            st.write('Idle Periods (> threshold):', idle_df)
            st.download_button('Download Idle Report', idle_df.to_csv(index=False), file_name='idle_report.csv', key="download2")
            if st.button("Save Idle Report to Database"):
                try:
                    save_idle_report(idle_df, st.session_state.get('user_name', 'Unknown'))
                    st.success("Idle report saved to database!")
                except Exception as e:
                    st.error(f"Error saving to database: {e}")

def view_idle_reports_page():
    st.header("Saved Idle Reports")
    df = get_idle_reports(limit=1000)

    # --- FILTERS ---
    st.subheader("Filter Idle Reports")
    # Define all possible patrol vehicles
    all_vehicles = ["KDG 320Z", "KDK 825Y", "KDS 374F"]
    vehicles_in_data = sorted(set(df['vehicle'].dropna().unique()))
    vehicles = sorted(set(all_vehicles) | set(vehicles_in_data))
    selected_vehicle = st.selectbox("Vehicle", options=["All"] + list(vehicles), key="vehicle_filter")
    if selected_vehicle != "All":
        selected_norm = selected_vehicle.strip().upper().rstrip('-')
        df = df[df['vehicle'].str.strip().str.upper().apply(lambda v: v.rstrip('-')) == selected_norm]

    date_min = df['idle_start'].min()
    date_max = df['idle_start'].max()
    if pd.isna(date_min) or pd.isna(date_max):
        st.warning("No idle start dates available to filter.")
        date_range = []
    else:
        date_range = st.date_input("Idle Start Date Range", [date_min, date_max], key="date_range")
        if date_range and len(date_range) == 2:
            df = df[(df['idle_start'] >= pd.to_datetime(date_range[0])) & (df['idle_start'] <= pd.to_datetime(date_range[1]))]
        else:
            st.warning("Please select a valid date range to filter reports.")

    # Delete
    delete_ids = st.multiselect("Select rows to delete (by ID)", df['id'], key="delete_ids")
    if st.button("Delete Selected"):
        if delete_ids:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM idle_reports WHERE id = ANY(%s)", (delete_ids,))
            conn.commit()
            cur.close()
            conn.close()
            st.success(f"Deleted {len(delete_ids)} row(s). Please refresh to see changes.")

    # Download
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download as CSV",
        data=csv,
        file_name="filtered_idle_reports.csv",
        mime="text/csv"
    )

    import io
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False)
    st.download_button(
        label="Download as Excel",
        data=excel_buffer.getvalue(),
        file_name="filtered_idle_reports.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.dataframe(df)