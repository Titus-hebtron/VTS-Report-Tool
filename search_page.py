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
                df = pd.read_sql_query(query, engine, params=params)
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
                    image_df = pd.read_sql_query(image_query, engine, params=report_ids)
                    st.success(f"Found {len(df)} reports and {len(image_df)} associated images.")
                except Exception as e:
                    st.warning(f"Could not fetch image data from incident_images table: {e}. Download will be data-only.")

        elif selected_option == "Breaks":
            query = "SELECT * FROM breaks WHERE break_date BETWEEN ? AND ?"
            params = (start_date, end_date)
            if vehicle:
                query += " AND vehicle = ?"
                params = params + (vehicle,)
            try:
                df = pd.read_sql_query(query, engine, params=params)
            except Exception as e:
                st.error(f"Database error fetching breaks data: {e}")

        elif selected_option == "Pickups":
            query = "SELECT * FROM pickups WHERE DATE(pickup_start) BETWEEN ? AND ?"
            params = (start_date, end_date)
            if vehicle:
                query += " AND vehicle = ?"
                params = params + (vehicle,)
            try:
                df = pd.read_sql_query(query, engine, params=params)
            except Exception as e:
                st.error(f"Database error fetching pickups data: {e}")

        # --- 3. DISPLAY AND DOWNLOAD LOGIC ---
        if not df.empty:
            st.dataframe(df)

            # Only offer Excel download with images for Accidents/Incidents and if images exist
            if selected_option in ["Accidents", "Incidents"] and not image_df.empty:

                # Use a temporary directory for images required by openpyxl
                with tempfile.TemporaryDirectory() as temp_dir:
                    output = BytesIO()

                    try:
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            # 1. Write the DataFrame to the sheet first
                            df.to_excel(writer, index=False, sheet_name=selected_option)

                            workbook = writer.book
                            worksheet = writer.sheets[selected_option]

                            # Start writing pictures a few rows below the data table
                            current_row = len(df) + 3

                            # 2. Iterate through each incident report row
                            for index, row in df.iterrows():
                                report_id = row.get('id') # Use the PK 'id' for linking
                                if not report_id:
                                    continue

                                # Filter images for the current report (using incident_id foreign key)
                                linked_images = image_df[image_df['incident_id'] == report_id]

                                if not linked_images.empty:
                                    # Write separator/header for the images
                                    worksheet.cell(row=current_row, column=1, value=f"--- IMAGES FOR REPORT ID: {report_id} ---").font = openpyxl.styles.Font(bold=True)
                                    current_row += 1

                                    # 3. Embed the pictures
                                    for img_index, img_row in linked_images.iterrows():
                                        img_data_blob = img_row['image_data']
                                        img_name = img_row['image_name']

                                        # Extract extension from image_name or default
                                        file_ext = img_name.split('.')[-1] if '.' in img_name else 'png'

                                        # Write the BLOB data to a temporary file
                                        temp_file_path = os.path.join(temp_dir, f"{report_id}_{img_index}.{file_ext}")
                                        with open(temp_file_path, 'wb') as f:
                                            f.write(img_data_blob)

                                        # Insert image from the temporary file path
                                        img = OpenpyxlImage(temp_file_path)
                                        img.anchor = f'A{current_row}'
                                        img.width = 300
                                        img.height = 200
                                        worksheet.add_image(img)

                                        # Move the next content/image down
                                        current_row += 15

                                    current_row += 2 # Extra separator row

                        # --- DOWNLOAD BUTTON FOR EXCEL WITH IMAGES ---
                        st.download_button(
                            label="⬇️ Download Excel (Data + Pictures)",
                            data=output.getvalue(),
                            file_name=f"{selected_option.lower()}_results_with_images.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )

                    except Exception as e:
                        st.error(f"Error creating Excel file with images: {e}")
                        st.warning("Ensure all image data is valid and required libraries are installed.")

                # The temporary directory is automatically cleaned up outside the 'with' block

            # CSV Download (for all options, including those without images)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="⬇️ Download Data as CSV (No Pictures)",
                data=csv,
                file_name=f"{selected_option.lower()}_results.csv",
                mime="text/csv"
            )
        else:
            st.info("No data found for your search.")
