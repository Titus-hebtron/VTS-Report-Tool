import streamlit as st
import pandas as pd
from io import BytesIO
import openpyxl
from openpyxl.drawing.image import Image as OpenpyxlImage # New Import for image handling
from sqlalchemy import text
from db_utils import get_sqlalchemy_engine
import os # New Import for file system operations

def accident_analysis_page():
    st.header("🚧 Accident Analysis Tool")

    uploaded_file = st.file_uploader("Upload Accident Workbook (.xlsx or .xls)", type=["xlsx", "xls"])

    if uploaded_file:
        try:
            # --- 1. SETUP & FILE EXTENSION CHECK ---
            file_ext = uploaded_file.name.split(".")[-1].lower()

            # --- 2. IMAGE EXTRACTION (Only possible for .xlsx files) ---
            all_images = {}
            IMAGE_DIR = "uploaded_accident_images" # Directory to save images
            image_counter = 0

            if file_ext == "xlsx":
                st.info("Attempting to extract embedded images from the XLSX file...")
                # Reset file pointer and load with openpyxl for image extraction
                uploaded_file.seek(0)
                workbook = openpyxl.load_workbook(uploaded_file)
                uploaded_file.seek(0) # Reset pointer again for pandas to read the data

                # Create the image directory if it doesn't exist
                os.makedirs(IMAGE_DIR, exist_ok=True)
                image_db_records = []

                for sheet_name in workbook.sheetnames:
                    worksheet = workbook[sheet_name]

                    # Iterate through all drawings on the sheet
                    if worksheet._drawing:
                        for drawing in worksheet._drawing.get_children():
                            # Check if the drawing is an embedded image
                            if isinstance(drawing, OpenpyxlImage):
                                image_bytes = drawing.image.ref.image.data
                                img_format = drawing.image.format.lower()

                                # Generate a unique name and path
                                image_name = f"image_{image_counter}_{sheet_name}.{img_format}"
                                file_path = os.path.join(IMAGE_DIR, image_name)
                                image_counter += 1

                                # Save the image to the file system
                                with open(file_path, 'wb') as f:
                                    f.write(image_bytes)

                                # Get cell anchor for metadata (e.g., A1, B5, etc.)
                                anchor_cell = str(drawing.anchor.cell) if drawing.anchor.cell else 'N/A'

                                # Prepare record for database storage
                                image_db_records.append({
                                    'image_name': image_name,
                                    'sheet_name': sheet_name,
                                    'anchor_cell': anchor_cell,
                                    'file_path': file_path,
                                    'upload_date': pd.Timestamp.now()
                                })

                if image_db_records:
                    all_images = pd.DataFrame(image_db_records)
                    st.success(f"🖼️ Successfully extracted and saved {len(all_images)} images to the '{IMAGE_DIR}' folder.")

            else:
                st.warning("⚠️ Image extraction is only supported for .xlsx files. Skipping image extraction for .xls.")


            # --- 3. DATA EXTRACTION (Original Logic) ---

            # Load file using the appropriate engine
            if file_ext == "xls":
                xls = pd.ExcelFile(uploaded_file, engine="xlrd")
            else:
                xls = pd.ExcelFile(uploaded_file, engine="openpyxl")

            all_data = []
            expected_cols = [
                "incident_date", "incident_time", "caller", "phone_number", "location",
                "bound", "chainage", "num_vehicles", "vehicle_type", "vehicle_condition",
                "num_injured", "cond_injured", "injured_part", "fire_hazard", "oil_leakage",
                "chemical_leakage", "damage_road_furniture", "response_time", "clearing_time",
                "department_contact", "description", "patrol_car", "incident_type"
            ]

            for sheet in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet)
                df.columns = df.columns.str.strip().str.lower()
                found_cols = [col for col in expected_cols if col in df.columns]

                if found_cols:
                    all_data.append(df[found_cols])

            if all_data:
                final_df = pd.concat(all_data, ignore_index=True)

                st.success(f"✅ Extracted {len(final_df)} accident records from {len(all_data)} sheets")

                # Display data
                st.subheader("📊 Extracted Accident Data")
                st.dataframe(final_df, width='stretch')

                # --- 4. DATA ANALYSIS ---
                st.subheader("📈 Accident Analysis")

                # Summary statistics
                st.write("### Summary Statistics")
                summary = final_df.describe(include='all')
                st.dataframe(summary)

                # Incident type distribution
                if 'incident_type' in final_df.columns:
                    st.write("### Incident Type Distribution")
                    incident_counts = final_df['incident_type'].value_counts()
                    st.bar_chart(incident_counts)

                # Location distribution
                if 'location' in final_df.columns:
                    st.write("### Location Distribution")
                    location_counts = final_df['location'].value_counts().head(10)  # Top 10
                    st.bar_chart(location_counts)

                # Response time analysis
                if 'response_time' in final_df.columns:
                    st.write("### Response Time Analysis")
                    # Assuming response_time is numeric
                    try:
                        response_times = pd.to_numeric(final_df['response_time'], errors='coerce')
                        st.write(f"Average Response Time: {response_times.mean():.2f} minutes")
                        st.write(f"Median Response Time: {response_times.median():.2f} minutes")
                    except:
                        st.write("Response time data not numeric.")

                # --- 5. SAVE BUTTON ---
                if st.button("💾 Save Data and Analysis to Database"):
                    try:
                        engine = get_sqlalchemy_engine()

                        # Store data records
                        with engine.connect() as conn:
                            final_df.to_sql(
                                'accident_reports_data',
                                con=conn,
                                if_exists='append',
                                index=False
                            )
                            conn.commit()
                        st.success("💾 Accident **Data** successfully stored in the `accident_reports_data` table.")

                        # Store image metadata records
                        if isinstance(all_images, pd.DataFrame) and not all_images.empty:
                            with engine.connect() as conn:
                                all_images.to_sql(
                                    'accident_reports_images',
                                    con=conn,
                                    if_exists='append',
                                    index=False
                                )
                                conn.commit()
                            st.success(f"💾 Image **Metadata** for {len(all_images)} images stored in the `accident_reports_images` table.")

                    except Exception as db_e:
                        st.error(f"Error connecting or storing to database (check db_utils.py): {db_e}")

                # --- 5. EXPORT OPTIONS (Original Logic) ---
                csv = final_df.to_csv(index=False).encode("utf-8")
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                    final_df.to_excel(writer, index=False, sheet_name="Accidents")

                st.subheader("⬇️ Download Extracted Data")
                st.download_button(
                    label="📥 Download as CSV",
                    data=csv,
                    file_name="accidents_extracted.csv",
                    mime="text/csv",
                )

                st.download_button(
                    label="📥 Download as Excel",
                    data=buffer.getvalue(),
                    file_name="accidents_extracted.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            else:
                st.warning("⚠️ No accident-related data found in the workbook.")

        except Exception as e:
            st.error(f"Error processing file: {e}")
