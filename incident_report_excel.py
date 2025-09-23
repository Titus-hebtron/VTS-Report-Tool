import streamlit as st
import pandas as pd
import openpyxl
from openpyxl import Workbook
from io import BytesIO

def extract_incident_info(df):
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
            if 'Caller' in val:
                info['Caller'] = row[col+1] if col+1 < len(row) else ''
            if 'Phone Number' in val:
                info['Phone Number'] = row[col+1] if col+1 < len(row) else ''
            if 'Nature of Incident' in val:
                info['Nature of Incident'] = row[col+1] if col+1 < len(row) else ''
            if 'Bound:' in val:
                info['Bound'] = row[col+1] if col+1 < len(row) else ''
            if 'Chainage:' in val:
                info['Chainage'] = row[col+1] if col+1 < len(row) else ''
            if 'Response Time' in val:
                info['Response Time'] = row[col+1] if col+1 < len(row) else ''
    return info

def create_excel_report(info):
    wb = Workbook()
    ws = wb.active
    ws.title = 'Incident Report'
    # Template fields
    fields = [
        'Incident Date', 'Incident Time', 'Location', 'Bound', 'Chainage',
        'Vehicle Type', 'Number of Vehicles', 'Vehicle Condition', 'Number Injured',
        'Caller', 'Phone Number', 'Nature of Incident', 'Response Time', 'Clearing Time'
    ]
    ws.append(['Field', 'Value'])
    for field in fields:
        ws.append([field, info.get(field, '')])
    # Formatting (bold headers)
    for cell in ws[1]:
        cell.font = openpyxl.styles.Font(bold=True)
    # Auto column width
    for col in ws.columns:
        max_length = 0
        col_letter = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        ws.column_dimensions[col_letter].width = max_length + 2
    # Save to BytesIO
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output

st.title('Incident Report Excel Generator')

uploaded_file = st.file_uploader('Upload Incident Report CSV', type=['csv'])
if uploaded_file:
    df = pd.read_csv(uploaded_file, header=None)
    info = extract_incident_info(df)
    st.write('Extracted Incident Information:')
    for k, v in info.items():
        st.write(f"**{k}:** {v}")
    excel_data = create_excel_report(info)
    st.download_button('Download Incident Report Excel', excel_data, file_name='incident_report.xlsx')
