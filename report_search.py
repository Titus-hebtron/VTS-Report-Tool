import streamlit as st
import pandas as pd
from db_utils import get_sqlalchemy_engine
import calendar
import io
import re

def extract_license_plate(vehicle_string):
    """Extract license plate from vehicle string that may contain contractor name"""
    if not vehicle_string or vehicle_string.lower() in ['unknown', 'unknown vehicle', '']:
        return None

    vehicle_string = vehicle_string.strip()

    # Pattern for Kenyan license plates (e.g., KDG 320Z, KDK 825Y, KDS 374F)
    # Typically: 3 letters, space, 3-4 digits/alphanumerics
    plate_pattern = re.match(r'^([A-Z]{3}\s*\d{1,4}[A-Z]*)\s*(.*)', vehicle_string.upper())

    if plate_pattern:
        return plate_pattern.group(1).replace(' ', '')  # Remove spaces from plate

    # Fallback: try to find any license plate-like pattern
    fallback_pattern = re.search(r'([A-Z]{2,4}\s*\d{1,4}[A-Z]*)', vehicle_string.upper())
    if fallback_pattern:
        return fallback_pattern.group(1).replace(' ', '')

    # If no pattern matches, return the whole string as potential plate
    return vehicle_string.replace(' ', '').upper()

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
            WHERE patrol_car = %s
              AND response_time <= %s
              AND clearing_time >= %s
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
                WHERE vehicle = %s
                  AND break_start <= %s
                  AND (break_end IS NULL OR break_end >= %s)
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
                WHERE vehicle = %s
                  AND pickup_start <= %s
                  AND (pickup_end IS NULL OR pickup_end >= %s)
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
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (vehicle, idle_start, idle_end, idle_duration, uploaded_by, description))
            saved_count += 1
        except Exception as e:
            print(f"❌ Error saving row for {vehicle}: {e}")

    conn.commit()
    cur.close()
    conn.close()
    print(f"✅ Idle report save complete. Rows saved: {saved_count}")

# ---------------------- GET WEEKLY CONSOLIDATED DATA ----------------------
def get_weekly_data(vehicle, week_start, week_end):
    engine = get_sqlalchemy_engine()

    # Get all idle events for the week
    idle_query = """
        SELECT id, vehicle, idle_start, idle_end, idle_duration_min, description
        FROM idle_reports
        WHERE idle_start::date BETWEEN %s AND %s
    """
    idle_df = pd.read_sql_query(idle_query, engine, params=(week_start, week_end))
    if vehicle != "All":
        # Extract license plate from selected vehicle for matching
        selected_plate = extract_license_plate(vehicle)
        if selected_plate:
            # Filter by matching license plates in idle data
            idle_df['extracted_plate'] = idle_df['vehicle'].apply(extract_license_plate)
            idle_df = idle_df[idle_df['extracted_plate'] == selected_plate]
            idle_df = idle_df.drop('extracted_plate', axis=1)
        else:
            # Fallback to original logic if license plate extraction fails
            def normalize(v):
                return v.strip().upper().rstrip('-')
            vehicle_norm = normalize(vehicle)
            idle_df = idle_df[idle_df['vehicle'].apply(normalize) == vehicle_norm]

    if idle_df.empty:
        return pd.DataFrame()

    # Get all incidents, breaks, pickups for the week
    incidents_df = pd.read_sql_query(
        "SELECT * FROM incident_reports WHERE incident_date BETWEEN %s AND %s",
        engine, params=(week_start, week_end)
    )
    breaks_df = pd.read_sql_query(
        "SELECT * FROM breaks WHERE break_date BETWEEN %s AND %s",
        engine, params=(week_start, week_end)
    )
    pickups_df = pd.read_sql_query(
        "SELECT * FROM pickups WHERE pickup_start::date BETWEEN %s AND %s",
        engine, params=(week_start, week_end)
    )

    # --- FILTER BY VEHICLE ---
    if vehicle != "All":
        # Extract license plate from selected vehicle for matching
        selected_plate = extract_license_plate(vehicle)
        if selected_plate:
            # Filter all data sources by matching license plates
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
        else:
            # Fallback to original logic if license plate extraction fails
            def normalize(v):
                return v.strip().upper().rstrip('-')
            vehicle_norm = normalize(vehicle)
            idle_df = idle_df[idle_df['vehicle'].apply(normalize) == vehicle_norm]
            incidents_df = incidents_df[incidents_df['patrol_car'].apply(normalize) == vehicle_norm]
            breaks_df = breaks_df[breaks_df['vehicle'].apply(normalize) == vehicle_norm]
            pickups_df = pickups_df[pickups_df['vehicle'].apply(normalize) == vehicle_norm]

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
            overlaps_inc = ((valid_incidents['response_time'] <= idle_end) & (valid_incidents['clearing_time'] >= idle_start)).any()
            if overlaps_inc:
                idle_df.at[idx, "Incident"] = duration
                continue

        # Breaks check - vectorized
        valid_breaks = breaks_df.copy()
        valid_breaks['break_end'] = valid_breaks['break_end'].fillna(pd.Timestamp.max)
        overlaps_br = ((valid_breaks['break_start'] <= idle_end) & (valid_breaks['break_end'] >= idle_start)).any()
        if overlaps_br:
            idle_df.at[idx, "Breaks"] = duration
            continue

        # Pickups check - vectorized
        valid_pickups = pickups_df.copy()
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
def create_weekly_table_for_excel(df, year, month):
    df['Date'] = pd.to_datetime(df['idle_start']).dt.date
    df['Start'] = pd.to_datetime(df['idle_start']).dt.strftime("%H:%M:%S")
    df['End'] = pd.to_datetime(df['idle_end']).dt.strftime("%H:%M:%S")
    df['Time Diff'] = pd.to_numeric(df['idle_duration_min'], errors='coerce').fillna(0)

    # Ensure breakdown columns are numeric
    for col in ['Incident', 'Breaks', 'Pickups', 'Unjustified']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    cols = ['Date', 'Start', 'End', 'Time Diff', 'Incident', 'Breaks', 'Pickups', 'Unjustified']
    cols = [c for c in cols if c in df.columns]
    cal = calendar.Calendar()
    weeks = cal.monthdatescalendar(year, month)

    output_rows = []
    weekly_percentages = []

    for week_num, week_days in enumerate(weeks, 1):
        output_rows.append([f"=== Week {week_num} ==="] + [""]*(len(cols)-1))

        week_total = {col: 0.0 for col in cols}
        week_total['Date'] = "WEEK TOTAL"

        for day in week_days:
            if day.month != month:
                continue
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
                    'Time Diff': day_df['Time Diff'].sum(),
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
            'Time Diff': "",
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
        'Time Diff': df['Time Diff'].sum(),
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
        'Time Diff': "",
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

    # ------------------- WEEKLY -------------------
    st.subheader("Weekly Report")
    week_start = st.date_input("Select week start date")
    week_end = st.date_input("Select week end date")

    patrol_vehicle_options = ["All", "KDG 320Z", "KDK 825Y", "KDS 374F"]
    selected_vehicle = st.selectbox("Select Patrol Vehicle", patrol_vehicle_options)

    weekly_df = get_weekly_data(selected_vehicle, week_start, week_end)

    if not weekly_df.empty:
        for col in ["Incident", "Breaks", "Pickups", "Unjustified"]:
            if col in weekly_df.columns:
                weekly_df[col] = weekly_df[col].astype(str)

        st.dataframe(weekly_df)

        # Export Weekly
        if st.button("Download Weekly Report"):
            with pd.ExcelWriter("weekly_report.xlsx") as writer:
                weekly_df.to_excel(writer, sheet_name=selected_vehicle, index=False)
            with open("weekly_report.xlsx", "rb") as f:
                st.download_button(
                    label="Download File",
                    data=f,
                    file_name="weekly_report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    else:
        st.info("No idle data found for this vehicle in the selected week.")

    # ------------------- MONTHLY -------------------
    st.subheader("Monthly Consolidated Report (4 Weeks + Grand Total)")

    month = st.date_input("Pick any date in the month for report")
    month_start = pd.to_datetime(month).replace(day=1)
    month_end = (month_start + pd.offsets.MonthEnd(0))

    if st.button("Download Monthly Report"):
        month_name = month_start.strftime('%B_%Y')
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            for vehicle in ["KDG 320Z", "KDK 825Y", "KDS 374F"]:
                df = get_weekly_data(vehicle, month_start, month_end)
                if not df.empty:
                    year = month_start.year
                    month_num = month_start.month
                    export_df = create_weekly_table_for_excel(df, year, month_num)
                    export_df.to_excel(writer, sheet_name=vehicle, index=False, header=True)
                    # Formatting
                    workbook  = writer.book
                    worksheet = writer.sheets[vehicle]
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
                        elif cell_val.startswith("==="):
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

        output.seek(0)
        st.download_button(
            label="Download Monthly Report",
            data=output,
            file_name=f"monthly_report_{month_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

def search_page():
    import streamlit as st
    import pandas as pd
    from db_utils import get_sqlalchemy_engine

    st.header("🔍 Search & View Data")

    search_options = ["Accidents", "Incidents", "Breaks", "Pickups"]
    selected_option = st.selectbox("Select data to view", search_options)

    start_date = st.date_input("Start date")
    end_date = st.date_input("End date")
    vehicle = st.text_input("Vehicle (optional)")

    if st.button("Search"):
        engine = get_sqlalchemy_engine()
        if selected_option == "Accidents":
            query = "SELECT * FROM accidents WHERE accident_date BETWEEN %s AND %s"
            params = (start_date, end_date)
            if vehicle:
                query += " AND vehicle = %s"
                params += (vehicle,)
            df = pd.read_sql_query(query, engine, params=params)
        elif selected_option == "Incidents":
            query = "SELECT * FROM incident_reports WHERE incident_date BETWEEN %s AND %s"
            params = (start_date, end_date)
            if vehicle:
                query += " AND patrol_car = %s"
                params += (vehicle,)
            df = pd.read_sql_query(query, engine, params=params)
        elif selected_option == "Breaks":
            query = "SELECT * FROM breaks WHERE break_date BETWEEN %s AND %s"
            params = (start_date, end_date)
            if vehicle:
                query += " AND vehicle = %s"
                params += (vehicle,)
            df = pd.read_sql_query(query, engine, params=params)
        elif selected_option == "Pickups":
            query = "SELECT * FROM pickups WHERE pickup_start::date BETWEEN %s AND %s"
            params = (start_date, end_date)
            if vehicle:
                query += " AND vehicle = %s"
                params += (vehicle,)
            df = pd.read_sql_query(query, engine, params=params)
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

# ---------------------- RUN APP ----------------------
if __name__ == "__main__":
    report_search_page()
