import streamlit as st
import pandas as pd
from datetime import timedelta
import time

def clean_data(df):
    # Drop completely empty rows
    df = df.dropna(how='all')
    # Try to parse datetime columns
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

st.title('Vehicle Idle Time Analyzer')

uploaded_file = st.file_uploader('Upload Excel or CSV file', type=['csv', 'xlsx'])
if uploaded_file:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    df = clean_data(df)
    st.write('Cleaned Data:', df.head())

    # Guess columns
    columns = df.columns.tolist()
    vehicle_col = st.selectbox('Select vehicle ID column', columns)
    time_col = st.selectbox('Select timestamp column', columns)
    speed_col = st.selectbox('Select speed column (0 = idle)', columns)
    threshold = st.number_input('Idle threshold (minutes)', min_value=1, value=5)

    if st.button('Analyze Idle Times'):
        start_time = time.time()
        idle_df = find_idle_times(df, vehicle_col, time_col, speed_col, idle_threshold=threshold)
        end_time = time.time()
        st.write(f'Analysis completed in {end_time - start_time:.2f} seconds')
        st.write('Idle Periods (> threshold):', idle_df)
        st.download_button('Download Idle Report', idle_df.to_csv(index=False), file_name='idle_report.csv')
