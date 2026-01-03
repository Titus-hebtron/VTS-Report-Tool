import streamlit as st
import pandas as pd
from db_utils import get_sqlalchemy_engine, get_contractor_name
from sqlalchemy import text
import calendar
import io
import re

def extract_license_plate(vehicle_string):
    """Extract standardized license plate from vehicle string, normalizing variations"""
    if not vehicle_string or vehicle_string.lower() in ['unknown', 'unknown vehicle', '']:
        return None

    # Clean the string: remove extra whitespace, newlines, tabs, quotes, and special chars
    vehicle_string = re.sub(r'[\s\t\n\r"\'-]+', ' ', vehicle_string.strip())

    # Primary pattern: 3 letters + space + 3-4 digits + optional letter (e.g., "KDK 825Y")
    plate_pattern = re.search(r'\b([A-Z]{3}\s+\d{3,4}[A-Z]?)\b', vehicle_string.upper())
    if plate_pattern:
        plate = plate_pattern.group(1)
        # Normalize spacing (ensure single space between letters and numbers)
        plate = re.sub(r'\s+', ' ', plate)
        return plate

    # Secondary pattern: 3 letters + 3-4 digits + optional letter (no space, may have company name after)
    # This handles cases like "KDG320ZWIZPROENTERPRISESLTD" -> "KDG320Z"
    compact_pattern = re.search(r'\b([A-Z]{3}\d{3,4}[A-Z]?)(?:[A-Z]*)*\b', vehicle_string.upper())
    if compact_pattern:
        plate = compact_pattern.group(1)
        # Add space between letters and numbers for consistency
        plate = re.sub(r'([A-Z]{3})(\d)', r'\1 \2', plate)
        return plate

    # Fallback: any license plate-like pattern
    fallback_pattern = re.search(r'\b([A-Z]{2,4}\s*\d{1,4}[A-Z]*)\b', vehicle_string.upper())
    if fallback_pattern:
        plate = fallback_pattern.group(1)
        # Normalize spacing
        plate = re.sub(r'\s+', ' ', plate).strip()
        return plate

    # Last resort: clean and return as-is
    return re.sub(r'[^\w]', '', vehicle_string.upper())

# ---------------------- SAVE IDLE WITH DESCRIPTION ----------------------
def save_idle_report(idle_df, uploaded_by, engine):
    import pandas as pd

    conn = engine.raw_connection()
    cur = conn.cursor()
    saved_count = 0

    for _, row in idle_df.iterrows():
        vehicle = row['Vehicle']
        idle_start = pd.to_datetime(row['Idle Start'])
        idle_end = pd.to_datetime(row['Idle End'])
        idle_duration = row['Idle Duration (min)']

        description = None

        # --- INCIDENTS ---
        cur.execute("""
            SELECT description
            FROM incident_reports
            WHERE patrol_car = ?
              AND response_time <= ?
              AND clearing_time >= ?
            LIMIT 1
        """, (vehicle, idle_start, idle_end))
        inc = cur.fetchone()
        if inc:
            description = inc[0]

        # --- BREAKS ---
        if not description:
            cur.execute("""
                SELECT reason
                FROM breaks
                WHERE vehicle = ?
                  AND break_start <= ?
                  AND (break_end IS NULL OR break_end >= ?)
                LIMIT 1
            """, (vehicle, idle_start, idle_end))
            br = cur.fetchone()
            if br:
                description = br[0]

        # --- PICKUPS ---
        if not description:
            cur.execute("""
                SELECT description
                FROM pickups
                WHERE vehicle = ?
                  AND pickup_start <= ?
                  AND (pickup_end IS NULL OR pickup_end >= ?)
                LIMIT 1
            """, (vehicle, idle_start, idle_end))
            pk = cur.fetchone()
            if pk:
                description = pk[0]

        # --- UNJUSTIFIED ---
        if not description:
            description = f"Unjustified Idle: {idle_duration} minutes"

        try:
            cur.execute("""
                INSERT INTO idle_reports (vehicle, idle_start, idle_end, idle_duration_min, uploaded_by, description)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (vehicle, idle_start, idle_end, idle_duration, uploaded_by, description))
            saved_count += 1
        except Exception as e:
            print(f"❌ Error saving row for {vehicle}: {e}")

    conn.commit()
    cur.close()
    conn.close()
    print(f"✅ Idle report save complete. Rows saved: {saved_count}")

# ---------------------- GET WEEKLY CONSOLIDATED DATA ----------------------
def get_weekly_data(vehicle, week_start, week_end, contractor_id=None):
    engine = get_sqlalchemy_engine()

    # Get contractor name for breaks/pickups filtering (they store contractor name, not ID)
    contractor_name = get_contractor_name(contractor_id) if contractor_id else None

    # Get all idle events for the week
    idle_query = """
        SELECT id, vehicle, idle_start, idle_end, idle_duration_min, description, location_address
        FROM idle_reports
        WHERE DATE(idle_start) BETWEEN :start_date AND :end_date
    """
    params = {
        "start_date": week_start.strftime('%Y-%m-%d'),
        "end_date": week_end.strftime('%Y-%m-%d')
    }
    if contractor_id:
        idle_query += " AND contractor_id = :contractor_id"
        params["contractor_id"] = contractor_id
    with engine.connect() as conn:
        idle_df = pd.read_sql_query(text(idle_query), conn, params=params)

    # Filter for idle periods over 5 minutes
    idle_df = idle_df[idle_df['idle_duration_min'] > 5]

    if vehicle != "All":
        selected_plate = extract_license_plate(vehicle)
        if selected_plate:
            idle_df['extracted_plate'] = idle_df['vehicle'].apply(extract_license_plate)
            idle_df = idle_df[idle_df['extracted_plate'] == selected_plate]
            idle_df = idle_df.drop('extracted_plate', axis=1)

    if idle_df.empty:
        return pd.DataFrame()

    # Get all incidents, breaks, pickups for the week
    inc_query = "SELECT * FROM incident_reports WHERE incident_date BETWEEN :start_date AND :end_date"
    br_query = "SELECT * FROM breaks WHERE break_date BETWEEN :start_date AND :end_date"
    pk_query = "SELECT * FROM pickups WHERE DATE(pickup_start) BETWEEN :start_date AND :end_date"
    inc_params = {"start_date": week_start.strftime('%Y-%m-%d'), "end_date": week_end.strftime('%Y-%m-%d')}
    br_params = inc_params.copy()
    pk_params = inc_params.copy()
    if contractor_id:
        inc_query += " AND contractor_id = :contractor_id"
        inc_params["contractor_id"] = contractor_id
        br_query += " AND contractor_id = :contractor_id"
        br_params["contractor_id"] = contractor_id
        pk_query += " AND contractor_id = :contractor_id"
        pk_params["contractor_id"] = contractor_id
    with engine.connect() as conn:
        incidents_df = pd.read_sql_query(text(inc_query), conn, params=inc_params)
        breaks_df = pd.read_sql_query(text(br_query), conn, params=br_params)
        pickups_df = pd.read_sql_query(text(pk_query), conn, params=pk_params)

    # --- FILTER BY VEHICLE ---
    if vehicle != "All":
        selected_plate = extract_license_plate(vehicle)
        if selected_plate:
            idle_df['extracted_plate'] = idle_df['vehicle'].apply(extract_license_plate)
            idle_df = idle_df[idle_df['extracted_plate'] == selected_plate]
            idle_df = idle_df.drop('extracted_plate', axis=1)
            incidents_df['extracted_plate'] = incidents_df['patrol_car'].apply(extract_license_plate)
            incidents_df = incidents_df[incidents_df['extracted_plate'] == selected_plate]
            incidents_df = incidents_df.drop('extracted_plate', axis=1)
            breaks_df['extracted_plate'] = breaks_df['vehicle'].apply(extract_license_plate)
            breaks_df = breaks_df[breaks_df['extracted_plate'] == selected_plate]
            breaks_df = breaks_df.drop('extracted_plate', axis=1)
            pickups_df['extracted_plate'] = pickups_df['vehicle'].apply(extract_license_plate)
            pickups_df = pickups_df[pickups_df['extracted_plate'] == selected_plate]
            pickups_df = pickups_df.drop('extracted_plate', axis=1)

    # Prepare columns as numeric
    idle_df["Incident"] = 0.0
    idle_df["Breaks"] = 0.0
    idle_df["Pickups"] = 0.0
    idle_df["Unjustified"] = 0.0

    # Vectorized overlap checks
    for idx, idle_row in idle_df.iterrows():
        idle_start = pd.to_datetime(idle_row['idle_start'])
        idle_end = pd.to_datetime(idle_row['idle_end'])
        duration = idle_row['idle_duration_min']

        # Incident check - vectorized
        valid_incidents = incidents_df.dropna(subset=['response_time', 'clearing_time'])
        if not valid_incidents.empty:
            valid_incidents['response_time'] = pd.to_datetime(valid_incidents['response_time'], errors='coerce')
            valid_incidents['clearing_time'] = pd.to_datetime(valid_incidents['clearing_time'], errors='coerce')
            valid_incidents = valid_incidents.dropna(subset=['response_time', 'clearing_time'])
            if not valid_incidents.empty:
                overlaps_inc = ((valid_incidents['response_time'] <= idle_end) & (valid_incidents['clearing_time'] >= idle_start)).any()
                if overlaps_inc:
                    idle_df.at[idx, "Incident"] = duration
                    continue

        # Breaks check - vectorized
        valid_breaks = breaks_df.copy()
        valid_breaks['break_start'] = pd.to_datetime(valid_breaks['break_start'], errors='coerce')
        valid_breaks['break_end'] = pd.to_datetime(valid_breaks['break_end'], errors='coerce')
        valid_breaks = valid_breaks.dropna(subset=['break_start'])
        if not valid_breaks.empty:
            valid_breaks['break_end'] = valid_breaks['break_end'].fillna(pd.Timestamp.max)
            overlaps_br = ((valid_breaks['break_start'] <= idle_end) & (valid_breaks['break_end'] >= idle_start)).any()
            if overlaps_br:
                idle_df.at[idx, "Breaks"] = duration
                continue

        # Pickups check - vectorized
        valid_pickups = pickups_df.copy()
        valid_pickups['pickup_start'] = pd.to_datetime(valid_pickups['pickup_start'], errors='coerce')
        valid_pickups['pickup_end'] = pd.to_datetime(valid_pickups['pickup_end'], errors='coerce')
        valid_pickups = valid_pickups.dropna(subset=['pickup_start'])
        if not valid_pickups.empty:
            valid_pickups['pickup_end'] = valid_pickups['pickup_end'].fillna(pd.Timestamp.max)
            overlaps_pk = ((valid_pickups['pickup_start'] <= idle_end) & (valid_pickups['pickup_end'] >= idle_start)).any()
            if overlaps_pk:
                idle_df.at[idx, "Pickups"] = duration
                continue

        # Unjustified
        idle_df.at[idx, "Unjustified"] = duration

    # Ensure all breakdown columns are numeric
    for col in ["Incident", "Breaks", "Pickups", "Unjustified"]:
        idle_df[col] = pd.to_numeric(idle_df[col], errors='coerce').fillna(0)

    return idle_df

# ---------------------- MONTHLY EXCEL BUILDER ----------------------
def create_weekly_table_for_excel(df, start_date, include_location=True):
    df['Date'] = pd.to_datetime(df['idle_start']).dt.date
    df['Start'] = pd.to_datetime(df['idle_start']).dt.strftime("%H:%M:%S")
    df['End'] = pd.to_datetime(df['idle_end']).dt.strftime("%H:%M:%S")
    df['Time Diff'] = pd.to_numeric(df['idle_duration_min'], errors='coerce').fillna(0)
    df['Location'] = df['location_address']

    # Ensure breakdown columns are numeric
    for col in ['Incident', 'Breaks', 'Pickups', 'Unjustified']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    if include_location:
        cols = ['Date', 'Start', 'End', 'Time Diff', 'Location', 'Incident', 'Breaks', 'Pickups', 'Unjustified']
    else:
        cols = ['Date', 'Start', 'End', 'Time Diff', 'Incident', 'Breaks', 'Pickups', 'Unjustified']
    cols = [c for c in cols if c in df.columns]

    output_rows = []
    weekly_percentages = []

    for week_num in range(1, 5):
        output_rows.append([f"Week {week_num}"] + [""]*(len(cols)-1))

        week_total = {col: 0.0 for col in cols if col not in ['Date', 'Start', 'End', 'Location']}
        week_total.update({'Date': "WEEK TOTAL", 'Start': "", 'End': "", 'Location': ""})

        week_start = pd.to_datetime(start_date) + pd.Timedelta(days=(week_num-1)*7)
        week_days = [(week_start + pd.Timedelta(days=i)).date() for i in range(7)]

        for day in week_days:
            day_df = df[df['Date'] == day].copy()
            if not day_df.empty:
                output_rows.append([str(day)] + [""]*(len(cols)-1))
                for col in ['Time Diff', 'Incident', 'Breaks', 'Pickups', 'Unjustified']:
                    day_df[col] = pd.to_numeric(day_df[col], errors='coerce').fillna(0)
                for _, row in day_df.iterrows():
                    output_rows.append([row.get(col, "") for col in cols])
                # Day total (in minutes)
                day_total = {
                    'Date': "DAY TOTAL",
                    'Start': "",
                    'End': "",
                    'Time Diff': day_df['Time Diff'].sum(),
                    'Location': "",
                    'Incident': day_df['Incident'].sum(),
                    'Breaks': day_df['Breaks'].sum(),
                    'Pickups': day_df['Pickups'].sum(),
                    'Unjustified': day_df['Unjustified'].sum()
                }
                output_rows.append([day_total.get(col, "") for col in cols])
                # Add to week total
                for key in ['Time Diff', 'Incident', 'Breaks', 'Pickups', 'Unjustified']:
                    week_total[key] += day_total[key]
                output_rows.extend([[""]*len(cols)]*2)

        # Weekly total (in minutes)
        output_rows.append([week_total.get(col, "") for col in cols])

        # Weekly percentage availability (in minutes)
        breaks_unjustified = week_total.get('Breaks', 0) + week_total.get('Unjustified', 0)
        percent_avail = (1 - (breaks_unjustified / 10080)) * 100 if week_total.get('Time Diff', 0) > 0 else 0
        weekly_percentages.append(percent_avail)
        percent_row = {
            'Date': "Availability (%)",
            'Start': "",
            'End': "",
            'Time Diff': "",
            'Location': "",
            'Incident': "",
            'Breaks': "",
            'Pickups': "",
            'Unjustified': f"{percent_avail:.2f}%"
        }
        output_rows.append([percent_row.get(col, "") for col in cols])

        output_rows.extend([[""]*len(cols)]*4)

    # Grand monthly total (in minutes)
    for col in ['Time Diff', 'Incident', 'Breaks', 'Pickups', 'Unjustified']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    monthly_totals = {
        'Date': "GRAND MONTHLY TOTAL",
        'Start': "",
        'End': "",
        'Time Diff': df['Time Diff'].sum(),
        'Location': "",
        'Incident': df['Incident'].sum(),
        'Breaks': df['Breaks'].sum(),
        'Pickups': df['Pickups'].sum(),
        'Unjustified': df['Unjustified'].sum()
    }
    output_rows.append([monthly_totals.get(col, "") for col in cols])

    # Monthly overall percentage
    if weekly_percentages:
        month_percent = sum(weekly_percentages) / len(weekly_percentages)
    else:
        month_percent = 0
    month_percent_row = {
        'Date': "Monthly Availability (%)",
        'Start': "",
        'End': "",
        'Time Diff': "",
        'Location': "",
        'Incident': "",
        'Breaks': "",
        'Pickups': "",
        'Unjustified': f"{month_percent:.2f}%"
    }
    output_rows.append([month_percent_row.get(col, "") for col in cols])

    final_df = pd.DataFrame(output_rows, columns=cols)
    return final_df

# ---------------------- STREAMLIT UI ----------------------
def report_search_page():
    st.header("📊 Final Consolidated Weekly & Monthly Report")

    engine = get_sqlalchemy_engine()

    # Get contractors for selection
    contractor_query = "SELECT DISTINCT contractor_id FROM idle_reports WHERE contractor_id IS NOT NULL ORDER BY contractor_id"
    with engine.connect() as conn:
        contractor_df = pd.read_sql_query(contractor_query, conn)
    contractor_options = contractor_df['contractor_id'].tolist()
    if not contractor_options:
        st.error("No contractors found.")
        return
    selected_contractor = st.selectbox("Select Contractor", contractor_options, key="contractor_select")
    contractor_id = selected_contractor

    # Get available date range
    try:
        date_query = "SELECT DATE(MIN(idle_start)) as min_date, DATE(MAX(idle_start)) as max_date FROM idle_reports"
        params = {}
        if contractor_id:
            date_query += " WHERE contractor_id = :contractor_id"
            params["contractor_id"] = contractor_id
        with engine.connect() as conn:
            if params:
                date_df = pd.read_sql_query(text(date_query), conn, params=params)
            else:
                date_df = pd.read_sql_query(date_query, conn)
        if not date_df.empty and date_df.iloc[0]['min_date'] is not None:
            min_date = date_df.iloc[0]['min_date']
            max_date = date_df.iloc[0]['max_date']
            st.info(f"Available idle report data from {min_date} to {max_date}")
        else:
            st.warning("No idle report data found for the selected contractor.")
    except Exception as e:
        st.error(f"Error fetching date range: {e}")

    # ------------------- WEEKLY -------------------
    st.subheader("Weekly Report")
    week_start = st.date_input("Select week start date")
    week_end = st.date_input("Select week end date")

    # Get available vehicles (normalized license plates)
    with engine.connect() as conn:
        if contractor_id:
            vehicle_options_query = "SELECT DISTINCT vehicle FROM idle_reports WHERE contractor_id = :contractor_id"
            vehicle_options_df = pd.read_sql_query(text(vehicle_options_query), conn, params={"contractor_id": contractor_id})
        else:
            vehicle_options_query = "SELECT DISTINCT vehicle FROM idle_reports"
            vehicle_options_df = pd.read_sql_query(vehicle_options_query, conn)

    # Normalize vehicle names to license plates for consistent grouping
    vehicle_options_df['normalized_plate'] = vehicle_options_df['vehicle'].apply(extract_license_plate)
    unique_plates = vehicle_options_df['normalized_plate'].dropna().unique()
    patrol_vehicle_options = ["All"] + sorted(list(unique_plates))

    st.write(f"Debug: Contractor ID = {contractor_id}, Vehicles = {patrol_vehicle_options}")
    selected_vehicle = st.selectbox("Select Patrol Vehicle", patrol_vehicle_options)

    weekly_df = get_weekly_data(selected_vehicle, week_start, week_end, contractor_id)

    if not weekly_df.empty:
        for col in ["Incident", "Breaks", "Pickups", "Unjustified"]:
            if col in weekly_df.columns:
                weekly_df[col] = weekly_df[col].astype(str)

        st.dataframe(weekly_df)

        # Export Weekly
        if st.button("Generate Weekly Report"):
            with pd.ExcelWriter("weekly_report.xlsx") as writer:
                weekly_df.to_excel(writer, sheet_name=selected_vehicle, index=False)
            with open("weekly_report.xlsx", "rb") as f:
                st.download_button(
                    label="Download Report",
                    data=f,
                    file_name="weekly_report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    else:
        st.info("No idle data found for this vehicle in the selected week.")

    # ------------------- MONTHLY -------------------
    st.subheader("Monthly Consolidated Report (4 Weeks + Grand Total)")

    start_date = st.date_input("Select start date for 4-week period")

    if st.button("Generate Monthly Report"):
        period_end = start_date + pd.Timedelta(days=27)
        period_name = f"{start_date.strftime('%Y-%m-%d')}_to_{period_end.strftime('%Y-%m-%d')}"
        output = io.BytesIO()
        # Get list of all unique license plates for the contractor (normalized)
        vehicle_query = "SELECT DISTINCT vehicle FROM idle_reports WHERE contractor_id = :contractor_id"
        params = {"contractor_id": contractor_id}
        with engine.connect() as conn:
            vehicles_df = pd.read_sql_query(text(vehicle_query), conn, params=params)

        # Normalize to license plates and get unique ones
        vehicles_df['normalized_plate'] = vehicles_df['vehicle'].apply(extract_license_plate)
        unique_plates = vehicles_df['normalized_plate'].dropna().unique()
        vehicles = sorted(list(unique_plates))

        if not vehicles:
            st.warning("No vehicles with idle data found in the selected period.")
            return

        summaries = []
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            for vehicle in vehicles:
                df = get_weekly_data(vehicle, start_date, period_end, contractor_id)
                if not df.empty:
                    export_df = create_weekly_table_for_excel(df, start_date, include_location=False)

                    # Extract weekly data for summary
                    vehicle_summary = {'Vehicle': vehicle}

                    # Extract data for each week by parsing the export_df structure
                    week_sections = []
                    current_week = None

                    for idx, row in export_df.iterrows():
                        date_val = str(row['Date'])
                        if date_val.startswith('Week '):
                            current_week = int(date_val.split()[1])
                            week_sections.append({'week': current_week, 'start_idx': idx})
                        elif date_val == 'WEEK TOTAL' and current_week:
                            week_sections[-1]['total_idx'] = idx
                        elif date_val == 'Availability (%)' and current_week:
                            week_sections[-1]['avail_idx'] = idx

                    # Extract data for each week
                    for week_info in week_sections:
                        week_num = week_info['week']

                        # Get week total data
                        if 'total_idx' in week_info:
                            total_data = export_df.iloc[week_info['total_idx']]
                            vehicle_summary[f'Week {week_num} Total (min)'] = float(total_data.get('Time Diff', 0))
                            vehicle_summary[f'Week {week_num} Incident (min)'] = float(total_data.get('Incident', 0))
                            vehicle_summary[f'Week {week_num} Breaks (min)'] = float(total_data.get('Breaks', 0))
                            vehicle_summary[f'Week {week_num} Pickups (min)'] = float(total_data.get('Pickups', 0))
                            vehicle_summary[f'Week {week_num} Unjustified (min)'] = float(total_data.get('Unjustified', 0))

                        # Get week availability percentage
                        if 'avail_idx' in week_info:
                            avail_data = export_df.iloc[week_info['avail_idx']]
                            avail_pct_str = str(avail_data.get('Unjustified', '0%')).replace('%', '')
                            try:
                                vehicle_summary[f'Week {week_num} Availability %'] = float(avail_pct_str)
                            except:
                                vehicle_summary[f'Week {week_num} Availability %'] = 0.0

                    # Extract monthly data
                    monthly_row = export_df[export_df['Date'] == "Monthly Availability (%)"]
                    grand_row = export_df[export_df['Date'] == "GRAND MONTHLY TOTAL"]
                    if not monthly_row.empty and not grand_row.empty:
                        monthly_pct_str = monthly_row['Unjustified'].values[0]
                        monthly_pct = float(monthly_pct_str.replace('%', ''))
                        incident_min = float(grand_row['Incident'].values[0])
                        breaks_min = float(grand_row['Breaks'].values[0])
                        pickups_min = float(grand_row['Pickups'].values[0])
                        unjustified_min = float(grand_row['Unjustified'].values[0])

                        vehicle_summary.update({
                            'Monthly Availability %': monthly_pct,
                            'Total Incident (min)': incident_min,
                            'Total Breaks (min)': breaks_min,
                            'Total Pickups (min)': pickups_min,
                            'Total Unjustified (min)': unjustified_min
                        })

                    # Vehicle name is already normalized license plate, clean for Excel worksheet (must be <= 31 chars)
                    clean_vehicle_name = vehicle.replace('"', '').strip()
                    if len(clean_vehicle_name) > 31:
                        # Truncate and add ellipsis if too long
                        clean_vehicle_name = clean_vehicle_name[:28] + "..."

                    summaries.append(vehicle_summary)
                    export_df.to_excel(writer, sheet_name=clean_vehicle_name, index=False, header=True)
                    # Formatting
                    workbook  = writer.book
                    worksheet = writer.sheets[clean_vehicle_name]
                    header_fmt = workbook.add_format({
                        'font_name': 'Arial Narrow', 'font_size': 16,
                        'bold': True, 'align': 'center', 'font_color': 'blue'
                    })
                    day_total_fmt = workbook.add_format({
                        'font_name': 'Calisto MT', 'font_size': 12,
                        'font_color': 'red', 'bold': True
                    })
                    week_total_fmt = workbook.add_format({
                        'font_name': 'Calisto MT', 'font_size': 12,
                        'font_color': 'red', 'bold': True
                    })
                    grand_fmt = workbook.add_format({
                        'font_name': 'Arial Black', 'font_size': 14,
                        'font_color': 'blue', 'bold': True
                    })
                    percent_fmt = workbook.add_format({
                        'font_name': 'Arial Black', 'font_size': 14,
                        'font_color': 'blue', 'bold': True
                    })
                    normal_fmt = workbook.add_format({'font_size': 12})

                    # Write header row manually with formatting
                    for col_num, col_name in enumerate(export_df.columns):
                        worksheet.write(0, col_num, col_name, header_fmt)

                    # Apply formatting to rows
                    for row_idx, row in export_df.iterrows():
                        cell_val = str(row['Date'])
                        # Grand monthly total
                        if cell_val.startswith("GRAND MONTHLY TOTAL"):
                            worksheet.set_row(row_idx+1, None, grand_fmt)
                        # Weekly total
                        elif cell_val.startswith("WEEK TOTAL"):
                            worksheet.set_row(row_idx+1, None, week_total_fmt)
                        # Day total
                        elif cell_val.startswith("DAY TOTAL"):
                            worksheet.set_row(row_idx+1, None, day_total_fmt)
                        # Week header
                        elif cell_val.startswith("Week "):
                            worksheet.set_row(row_idx+1, None, header_fmt)
                        # Percent rows
                        elif cell_val.endswith("Availability (%)") or cell_val.startswith("Monthly Availability (%)"):
                            worksheet.set_row(row_idx+1, None, percent_fmt)
                        else:
                            worksheet.set_row(row_idx+1, None, normal_fmt)
                    # Adjust column widths
                    for i, col in enumerate(export_df.columns):
                        max_length = max(export_df[col].astype(str).map(len).max(), len(col))
                        worksheet.set_column(i, i, max_length + 2)

            # Add Summary sheet
            if summaries:
                summary_df = pd.DataFrame(summaries)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
                # Formatting for summary
                workbook = writer.book
                summary_worksheet = writer.sheets['Summary']
                summary_fmt = workbook.add_format({
                    'font_name': 'Arial', 'font_size': 12,
                    'bold': True, 'align': 'center'
                })
                header_fmt = workbook.add_format({
                    'font_name': 'Arial', 'font_size': 10,
                    'bold': True, 'align': 'center', 'text_wrap': True
                })

                for col_num, col_name in enumerate(summary_df.columns):
                    summary_worksheet.write(0, col_num, col_name, header_fmt)

                # Set column widths - adjust for many more columns
                summary_worksheet.set_column(0, 0, 12)  # Vehicle
                summary_worksheet.set_column(1, 4, 10)  # Week 1 totals
                summary_worksheet.set_column(5, 8, 10)  # Week 2 totals
                summary_worksheet.set_column(9, 12, 10) # Week 3 totals
                summary_worksheet.set_column(13, 16, 10) # Week 4 totals
                summary_worksheet.set_column(17, 21, 12) # Monthly totals

                # Add pie charts for each vehicle - positioned centrally below the data
                chart_row = len(summary_df) + 2  # Start charts below the data

                for i, summary in enumerate(summaries, start=1):
                    # Create pie chart for time breakdown (Incident, Breaks, Pickups, Unjustified)
                    chart = workbook.add_chart({'type': 'pie'})
                    chart.add_series({
                        'name': f'{summary["Vehicle"]} Time Breakdown',
                        'categories': ['Summary', 0, 4, 0, 7],  # Incident, Breaks, Pickups, Unjustified columns
                        'values': ['Summary', i, 4, i, 7],      # Data row i, columns 4-7
                        'data_labels': {'percentage': True, 'position': 'outside_end', 'font_size': 10}
                    })
                    chart.set_title({'name': f'{summary["Vehicle"]} Idle Time Breakdown'})
                    chart.set_size({'width': 350, 'height': 250})
                    chart.set_legend({'position': 'bottom'})

                    # Position charts in a grid layout (2 charts per row)
                    charts_per_row = 2
                    row_offset = (i - 1) // charts_per_row
                    col_offset = (i - 1) % charts_per_row

                    # Column positions: H and P (columns 7 and 15 in Excel)
                    col_positions = ['H', 'P']
                    start_row = chart_row + (row_offset * 20)  # 20 rows spacing between chart rows

                    summary_worksheet.insert_chart(f'{col_positions[col_offset]}{start_row}', chart)

        output.seek(0)
        st.download_button(
            label="Download Report",
            data=output,
            file_name=f"monthly_report_{period_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

def search_page():
    import streamlit as st
    import pandas as pd
    from db_utils import get_sqlalchemy_engine, get_contractor_name, get_active_contractor

    st.header("🔍 Search & View Data")

    search_options = ["Accidents", "Incidents", "Breaks", "Pickups"]
    selected_option = st.selectbox("Select data to view", search_options)

    start_date = st.date_input("Start date")
    end_date = st.date_input("End date")
    vehicle = st.text_input("Vehicle (optional)")

    # Get current contractor for filtering
    contractor_id = get_active_contractor()

    if st.button("Search"):
        try:
            engine = get_sqlalchemy_engine()
            with engine.connect() as conn:
                if selected_option == "Accidents":
                    query = "SELECT * FROM accidents WHERE accident_date BETWEEN :start_date AND :end_date"
                    params = {"start_date": start_date.strftime('%Y-%m-%d'), "end_date": end_date.strftime('%Y-%m-%d')}
                    if contractor_id:
                        query += " AND contractor_id = :contractor_id"
                        params["contractor_id"] = contractor_id
                    if vehicle:
                        query += " AND vehicle = :vehicle"
                        params["vehicle"] = vehicle
                    df = pd.read_sql_query(text(query), conn, params=params)
                elif selected_option == "Incidents":
                    query = "SELECT * FROM incident_reports WHERE incident_date BETWEEN :start_date AND :end_date"
                    params = {"start_date": start_date.strftime('%Y-%m-%d'), "end_date": end_date.strftime('%Y-%m-%d')}
                    if contractor_id:
                        query += " AND contractor_id = :contractor_id"
                        params["contractor_id"] = contractor_id
                    if vehicle:
                        query += " AND patrol_car = :vehicle"
                        params["vehicle"] = vehicle
                    df = pd.read_sql_query(text(query), conn, params=params)
                elif selected_option == "Breaks":
                    query = "SELECT * FROM breaks WHERE break_date BETWEEN :start_date AND :end_date"
                    params = {"start_date": start_date.strftime('%Y-%m-%d'), "end_date": end_date.strftime('%Y-%m-%d')}
                    if contractor_id:
                        query += " AND contractor_id = :contractor_id"
                        params["contractor_id"] = contractor_id
                    if vehicle:
                        query += " AND vehicle = :vehicle"
                        params["vehicle"] = vehicle
                    df = pd.read_sql_query(text(query), conn, params=params)
                elif selected_option == "Pickups":
                    query = "SELECT * FROM pickups WHERE DATE(pickup_start) BETWEEN :start_date AND :end_date"
                    params = {"start_date": start_date.strftime('%Y-%m-%d'), "end_date": end_date.strftime('%Y-%m-%d')}
                    if contractor_id:
                        query += " AND contractor_id = :contractor_id"
                        params["contractor_id"] = contractor_id
                    if vehicle:
                        query += " AND vehicle = :vehicle"
                        params["vehicle"] = vehicle
                    df = pd.read_sql_query(text(query), conn, params=params)
                else:
                    df = pd.DataFrame()

            if not df.empty:
                st.dataframe(df)
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Results as CSV",
                    data=csv,
                    file_name=f"{selected_option.lower()}_results.csv",
                    mime="text/csv"
                )
            else:
                st.info("No data found for your search.")
        except Exception as e:
            st.error(f"Database error fetching {selected_option.lower()} data: {e}")
    else:
        st.info("Click 'Search' to fetch data.")

# ---------------------- RUN APP ----------------------
if __name__ == "__main__":
    report_search_page()
