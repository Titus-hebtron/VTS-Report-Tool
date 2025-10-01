def search_page():
    import streamlit as st
    import pandas as pd
    from db_utils import get_sqlalchemy_engine
    from io import BytesIO
    import openpyxl
    from openpyxl.drawing.image import Image as OpenpyxlImage
    import os

    # Define the directory where images are expected to be saved
    IMAGE_DIR = "uploaded_accident_images"

    st.header("🔍 Search & View Data")

    search_options = ["Accidents", "Incidents", "Breaks", "Pickups"]
    selected_option = st.selectbox("Select data to view", search_options)

    # Convert date to string format for SQL query parameters
    start_date = st.date_input("Start date").strftime('%Y-%m-%d')
    end_date = st.date_input("End date").strftime('%Y-%m-%d')
    vehicle = st.text_input("Vehicle (optional)")

    if st.button("Search"):
        engine = get_sqlalchemy_engine()
        df = pd.DataFrame()
        image_df = pd.DataFrame() # DataFrame to hold image metadata

        # --- 1. CONSTRUCT QUERY AND FETCH MAIN DATA ---
        if selected_option in ["Accidents", "Incidents"]:
            incident_type = "Accident" if selected_option == "Accidents" else "Incident"
            query = "SELECT * FROM incident_reports WHERE incident_date BETWEEN ? AND ? AND incident_type = ?"
            params = (start_date, end_date, incident_type)

            if vehicle:
                query += " AND patrol_car = ?"
                params = params + (vehicle,)

            try:
                df = pd.read_sql_query(query, engine, params=params)
            except Exception as e:
                st.error(f"Database error fetching incident data: {e}")

            # --- 2. FETCH IMAGE METADATA FOR LINKING ---
            if not df.empty and 'rfi_no' in df.columns:
                rfi_list = df['rfi_no'].tolist()

                # Query the image metadata table for all relevant reports
                placeholders = ','.join(['?'] * len(rfi_list))
                image_query = f"SELECT * FROM accident_reports_images WHERE image_link_id IN ({placeholders})"

                try:
                    # image_df will contain: image_name, image_link_id (rfi_no), file_path, etc.
                    image_df = pd.read_sql_query(image_query, engine, params=rfi_list)
                    st.success(f"Found {len(df)} reports and {len(image_df)} associated images.")
                except Exception as e:
                    st.warning(f"Could not fetch image metadata. Database error: {e}. Download will be data-only.")

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

            # Offer Excel download for all options
            if True:  # Always true to enable for all

                output = BytesIO()

                # --- EXCEL CREATION ---
                try:
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        # 1. Write the DataFrame to the sheet first
                        df.to_excel(writer, index=False, sheet_name=selected_option)

                        # Embed images if available for Accidents/Incidents
                        if selected_option in ["Accidents", "Incidents"] and not image_df.empty:
                            workbook = writer.book
                            worksheet = writer.sheets[selected_option]

                            # Start writing pictures a few rows below the data table
                            current_row = len(df) + 3

                            # 2. Iterate through each incident report row
                            for index, row in df.iterrows():
                                rfi_no = row.get('rfi_no')
                                if not rfi_no:
                                    continue # Skip if RFI No is missing

                                # Filter images for the current report
                                linked_images = image_df[image_df['image_link_id'] == rfi_no]

                                if not linked_images.empty:
                                    # Write separator/header for the images
                                    worksheet.cell(row=current_row, column=1, value=f"--- IMAGES FOR RFI No: {rfi_no} ({row.get('location', 'N/A')}) ---").font = openpyxl.styles.Font(bold=True)
                                    current_row += 1

                                    # 3. Embed the pictures
                                    for img_index, img_row in linked_images.iterrows():
                                        image_path = img_row['file_path']

                                        # Use os.path.join for robust path handling (though image_path should already be absolute/full)
                                        full_path = image_path

                                        if os.path.exists(full_path):
                                            try:
                                                # Insert image using OpenpyxlImage
                                                img = OpenpyxlImage(full_path)
                                                # Anchor the image to the current cell (e.g., A[current_row])
                                                img.anchor = f'A{current_row}'

                                                # Optional: Set a reasonable fixed size for display (e.g., 300x200 pixels)
                                                img.width = 300
                                                img.height = 200

                                                worksheet.add_image(img)

                                                # Move the next content/image down by the image height plus margin
                                                current_row += 15
                                            except Exception as e:
                                                 worksheet.cell(row=current_row, column=1, value=f"Error inserting image {img_row['image_name']}: {e}").font = openpyxl.styles.Font(color="FF0000")
                                                 current_row += 2
                                        else:
                                            worksheet.cell(row=current_row, column=1, value=f"Image file not found on disk: {img_row['image_name']}").font = openpyxl.styles.Font(color="FF0000")
                                            current_row += 2

                                    current_row += 2 # Extra separator row

                    # --- DOWNLOAD BUTTON FOR EXCEL ---
                    label = "⬇️ Download Excel (Data + Pictures)" if selected_option in ["Accidents", "Incidents"] and not image_df.empty else "⬇️ Download Excel"
                    st.download_button(
                        label=label,
                        data=output.getvalue(),
                        file_name=f"{selected_option.lower()}_results.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )

                except Exception as e:
                    st.error(f"FATAL Error creating Excel file with images: {e}")
                    st.warning("Please ensure required libraries are installed and the image paths are correct.")

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
