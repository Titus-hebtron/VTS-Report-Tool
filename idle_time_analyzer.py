import streamlit as st
import pandas as pd
from datetime import timedelta
from db_utils import save_idle_report, get_idle_reports

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
                    'Vehicle': vehicle_id,
                    'Idle Start': row['idle_start'],
                    'Idle End': row['idle_end'],
                    'Idle Duration (min)': round(idle_duration, 2)
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
        vehicle_col = st.selectbox('Select vehicle ID column', columns)
        time_col = st.selectbox('Select timestamp column', columns)
        speed_col = st.selectbox('Select speed column (0 = idle)', columns)
        threshold = st.number_input('Idle threshold (minutes)', min_value=1, value=5)

        if st.button('Analyze Idle Times'):
            idle_df = find_idle_times(df, vehicle_col, time_col, speed_col, idle_threshold=threshold)
            st.write('Idle Periods (> threshold):', idle_df)
            st.download_button('Download Idle Report', idle_df.to_csv(index=False), file_name='idle_report.csv')
            
            if not idle_df.empty:
                if st.button("Save Idle Report to Database"):
                    try:
                        print("DF columns before save:", idle_df.columns)
                        print(idle_df.head())
                        save_idle_report(idle_df, st.session_state.get('user_name', 'Unknown'))
                        st.success("Idle report saved to database!")
                    except Exception as e:
                        st.error(f"Error saving to database: {e}")

def view_idle_reports_page():
    st.header("Saved Idle Reports")
    df = get_idle_reports()
    st.dataframe(df)
    st.download_button("Download All Idle Reports", df.to_csv(index=False), file_name="all_idle_reports.csv")

import streamlit as st
import pandas as pd
from db_utils import save_idle_report, get_idle_reports, get_connection

st.title("Idle Time Analyzer")

# --- Upload and Analyze ---
uploaded_file = st.file_uploader("Upload Idle Report (CSV or Excel)", type=["csv", "xlsx"])
threshold = st.number_input("Idle Duration Threshold (min)", min_value=0.0, value=10.0)

idle_periods_df = pd.DataFrame()

if uploaded_file:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    # Normalize columns
    df.columns = df.columns.str.strip().str.lower()
    df = df.rename(columns={
        'vehicle': 'Vehicle',
        'idle start': 'Idle Start',
        'idle_end': 'Idle End',
        'idle end': 'Idle End',
        'idle duration (min)': 'Idle Duration (min)',
        'idle_duration_min': 'Idle Duration (min)'
    })
    df.columns = [c.lower() for c in df.columns]
    # Convert types
    df['idle start'] = pd.to_datetime(df['idle start'], errors='coerce')
    df['idle end'] = pd.to_datetime(df['idle end'], errors='coerce')
    df['idle duration (min)'] = pd.to_numeric(df['idle duration (min)'], errors='coerce')
    df = df.dropna(subset=['vehicle', 'idle start', 'idle end', 'idle duration (min)'])
    # Filter by threshold
    idle_periods_df = df[df['idle duration (min)'] > threshold]
    st.subheader("Idle Periods (> threshold)")
    st.dataframe(idle_periods_df)

    # --- Save to Database ---
    if not idle_periods_df.empty and st.button("Save These Idle Periods to Database"):
        save_idle_report(idle_periods_df, uploaded_by=st.session_state.get("username", "System"))
        st.success("Idle periods saved to database!")

# --- View, Filter, Delete, Download ---
st.header("Saved Idle Reports")
# Fetch all idle reports
df = get_idle_reports(limit=1000)

# --- FILTERS ---
st.subheader("Filter Idle Reports")
vehicles = df['Vehicle'].unique()
selected_vehicle = st.selectbox("Vehicle", options=["All"] + list(vehicles))
if selected_vehicle != "All":
    df = df[df['Vehicle'] == selected_vehicle]

date_min = df['Idle Start'].min()
date_max = df['Idle Start'].max()
date_range = st.date_input("Idle Start Date Range", [date_min, date_max])
if date_range:
    df = df[(df['Idle Start'] >= pd.to_datetime(date_range[0])) & (df['Idle Start'] <= pd.to_datetime(date_range[1]))]

# Delete
delete_ids = st.multiselect("Select rows to delete (by ID)", df['ID'])
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