def fill_incident_template(ws, row):
    from openpyxl.styles import Font, PatternFill
    yellow = PatternFill(start_color='FFFF00', end_color='FFFF00', fill_type='solid')
    # Row 7: Incident Notification Date, Incident Notification Time
    ws['B7'] = 'Incident Notification Date:'
    ws['C7'] = str(row.get('incident_date', ''))
    ws['F7'] = 'Incident Notification Time:'
    ws['G7'] = str(row.get('incident_time', ''))
    ws['C7'].fill = yellow
    ws['G7'].fill = yellow
    # Row 8: Caller, Phone Number
    ws['I8'] = 'Caller:'
    ws['J8'] = str(row.get('caller', ''))
    ws['J8'].fill = yellow
    ws['L8'] = 'Phone Number:'
    ws['M8'] = str(row.get('phone_number', ''))
    ws['M8'].fill = yellow
    # Row 9: Nature of Incident
    ws['B9'] = 'Nature of Incident:'
    nature_text = f"{row.get('incident_type', 'N/A')} - {row.get('description', 'No details provided.')}"
    ws['C9'] = nature_text
    # Row 10: Location, Bound, Chainage
    ws['B10'] = 'Location of Incident :'
    ws['C10'] = str(row.get('location', ''))
    ws['C10'].fill = yellow
    ws['E10'] = 'Bound:'
    ws['F10'] = str(row.get('bound', ''))
    ws['F10'].fill = yellow
    ws['H10'] = 'Chainage:'
    ws['I10'] = str(row.get('chainage', ''))
    ws['I10'].fill = yellow
    # Row 11: Number of Accident Vehicles, Type of Vehicle
    ws['B11'] = 'Number of Accident Vehicles:'
    ws['C11'] = str(row.get('num_vehicles', ''))
    ws['C11'].fill = yellow
    ws['E11'] = 'Type of Vehicle:'
    ws['F11'] = str(row.get('vehicle_type', ''))
    ws['F11'].fill = yellow
    # Row 12: Conditions of Accident Vehicles, Number of Injured People
    ws['B12'] = 'Conditions of Accident Vehicles:'
    vehicle_details = f"Type: {row.get('vehicle_type', 'N/A')} ({row.get('num_vehicles', '1')} unit(s)). Condition: {row.get('vehicle_condition', 'Unknown')}"
    if str(row.get('incident_type', '')).lower() == "accident":
        ws['D12'] = vehicle_details
    else:
        ws['C12'] = vehicle_details
    ws['C12'].fill = yellow
    ws['D12'].fill = yellow
    ws['H12'] = 'Number of Injured People:'
    ws['I12'] = str(row.get('num_injured', ''))
    ws['I12'].fill = yellow
    # Row 13: Conditions of Injured People, The Injured Part
    ws['B13'] = 'Conditions of Injured People:'
    ws['C13'] = str(row.get('cond_injured', ''))
    ws['C13'].fill = yellow
    ws['F13'] = 'The Injured Part:'
    ws['G13'] = str(row.get('injured_part', ''))
    ws['G13'].fill = yellow
    # Row 14: Fire Hazard, Oil Leakage, Chemical Leakage
    ws['B14'] = 'Fire Hazard:'
    ws['C14'] = 'Yes' if row.get('fire_hazard') else 'No'
    ws['C14'].fill = yellow
    ws['E14'] = 'Oil Leakage:'
    ws['F14'] = 'Yes' if row.get('oil_leakage') else 'No'
    ws['F14'].fill = yellow
    ws['H14'] = 'Chemical Leakage:'
    ws['I14'] = 'Yes' if row.get('chemical_leakage') else 'No'
    ws['I14'].fill = yellow
    # Row 15: Damage To Road Furniture
    ws['B15'] = 'Damage To Road Furniture:'
    ws['C15'] = 'Yes' if row.get('damage_road_furniture') else 'No'
    ws['C15'].fill = yellow
    # Row 16: Response Time, Clearing Time
    ws['B16'] = 'Response Time:'
    ws['C16'] = str(row.get('response_time', ''))
    ws['C16'].fill = yellow
    ws['F16'] = 'Clearing Time:'
    ws['G16'] = str(row.get('clearing_time', ''))
    ws['G16'].fill = yellow
    # Formatting: bold for labels
    for row_num in range(7, 17):
        for cell in ws[row_num]:
            if cell.value and isinstance(cell.value, str) and (cell.value.endswith(':') or cell.value in ['Accident', 'Emergency', 'Others']):
                cell.font = Font(bold=True)
    # Auto column width
    for col in ws.columns:
        max_length = 0
        col_letter = col[0].column_letter
        for cell in col:
            try:
                if cell.value and len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        ws.column_dimensions[col_letter].width = max_length + 2

def search_page():
    import streamlit as st
    import pandas as pd
    from db_utils import get_sqlalchemy_engine
    from io import BytesIO
    import openpyxl
    from openpyxl.drawing.image import Image as OpenpyxlImage
    import os
    import tempfile # NEW: For creating temporary image files

    st.header("🔍 Search & View Data")

    search_options = ["Accidents", "Incidents", "Breaks", "Pickups"]
    selected_option = st.selectbox("Select data to view", search_options)

    start_date = st.date_input("Start date").strftime('%Y-%m-%d')
    end_date = st.date_input("End date").strftime('%Y-%m-%d')
    vehicle = st.text_input("Vehicle (optional)")

    if st.button("Search"):
        try:
            engine = get_sqlalchemy_engine()
        except Exception as e:
            st.error(f"❌ ERROR: Could not get database engine. Details: {e}")
            return # Exit if DB connection fails

        df = pd.DataFrame()
        image_df = pd.DataFrame()

        # --- 1. CONSTRUCT QUERY AND FETCH MAIN DATA ---
        if selected_option in ["Accidents", "Incidents"]:
            incident_type = "Accident" if selected_option == "Accidents" else "Incident"
            query = "SELECT * FROM incident_reports WHERE incident_date BETWEEN ? AND ? AND incident_type = ?"
            params = [start_date, end_date, incident_type]

            if vehicle:
                query += " AND patrol_car = ?"
                params.append(vehicle)

            try:
                # Fetch main report data. The 'id' column is the Primary Key.
                with engine.connect() as conn:
                    df = pd.read_sql_query(query, conn, params=params)
            except Exception as e:
                st.error(f"Database error fetching incident data: {e}")


            # --- 2. FETCH IMAGE DATA (BLOBs) FOR LINKING ---
            if not df.empty and 'id' in df.columns: # 'id' is the primary key (PK)
                report_ids = df['id'].tolist()

                # Handling the IN clause parameters
                placeholders = ','.join(['?'] * len(report_ids))

                # Query the image table for BLOB data and metadata
                # Note the change: incident_images table and incident_id column
                image_query = f"SELECT incident_id, image_name, image_data FROM incident_images WHERE incident_id IN ({placeholders})"

                try:
                    # Fetching the BLOB data is slow but necessary for embedding
                    with engine.connect() as conn:
                        image_df = pd.read_sql_query(image_query, conn, params=report_ids)
                    st.success(f"Found {len(df)} reports and {len(image_df)} associated images.")
                except Exception as e:
                    st.warning(f"Could not fetch image data from incident_images table: {e}. Download will be data-only.")

        elif selected_option == "Breaks":
            query = "SELECT * FROM breaks WHERE break_date BETWEEN ? AND ?"
            params = [start_date, end_date]
            if vehicle:
                query += " AND vehicle = ?"
                params.append(vehicle)
            try:
                with engine.connect() as conn:
                    df = pd.read_sql_query(query, conn, params=params)
            except Exception as e:
                st.error(f"Database error fetching breaks data: {e}")

        elif selected_option == "Pickups":
            query = "SELECT * FROM pickups WHERE DATE(pickup_start) BETWEEN ? AND ?"
            params = [start_date, end_date]
            if vehicle:
                query += " AND vehicle = ?"
                params.append(vehicle)
            try:
                with engine.connect() as conn:
                    df = pd.read_sql_query(query, conn, params=params)
            except Exception as e:
                st.error(f"Database error fetching pickups data: {e}")

        # --- 3. DISPLAY AND DOWNLOAD LOGIC ---
        if not df.empty:
            st.dataframe(df)

            # Excel Workbook Download
            output = BytesIO()
            try:
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    if selected_option in ["Accidents", "Incidents"]:
                        # Create a template sheet for each report
                        for index, row in df.iterrows():
                            sheet_name = f"Report_{index+1}"[:31]
                            ws = writer.book.create_sheet(title=sheet_name)
                            fill_incident_template(ws, row)
                    else:
                        # For other options, use column sheets
                        for col in df.columns:
                            sheet_name = col[:31]
                            df[[col]].to_excel(writer, sheet_name=sheet_name, index=False)

                    workbook = writer.book

                    # Embed images if applicable
                    if selected_option in ["Accidents", "Incidents"] and not image_df.empty:
                        with tempfile.TemporaryDirectory() as temp_dir:
                            for index, row in df.iterrows():
                                report_id = row.get('id')
                                if report_id:
                                    sheet_name = f"Report_{index+1}"[:31]
                                    ws = writer.sheets[sheet_name]

                                    linked_images = image_df[image_df['incident_id'] == report_id]

                                    if not linked_images.empty:
                                        current_row = 19  # Below the template
                                        ws.cell(row=current_row, column=1, value=f"--- IMAGES FOR REPORT ID: {report_id} ---").font = openpyxl.styles.Font(bold=True)
                                        current_row += 1

                                        for img_index, img_row in linked_images.iterrows():
                                            img_data_blob = img_row['image_data']
                                            img_name = img_row['image_name']

                                            file_ext = img_name.split('.')[-1] if '.' in img_name else 'png'

                                            temp_file_path = os.path.join(temp_dir, f"{report_id}_{img_index}.{file_ext}")
                                            with open(temp_file_path, 'wb') as f:
                                                f.write(img_data_blob)

                                            img = OpenpyxlImage(temp_file_path)
                                            img.anchor = f'A{current_row}'
                                            img.width = 300
                                            img.height = 200
                                            ws.add_image(img)

                                            current_row += 15

                                        current_row += 2

                # --- DOWNLOAD BUTTON FOR EXCEL WORKBOOK ---
                st.download_button(
                    label="⬇️ Download Excel Workbook",
                    data=output.getvalue(),
                    file_name=f"{selected_option.lower()}_results_workbook.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

            except Exception as e:
                st.error(f"Error creating Excel workbook: {e}")
                st.warning("Ensure all data is valid and required libraries are installed.")

            # CSV Download
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="⬇️ Download Data as CSV",
                data=csv,
                file_name=f"{selected_option.lower()}_results.csv",
                mime="text/csv"
            )
        else:
            st.info("No data found for your search.")
