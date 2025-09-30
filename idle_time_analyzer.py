import streamlit as st
import pandas as pd
import io
from datetime import timedelta
from db_utils import save_idle_report, get_idle_reports, get_connection, get_active_contractor, get_contractor_name
from idle_time_analyzer_page import parse_wizpro_idle, parse_paschal_idle, parse_paschal_idle_report, detect_idle_format
import re

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

# 🔹 Check if vehicle plate belongs to Wizpro
def is_wizpro_vehicle(plate):
    """Check if a vehicle plate belongs to Wizpro based on patterns"""
    if not plate or plate.lower() in ['unknown', 'unknown vehicle', '']:
        return False

    plate = plate.upper().strip()

    # Wizpro specific patterns - very restrictive to avoid false positives
    # Only enable this when you know the exact Wizpro plate ranges
    wizpro_patterns = [
        # Add specific Wizpro plate ranges here when known
        # Example: r'^KDK\s*\d{3}[A-Z]?',  # Only KDK plates
        # Example: r'^KAB\s*\d{3}[A-Z]?',  # Only KAB plates
    ]

    for pattern in wizpro_patterns:
        if re.match(pattern, plate):
            return True

    return False

# 🔹 Check if document contains Wizpro indicators
def contains_wizpro_indicators(raw_df):
    """Check if the document contains Wizpro-specific indicators"""
    # Convert all cells to string and check for wizpro mentions
    all_text = ' '.join([str(cell) for row in raw_df.values for cell in row if pd.notna(cell)]).lower()

    wizpro_indicators = ['wizpro', 'wiz pro', 'engine idle', 'idle time']
    return any(indicator in all_text for indicator in wizpro_indicators)

# 🔹 Extract vehicle plates from document
def extract_vehicles_from_document(raw_df):
    """Extract all vehicle plates mentioned in the document"""
    vehicles = set()

    for row in raw_df.values:
        for cell in row:
            if pd.notna(cell):
                cell_str = str(cell).strip()
                # Look for license plate patterns
                plate_matches = re.findall(r'\b([A-Z]{2,4}\s*\d{1,4}[A-Z]*)\b', cell_str.upper())
                for match in plate_matches:
                    # Clean the plate
                    clean_plate = re.sub(r'\s+', ' ', match).strip()
                    if len(clean_plate) >= 4:  # Minimum length for a valid plate
                        vehicles.add(clean_plate)

    return list(vehicles)

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

    # Detect where header row starts (search entire sheet for "Status" or other headers)
    header_row = None
    # First try to find "Status" anywhere in the sheet
    status_rows = raw_df[raw_df.eq("Status").any(axis=1)].index
    if len(status_rows) > 0:
        header_row = status_rows[0]
    else:
        # If no "Status", look for other common headers
        common_headers = ["Start", "End", "Duration", "Stop position", "Stop Duration", "Address"]
        for header in common_headers:
            header_rows = raw_df[raw_df.eq(header).any(axis=1)].index
            if len(header_rows) > 0:
                header_row = header_rows[0]
                break

    # Fallback to first row if no headers found
    if header_row is None:
        header_row = 0

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
    # Show detected format and allow manual method selection
    st.subheader("📊 Format Detection & Processing Method")

    # Determine default processing method based on current contractor
    active_contractor_id = get_active_contractor()
    contractor_name = get_contractor_name(active_contractor_id)

    if contractor_name == "Wizpro":
        default_method = "Wizpro"
    elif contractor_name == "Paschal":
        default_method = "Paschal"
    else:
        default_method = "VTS"

    options = ["Auto-detect", "Wizpro", "Paschal", "VTS"]
    default_index = options.index(default_method) if default_method in options else 0

    # Manual processing method selection
    processing_method = st.selectbox(
        f"Select Processing Method (Default: {default_method} for {contractor_name or 'Unknown Contractor'})",
        options=options,
        index=default_index,
        help="Choose the processing method. Defaults to the method associated with your contractor."
    )

    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        # First, read as raw to detect format and find headers
        try:
            raw_df = pd.read_excel(uploaded_file, header=None, engine="xlrd")
        except:
            raw_df = pd.read_excel(uploaded_file, header=None, engine="openpyxl")

        # Search for headers in the entire sheet
        all_headers = set()
        header_row = None
        wizpro_cols = ["Status", "Stop position"]
        paschal_cols = ["Stop Duration", "Address"]

        for row_idx in range(min(len(raw_df), 50)):  # Check first 50 rows for performance
            row_values = raw_df.iloc[row_idx].dropna().astype(str).str.strip()
            all_headers.update(row_values)
            # Also check if this row contains multiple expected headers
            wizpro_matches = sum(1 for col in wizpro_cols if col in row_values.values)
            paschal_matches = sum(1 for col in paschal_cols if col in row_values.values)
            if wizpro_matches >= 1 or paschal_matches >= 1:
                header_row = row_idx
                break

        # Check if manual method is selected
        if processing_method != "Auto-detect":
            st.info(f"🔧 Using manually selected {processing_method} processing method")

            if processing_method == "Wizpro":
                # Read with detected header row
                try:
                    df_with_headers = pd.read_excel(uploaded_file, header=header_row, engine="xlrd")
                except:
                    df_with_headers = pd.read_excel(uploaded_file, header=header_row, engine="openpyxl")
                df = parse_wizpro_idle(df_with_headers)

            elif processing_method == "Paschal":
                # Try to detect if it's idle report or parking format
                coordinate_score = sum(1 for col in all_headers if "coordinate" in col.lower())
                if coordinate_score > 0:
                    # Read entire file for idle report format
                    try:
                        df_raw = pd.read_excel(uploaded_file, header=None, engine="xlrd")
                    except:
                        df_raw = pd.read_excel(uploaded_file, header=None, engine="openpyxl")
                    df = parse_paschal_idle_report(df_raw)
                else:
                    # Read with detected header row for parking format
                    try:
                        df_with_headers = pd.read_excel(uploaded_file, header=header_row, engine="xlrd")
                    except:
                        df_with_headers = pd.read_excel(uploaded_file, header=header_row, engine="openpyxl")
                    df = parse_paschal_idle(df_with_headers)

            elif processing_method == "VTS":
                # Handle raw VTS Excel with "Object:" info
                df = preprocess_vts_file(uploaded_file)

        else:
            # Auto-detection logic
            wizpro_score = sum(1 for col in wizpro_cols if col in all_headers)
            paschal_score = sum(1 for col in paschal_cols if col in all_headers)
            coordinate_score = sum(1 for col in all_headers if "coordinate" in col.lower())

            # Check for Wizpro indicators in document content
            has_wizpro_text = contains_wizpro_indicators(raw_df)
            vehicles_in_doc = extract_vehicles_from_document(raw_df)
            has_wizpro_vehicles = any(is_wizpro_vehicle(plate) for plate in vehicles_in_doc)

            # Prioritize contractor-based detection over content analysis
            if contractor_name == "Wizpro":
                is_wizpro_format = True
                st.info(f"📊 Contractor {contractor_name} detected - prioritizing Wizpro extraction method")
            elif contractor_name == "Paschal":
                is_wizpro_format = False  # Will use Paschal detection logic
                st.info(f"📊 Contractor {contractor_name} detected - prioritizing Paschal extraction method")
            else:
                # For RE Office, use content-based auto-detection
                is_wizpro_format = has_wizpro_text or (wizpro_score >= paschal_score and wizpro_score > 0) or has_wizpro_vehicles
                if is_wizpro_format:
                    st.info("📊 Auto-detected Wizpro format - using Wizpro extraction method")
                else:
                    st.info("📊 Auto-detected non-Wizpro format - proceeding with Paschal/VTS detection")

            if is_wizpro_format:
                if contractor_name != "Wizpro":  # Don't show auto-detect message if already shown contractor message
                    st.info("📊 Auto-detected Wizpro format - using Wizpro extraction method")
                # Read with detected header row
                try:
                    df_with_headers = pd.read_excel(uploaded_file, header=header_row, engine="xlrd")
                except:
                    df_with_headers = pd.read_excel(uploaded_file, header=header_row, engine="openpyxl")
                df = parse_wizpro_idle(df_with_headers)
            elif coordinate_score > 0:
                st.info("📊 Auto-detected Paschal idle report format - using Paschal idle report extraction method")
                # Read entire file for idle report format (no specific header row needed)
                try:
                    df_raw = pd.read_excel(uploaded_file, header=None, engine="xlrd")
                except:
                    df_raw = pd.read_excel(uploaded_file, header=None, engine="openpyxl")
                df = parse_paschal_idle_report(df_raw)
            elif paschal_score > wizpro_score:
                st.info("📊 Auto-detected Paschal parking format - using Paschal parking extraction method")
                # Read with detected header row
                try:
                    df_with_headers = pd.read_excel(uploaded_file, header=header_row, engine="xlrd")
                except:
                    df_with_headers = pd.read_excel(uploaded_file, header=header_row, engine="openpyxl")
                df = parse_paschal_idle(df_with_headers)
            else:
                st.info("📊 Auto-detected VTS format - using VTS extraction method")
                # Handle raw VTS Excel with "Object:" info
                df = preprocess_vts_file(uploaded_file)

    # Display detected columns
    if not df.empty:
        detected_columns = list(df.columns)
        st.write(f"**Detected Columns ({len(detected_columns)}):** {detected_columns}")

        # Manual column mapping section
        st.write("---")
        st.write("**Manual Column Mapping (Optional)**")
        st.write("If automatic detection didn't map columns correctly, use these dropdowns to override:")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            vehicle_col = st.selectbox(
                "Vehicle Column",
                options=["Auto-detect"] + detected_columns,
                index=0,
                help="Column containing vehicle/license plate information"
            )

        with col2:
            start_col = st.selectbox(
                "Start Time Column",
                options=["Auto-detect"] + detected_columns,
                index=0,
                help="Column containing idle start time"
            )

        with col3:
            end_col = st.selectbox(
                "End Time Column",
                options=["Auto-detect"] + detected_columns,
                index=0,
                help="Column containing idle end time"
            )

        with col4:
            duration_col = st.selectbox(
                "Duration Column",
                options=["Auto-detect"] + detected_columns,
                index=0,
                help="Column containing idle duration"
            )

        # Apply manual mappings if selected
        manual_mapping_applied = False
        if vehicle_col != "Auto-detect" or start_col != "Auto-detect" or end_col != "Auto-detect" or duration_col != "Auto-detect":
            st.info("🔄 Applying manual column mappings...")

            # Create mapping dictionary
            column_mapping = {}
            if vehicle_col != "Auto-detect":
                column_mapping[vehicle_col] = "Vehicle"
            if start_col != "Auto-detect":
                column_mapping[start_col] = "Idle Start"
            if end_col != "Auto-detect":
                column_mapping[end_col] = "Idle End"
            if duration_col != "Auto-detect":
                column_mapping[duration_col] = "Idle Duration (min)"

            # Apply the mapping
            df = df.rename(columns=column_mapping)
            manual_mapping_applied = True
            st.success(f"✅ Manual mapping applied: {column_mapping}")

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

def display_saved_idle_reports():
    """Display and manage saved idle reports"""
    st.header("📂 Saved Idle Reports")

    # Only load data when the section is reached (not at import time)
    try:
        df = get_idle_reports(limit=1000)
    except Exception as e:
        st.error(f"❌ Database connection error: {e}")
        st.info("💡 Please ensure the database is running and credentials are correct.")
        df = pd.DataFrame()  # Empty dataframe as fallback
        return

    # --- Filters ---
    if not df.empty:
        st.subheader("Filter Idle Reports")
        vehicles = df["Vehicle"].unique()
        selected_vehicle = st.selectbox("Vehicle", options=["All"] + list(vehicles), key="vehicle_filter_saved")
        if selected_vehicle != "All":
            df = df[df["Vehicle"] == selected_vehicle]

        if "Idle Start" in df.columns:
            date_min = df["Idle Start"].min()
            date_max = df["Idle Start"].max()
            date_range = st.date_input("Idle Start Date Range", [date_min, date_max], key="date_filter_saved")
            if date_range:
                df = df[
                    (df["Idle Start"] >= pd.to_datetime(date_range[0]))
                    & (df["Idle Start"] <= pd.to_datetime(date_range[1]))
                ]

        # Delete selected
        if "ID" in df.columns:
            delete_ids = st.multiselect("Select rows to delete (by ID)", df["ID"], key="delete_filter_saved")
            if st.button("🗑 Delete Selected", key="delete_button_saved"):
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
        st.download_button("⬇️ Download CSV", data=csv, file_name="filtered_idle_reports.csv", mime="text/csv", key="csv_download_saved")

        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)
        st.download_button(
            "⬇️ Download Excel",
            data=excel_buffer.getvalue(),
            file_name="filtered_idle_reports.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="excel_download_saved"
        )

        st.subheader("📊 Final Data")
        st.dataframe(df)

# Note: display_saved_idle_reports() will be called by the main app when needed
# This prevents database calls during module import
