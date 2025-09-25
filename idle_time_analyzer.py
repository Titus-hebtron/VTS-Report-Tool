import streamlit as st
import pandas as pd
import io
from datetime import timedelta
from db_utils import save_idle_report, get_idle_reports, get_connection

# 🔹 Column translation map
TRANSLATION_MAP = {
    "Status": "Status",
    "Start": "Idle Start",
    "End": "Idle End",
    "Duration": "Idle Duration (min)",
    "Stop position": "Location",
    "Length": "Distance (km)",
    "Top speed": "Top Speed (km/h)",
    "Average speed": "Avg. Speed (km/h)",
    "Fuel consumption": "Fuel Used (L)",
    "Avg. fuel cons. (100 km)": "Fuel Efficiency (L/100km)",
    "Fuel cost": "Fuel Cost (Ksh)",
    "Engine idle": "Engine Idle (min)",
    "Driver": "Driver",
    "Trailer": "Trailer"
}

# 🔹 Clean timestamps
def clean_data(df):
    df = df.dropna(how="all")
    for col in df.columns:
        if "time" in col.lower() or "date" in col.lower():
            try:
                df[col] = pd.to_datetime(df[col])
            except Exception:
                pass
    return df

# 🔹 Extract vehicle number + normalize report
def preprocess_vts_file(uploaded_file):
    # Load as raw (no headers yet)
    try:
        raw_df = pd.read_excel(uploaded_file, header=None, engine="xlrd")
    except:
        raw_df = pd.read_excel(uploaded_file, header=None, engine="openpyxl")

    # Detect vehicle number from "Object:" row
    vehicle_number = "Unknown Vehicle"
    for row in raw_df[0]:
        if isinstance(row, str) and row.startswith("Object:"):
            vehicle_number = row.replace("Object:", "").strip()
            break

    # Detect where header row starts (where "Status" appears)
    header_row = raw_df[raw_df.eq("Status").any(axis=1)].index[0]

    # Reload properly with header
    try:
        df = pd.read_excel(uploaded_file, header=header_row, engine="xlrd")
    except:
        df = pd.read_excel(uploaded_file, header=header_row, engine="openpyxl")

    # Rename using translation map
    df = df.rename(columns={col: TRANSLATION_MAP[col] for col in df.columns if col in TRANSLATION_MAP})

    # Add vehicle column
    df["Vehicle"] = vehicle_number

    # Convert duration to minutes if needed
    if "Idle Duration (min)" in df.columns:
        df["Idle Duration (min)"] = (
            pd.to_timedelta(df["Idle Duration (min)"], errors="coerce").dt.total_seconds() / 60
        ).fillna(df["Idle Duration (min)"])

    return df

# 🔹 Main Streamlit App
st.title("🚗 Idle Time Analyzer (VTS Reports)")

uploaded_file = st.file_uploader("Upload VTS Report (CSV/XLS/XLSX)", type=["csv", "xls", "xlsx"])
threshold = st.number_input("Idle Duration Threshold (minutes)", min_value=0.0, value=10.0)

idle_periods_df = pd.DataFrame()

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        # Handle raw VTS Excel with "Object:" info
        df = preprocess_vts_file(uploaded_file)

    st.subheader("📊 Processed Data Preview")
    st.dataframe(df.head(20))

    # Ensure correct columns exist
    if {"Vehicle", "Idle Start", "Idle End", "Idle Duration (min)"}.issubset(df.columns):
        # Drop missing values
        df = df.dropna(subset=["Vehicle", "Idle Start", "Idle End", "Idle Duration (min)"])
        # Filter by threshold
        idle_periods_df = df[df["Idle Duration (min)"] > threshold]

        st.subheader("🛑 Idle Periods (> threshold)")
        st.dataframe(idle_periods_df)

        # Save to DB
        if not idle_periods_df.empty and st.button("💾 Save to Database"):
            save_idle_report(idle_periods_df, uploaded_by=st.session_state.get("username", "System"))
            st.success("✅ Idle periods saved to database!")

# 🔹 View, Filter, Delete, Download
st.header("📂 Saved Idle Reports")
df = get_idle_reports(limit=1000)

# --- Filters ---
if not df.empty:
    st.subheader("Filter Idle Reports")
    vehicles = df["Vehicle"].unique()
    selected_vehicle = st.selectbox("Vehicle", options=["All"] + list(vehicles))
    if selected_vehicle != "All":
        df = df[df["Vehicle"] == selected_vehicle]

    if "Idle Start" in df.columns:
        date_min = df["Idle Start"].min()
        date_max = df["Idle Start"].max()
        date_range = st.date_input("Idle Start Date Range", [date_min, date_max])
        if date_range:
            df = df[
                (df["Idle Start"] >= pd.to_datetime(date_range[0]))
                & (df["Idle Start"] <= pd.to_datetime(date_range[1]))
            ]

    # Delete selected
    if "ID" in df.columns:
        delete_ids = st.multiselect("Select rows to delete (by ID)", df["ID"])
        if st.button("🗑 Delete Selected"):
            if delete_ids:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM idle_reports WHERE id = ANY(%s)", (delete_ids,))
                conn.commit()
                cur.close()
                conn.close()
                st.success(f"✅ Deleted {len(delete_ids)} row(s). Refresh to see changes.")

    # Download
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download CSV", data=csv, file_name="filtered_idle_reports.csv", mime="text/csv")

    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False)
    st.download_button(
        "⬇️ Download Excel",
        data=excel_buffer.getvalue(),
        file_name="filtered_idle_reports.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.subheader("📊 Final Data")
    st.dataframe(df)
