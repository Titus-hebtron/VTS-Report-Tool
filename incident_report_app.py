import streamlit as st
import pandas as pd

def extract_incident_info(df):
    # Try to extract key fields from the first few rows
    info = {}
    for i, row in df.iterrows():
        for col in row.index:
            val = str(row[col])
            if 'Incident Notification Date' in val:
                info['Incident Date'] = row[col+1] if col+1 < len(row) else ''
            if 'Incident Notification Time' in val:
                info['Incident Time'] = row[col+1] if col+1 < len(row) else ''
            if 'Location of Incident' in val:
                info['Location'] = row[col+1] if col+1 < len(row) else ''
            if 'Type of Vehicle' in val:
                info['Vehicle Type'] = row[col+1] if col+1 < len(row) else ''
            if 'Number of Accident Vehicles' in val:
                info['Number of Vehicles'] = row[col+1] if col+1 < len(row) else ''
            if 'Number of Injured People' in val:
                info['Number Injured'] = row[col+1] if col+1 < len(row) else ''
            if 'Conditions of Accident Vehicles' in val:
                info['Vehicle Condition'] = row[col+1] if col+1 < len(row) else ''
            if 'Clearing Time' in val:
                info['Clearing Time'] = row[col+1] if col+1 < len(row) else ''
    return info


st.title('Incident Report Extractor')

uploaded_file = st.file_uploader('Upload Incident Report CSV', type=['csv'])
image_files = st.file_uploader('Upload Incident Images (multiple allowed)', type=['jpg', 'jpeg', 'png'], accept_multiple_files=True, help='You can take a photo or select from your device.')

if uploaded_file:
    df = pd.read_csv(uploaded_file, header=None)
    st.write('Raw Data:', df.head(20))
    info = extract_incident_info(df)
    st.write('Extracted Incident Information:')
    for k, v in info.items():
        st.write(f"**{k}:** {v}")

    if image_files:
        st.write('---')
        st.subheader('Uploaded Incident Images')
        for img in image_files:
            # Use upload time as timestamp (Streamlit does not provide EXIF info)
            st.image(img, caption=f"Uploaded: {img.name}", use_column_width=True)
