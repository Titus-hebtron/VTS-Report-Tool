import streamlit as st
import pandas as pd
from io import BytesIO

def accident_analysis_page():
    st.header("🚧 Accident Analysis Tool")

    uploaded_file = st.file_uploader("Upload Accident Workbook (.xlsx or .xls)", type=["xlsx", "xls"])

    if uploaded_file:
        try:
            # ✅ Detect file extension
            file_ext = uploaded_file.name.split(".")[-1].lower()
            if file_ext == "xls":
                xls = pd.ExcelFile(uploaded_file, engine="xlrd")
            else:
                xls = pd.ExcelFile(uploaded_file, engine="openpyxl")

            all_data = []

            # ✅ Expected accident form fields
            expected_cols = [
                "incident_date", "incident_time", "caller", "phone_number", "location",
                "bound", "chainage", "num_vehicles", "vehicle_type", "vehicle_condition",
                "num_injured", "cond_injured", "injured_part", "fire_hazard", "oil_leakage",
                "chemical_leakage", "damage_road_furniture", "response_time", "clearing_time",
                "department_contact", "description", "patrol_car", "incident_type"
            ]

            for sheet in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet)

                # ✅ Normalize column names
                df.columns = df.columns.str.strip().str.lower()

                # ✅ Pick only accident-related columns that exist in the sheet
                found_cols = [col for col in expected_cols if col in df.columns]

                if found_cols:  # even if not all columns are found
                    all_data.append(df[found_cols])

            if all_data:
                final_df = pd.concat(all_data, ignore_index=True)

                st.success(f"✅ Extracted {len(final_df)} accident records from {len(all_data)} sheets")

                # ✅ Display ALL extracted accident data
                st.subheader("📊 Extracted Accident Data")
                st.dataframe(final_df, width='stretch')

                # ✅ Export options
                csv = final_df.to_csv(index=False).encode("utf-8")

                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                    final_df.to_excel(writer, index=False, sheet_name="Accidents")

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
