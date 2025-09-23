import streamlit as st
import pandas as pd
import datetime
from db_utils import (
    save_incident_report,
    save_incident_image,
    get_recent_incident_reports,
    get_incident_images,
)

# ---------------- Page Function ----------------
def incident_report_page(patrol_vehicle_options=None):
    st.header("🚨 Incident Reporting")

    if patrol_vehicle_options is None:
        patrol_vehicle_options = ["KDG 320Z", "KDK 825Y", "KDS 374F"]

    # ---------------- Incident Form ----------------
    incident_type = st.selectbox("Incident Type", ["Accident", "Incident"])
    patrol_car = st.selectbox("Select Patrol Car", patrol_vehicle_options)

    with st.form("incident_form", clear_on_submit=True):
        st.subheader("Incident Details")

        col1, col2 = st.columns(2)
        with col1:
            incident_date = st.date_input("Incident Date")
            incident_time = st.time_input("Incident Time")
            caller = st.text_input("Caller Name")
            phone_number = st.text_input("Caller Phone Number")
            location = st.text_input("Location")
            bound = st.selectbox("Bound", ["Nairobi Bound", "Thika Bound", "Under Pass", "Over Pass", "Service Lane"])
            chainage = st.text_input("Chainage (km)")

        with col2:
            num_vehicles = st.number_input("Number of Vehicles Involved", min_value=0)
            vehicle_type = st.text_input("Type of Vehicle(s) Involved")
            vehicle_condition = st.text_input("Condition of Vehicle(s)")
            num_injured = st.number_input("Number of Injured", min_value=0)
            cond_injured = st.text_input("Condition of Injured")
            injured_part = st.text_input("Body Part Injured")
            fire_hazard = st.checkbox("Fire Hazard")
            oil_leakage = st.checkbox("Oil Leakage")
            chemical_leakage = st.checkbox("Chemical Leakage")
            damage_road_furniture = st.text_area("Damaged Road Furniture")

        st.subheader("Response Details")
        col3, col4 = st.columns(2)
        with col3:
            response_date = st.date_input("Response Date", value=incident_date)
            response_time_val = st.time_input("Response Time", value=incident_time)
        with col4:
            clearing_date = st.date_input("Clearing Date", value=incident_date)
            clearing_time_val = st.time_input("Clearing Time")

        department_contact = st.text_input("Department Contact")
        description = st.text_area("Incident Description")

        uploaded_photos = st.file_uploader(
            "Upload Incident Photos",
            accept_multiple_files=True,
            type=["jpg", "jpeg", "png"]
        )

        submitted = st.form_submit_button("💾 Save Incident Report")
        if submitted:
            try:
                response_datetime = datetime.datetime.combine(response_date, response_time_val)
                clearing_datetime = datetime.datetime.combine(clearing_date, clearing_time_val)

                data = {
                    "incident_date": incident_date,
                    "incident_time": incident_time,
                    "caller": caller,
                    "phone_number": phone_number,
                    "location": location,
                    "bound": bound,
                    "chainage": chainage,
                    "num_vehicles": num_vehicles,
                    "vehicle_type": vehicle_type,
                    "vehicle_condition": vehicle_condition,
                    "num_injured": num_injured,
                    "cond_injured": cond_injured,
                    "injured_part": injured_part,
                    "fire_hazard": "Yes" if fire_hazard else "No",
                    "oil_leakage": "Yes" if oil_leakage else "No",
                    "chemical_leakage": "Yes" if chemical_leakage else "No",
                    "damage_road_furniture": damage_road_furniture,
                    "response_time": response_datetime,
                    "clearing_time": clearing_datetime,
                    "department_contact": department_contact,
                    "description": description,
                    "patrol_car": patrol_car,
                    "incident_type": incident_type,
                }

                report_id = save_incident_report(data, uploaded_by="Admin")

                # Save uploaded photos
                if uploaded_photos:
                    for file in uploaded_photos:
                        file_bytes = file.read()
                        save_incident_image(report_id, file_bytes, file.name)

                st.success("✅ Incident report saved successfully!")

            except Exception as e:
                st.error(f"Error saving incident report: {e}")

    # ---------------- Recent Reports Section ----------------
    st.subheader("📋 Recent Incident Reports")

    filter_type = st.radio("Filter by Type", ["All", "Accident", "Incident"], horizontal=True)
    df = get_recent_incident_reports(limit=20)

    if not df.empty:
        if filter_type != "All":
            df = df[df["incident_type"] == filter_type]

        st.dataframe(df)

        # ---------------- Images Section ----------------
        st.subheader("🖼️ Incident Photos")
        selected_id = st.selectbox("Select Incident ID to view photos", df["id"].tolist())
        if selected_id:
            images_meta = get_incident_images(selected_id, only_meta=True)  # only metadata
            if images_meta:
                img_name = st.selectbox("Select Image", [img["image_name"] for img in images_meta])
                if st.button("View Selected Image"):
                    images = get_incident_images(selected_id)
                    selected_img = next(img for img in images if img["image_name"] == img_name)
                    st.image(bytes(selected_img["image_data"]), caption=img_name, width='stretch')
            else:
                st.info("No images uploaded for this incident.")
    else:
        st.info("No incident reports found.")
