import streamlit as st
import pandas as pd
from datetime import datetime
from db_utils import save_idle_report, get_idle_reports, get_connection
import re

def extract_vehicle_from_title(title_text):
    """Extract vehicle plate from title like 'Parking Details(KDC873G)' or 'ParkingDetails-KDC873G(...)'"""
    if not title_text:
        return None

    title_str = str(title_text).strip()

    # Look for pattern: (KDC873G) or similar in brackets
    bracket_match = re.search(r'\(([^)]+)\)', title_str)
    if bracket_match:
        vehicle = bracket_match.group(1).strip()
        # Clean up any extra characters that might be in the brackets
        vehicle = re.sub(r'[^\w-]', '', vehicle)
        return vehicle

    # Fallback: look for vehicle pattern in the text itself
    # Look for patterns like KDC873G, KDG320Z, etc.
    vehicle_match = re.search(r'\b([A-Z]{2,4}\d{1,4}[A-Z]*)\b', title_str)
    if vehicle_match:
        return vehicle_match.group(1).strip()

    return None

def extract_date_range(date_text):
    """Extract date range from text like 'From 2025-09-20 To 2025-09-25'"""
    if not date_text:
        return None, None

    # Look for pattern: From <date> To <date>
    from_match = re.search(r'From\s+([^\s]+)', str(date_text), re.IGNORECASE)
    to_match = re.search(r'To\s+([^\s]+)', str(date_text), re.IGNORECASE)

    start_date = None
    end_date = None

    if from_match:
        try:
            start_date = pd.to_datetime(from_match.group(1)).date()
        except:
            pass

    if to_match:
        try:
            end_date = pd.to_datetime(to_match.group(1)).date()
        except:
            pass

    return start_date, end_date

def parse_paschal_parking_excel(df):
    """Parse Paschal parking Excel with specific format"""
    try:
        st.write(f"Processing Paschal parking Excel. Original shape: {df.shape}")

        # For Paschal format: vehicle in first row brackets, data starts from 5th row (index 4)
        vehicle_plate = None

        # Extract vehicle from first row (index 0)
        if len(df) > 0:
            first_row = df.iloc[0]
            first_row_text = ' '.join([str(cell) for cell in first_row if pd.notna(cell)])
            vehicle_plate = extract_vehicle_from_title(first_row_text)
            st.write(f"First row content: '{first_row_text}'")
            st.write(f"Extracted vehicle: {vehicle_plate}")

            # Show first few rows for debugging
            st.write("First 10 rows preview:")
            preview_df = df.head(10).copy()
            preview_df['row_content'] = preview_df.apply(lambda row: ' | '.join([str(cell) if pd.notna(cell) else '' for cell in row]), axis=1)
            st.dataframe(preview_df[['row_content']])

        # Data always starts from 5th row (index 4) - treat all parking details as idle reports
        data_start_row = 4

        if data_start_row >= len(df):
            st.error("Excel file doesn't have enough rows for Paschal parking format.")
            return pd.DataFrame()

        # Extract data starting from row 4 (5th row)
        data_df = df.iloc[data_start_row:].copy()

        # Clean up empty rows
        data_df = data_df.dropna(how='all')

        # Reset index
        data_df = data_df.reset_index(drop=True)

        # Set expected column headers for Paschal parking format
        # Headers are: # | Start Time | End Time | Stop Duration | Address
        expected_headers = ['#', 'Start Time', 'End Time', 'Stop Duration', 'Address']
        if len(data_df.columns) >= len(expected_headers):
            data_df.columns = expected_headers + [f'extra_{i}' for i in range(len(expected_headers), len(data_df.columns))]
        else:
            # If fewer columns than expected, use what we have
            data_df.columns = expected_headers[:len(data_df.columns)]

        # Clean column names
        data_df.columns = data_df.columns.str.strip().str.lower()

        # Rename columns to match our schema
        column_mapping = {
            'start time': 'idle_start',
            'end time': 'idle_end',
            'stop duration': 'idle_duration_min',
            'address': 'location_address',
            'location': 'location_address'
        }

        data_df = data_df.rename(columns=column_mapping)

        # Process address column - merge coordinates and place name from two-line format
        if 'location_address' in data_df.columns:
            processed_addresses = []

            for idx, row in data_df.iterrows():
                current_addr = str(row.get('location_address', '')).strip()

                # Check if this row has coordinates (first line of address)
                if re.match(r'-?\d+\.\d+[NS],\s*-?\d+\.\d+[EW]', current_addr):
                    # This is coordinates, check next row for place name
                    if idx + 1 < len(data_df):
                        next_row = data_df.iloc[idx + 1]
                        next_addr = str(next_row.get('location_address', '')).strip()

                        # If next row has place name (doesn't look like coordinates)
                        if next_addr and not re.match(r'-?\d+\.\d+[NS],\s*-?\d+\.\d+[EW]', next_addr):
                            # Combine coordinates + place name
                            combined_address = f"{current_addr} {next_addr}"
                            processed_addresses.append(combined_address)
                            # Skip the next row as it's part of this address
                            data_df.at[idx + 1, 'location_address'] = None
                            continue

                # If not coordinates or no place name found, use current address as-is
                processed_addresses.append(current_addr if current_addr else None)

            data_df['location_address'] = processed_addresses

        # Remove rows that were marked for skipping (place name rows that were merged)
        data_df = data_df[data_df['location_address'].notna()]

        # Add vehicle plate to all rows
        if vehicle_plate:
            data_df['numberplate'] = vehicle_plate
        else:
            data_df['numberplate'] = 'Unknown'

        # Convert duration to minutes
        if 'idle_duration_min' in data_df.columns:
            data_df['idle_duration_min'] = data_df['idle_duration_min'].apply(parse_duration_to_minutes)

        # Convert times
        for col in ['idle_start', 'idle_end']:
            if col in data_df.columns:
                data_df[col] = pd.to_datetime(data_df[col], errors='coerce')

        # Extract coordinates from address if available
        data_df['latitude'] = None
        data_df['longitude'] = None

        if 'location_address' in data_df.columns:
            for idx, addr in data_df['location_address'].items():
                if addr and isinstance(addr, str):
                    # Look for coordinate pattern in address
                    coord_match = re.search(r'(-?\d+\.\d+)[NS],\s*(-?\d+\.\d+)[EW]', addr)
                    if coord_match:
                        lat_str = coord_match.group(1)
                        lon_str = coord_match.group(2)

                        # Convert to decimal degrees
                        try:
                            lat = float(lat_str)
                            lon = float(lon_str)
                            data_df.at[idx, 'latitude'] = lat
                            data_df.at[idx, 'longitude'] = lon
                        except:
                            pass

        # Add contractor ID
        from idle_time_analyzer_page import get_contractor_id_from_vehicle
        data_df['contact_id'] = data_df['numberplate'].apply(get_contractor_id_from_vehicle)

        # Select and clean final columns
        result_df = data_df[['numberplate', 'idle_start', 'idle_end', 'idle_duration_min', 'location_address', 'latitude', 'longitude', 'contact_id']].copy()

        # Drop rows with missing essential data
        result_df = result_df.dropna(subset=['idle_start', 'idle_end'])

        st.write(f"Paschal parking processing complete. Final shape: {result_df.shape}")
        return result_df

    except Exception as e:
        st.error(f"Error processing Paschal parking Excel: {e}")
        return pd.DataFrame()

def parse_duration_to_minutes(duration_str):
    """Parse duration strings to minutes"""
    if not duration_str or pd.isna(duration_str):
        return 0

    duration_str = str(duration_str).strip()

    # Handle HH:MM:SS format
    time_match = re.match(r'(\d+):(\d+)(?::(\d+))?', duration_str)
    if time_match:
        hours = int(time_match.group(1) or 0)
        minutes = int(time_match.group(2) or 0)
        seconds = int(time_match.group(3) or 0)
        return hours * 60 + minutes + seconds / 60

    # Handle "X min Y s" format
    match = re.match(r'(?:(\d+)\s*h\s*)?(?:(\d+)\s*min\s*)?(?:(\d+)\s*s)?', duration_str, re.IGNORECASE)
    if match:
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        return hours * 60 + minutes + seconds / 60

    # Handle decimal minutes
    decimal_match = re.match(r'(\d+(?:\.\d+)?)\s*min', duration_str, re.IGNORECASE)
    if decimal_match:
        return float(decimal_match.group(1))

    # Handle just seconds
    seconds_match = re.match(r'(\d+)\s*s', duration_str, re.IGNORECASE)
    if seconds_match:
        return int(seconds_match.group(1)) / 60

    # Try to convert directly to float
    try:
        return float(duration_str)
    except:
        return 0

def paschal_parking_analyzer_page():
    st.header("🅿️ Paschal Parking Analyzer")
    st.info("Upload Paschal parking Excel files with specific format: Title with vehicle in brackets, date range, and table with Start Time, End Time, Stop Duration, and Address columns.")

    # Get current contractor
    current_contractor = st.session_state.get("contractor", "Unknown")
    st.info(f"📋 Current Contractor: {current_contractor}")

    uploaded_file = st.file_uploader('Upload Paschal Parking Excel file', type=['xlsx', 'xls'])

    if uploaded_file:
        try:
            # Read Excel file with better error handling
            try:
                df = pd.read_excel(uploaded_file, header=None, engine='xlrd')  # Try xlrd for .xls files
                st.info("Excel file (.xls) loaded successfully with xlrd engine.")
            except Exception as excel_error:
                try:
                    df = pd.read_excel(uploaded_file, header=None, engine='openpyxl')  # Try openpyxl for .xlsx files
                    st.info("Excel file (.xlsx) loaded successfully with openpyxl engine.")
                except Exception as excel_error2:
                    st.warning(f"Could not read as Excel: {excel_error}. Trying alternative method...")
                    try:
                        # Try reading with different parameters
                        df = pd.read_excel(uploaded_file, header=None)
                        st.info("Excel file loaded successfully with default engine.")
                    except Exception as final_error:
                        st.error(f"Failed to read Excel file: {final_error}")
                        st.info("Please ensure the file is a valid Excel format (.xls or .xlsx)")
                        return

            st.write(f"File shape: {df.shape} rows x {df.columns} columns")

            # Process the Paschal parking data
            parking_df = parse_paschal_parking_excel(df)

            if not parking_df.empty:
                # Display results
                st.success(f"Successfully processed {len(parking_df)} parking records!")

                # Show summary info
                if len(parking_df) > 0:
                    vehicle = parking_df['numberplate'].iloc[0] if 'numberplate' in parking_df.columns else 'Unknown'
                    st.info(f"Vehicle: {vehicle}")

                    # Calculate total parking time
                    total_minutes = parking_df['idle_duration_min'].sum() if 'idle_duration_min' in parking_df.columns else 0
                    total_hours = total_minutes / 60
                    st.info(f"Total Parking Time: {total_hours:.1f} hours ({total_minutes:.1f} minutes)")

                # Display data table
                display_df = parking_df.copy()

                # Rename columns for display
                display_df = display_df.rename(columns={
                    'idle_start': 'Start Time',
                    'idle_end': 'End Time',
                    'idle_duration_min': 'Duration (min)',
                    'location_address': 'Location',
                    'latitude': 'Latitude',
                    'longitude': 'Longitude',
                    'numberplate': 'Vehicle',
                    'contact_id': 'Contractor ID'
                })

                st.write("Processed Parking Data:", display_df)

                # Download button
                st.download_button(
                    'Download Processed Parking Report',
                    display_df.to_csv(index=False),
                    file_name='paschal_parking_report.csv',
                    key="download_paschal"
                )

                # Save to database option
                if st.button("💾 Save Parking Report to Database"):
                    try:
                        # Prepare data for saving
                        save_df = parking_df.copy()

                        # Format vehicle name
                        save_df['vehicle'] = '"' + save_df['numberplate']

                        # Clean location address
                        from idle_time_analyzer_page import clean_location_address
                        save_df['location_address'] = save_df['location_address'].apply(clean_location_address)

                        # Rename columns to match database schema
                        save_df = save_df.rename(columns={
                            'idle_start': 'idle_start',
                            'idle_end': 'idle_end',
                            'idle_duration_min': 'idle_duration_min',
                            'location_address': 'location_address',
                            'latitude': 'latitude',
                            'longitude': 'longitude',
                            'contact_id': 'contractor_id'
                        })

                        # Filter out rows without contractor_id
                        save_df = save_df.dropna(subset=['contractor_id'])

                        if not save_df.empty:
                            save_idle_report(save_df, st.session_state.get('user_name', 'Unknown'))
                            st.success(f"✅ Parking report saved to database! ({len(save_df)} records)")
                        else:
                            st.error("❌ No records with valid contractor IDs to save.")

                    except Exception as e:
                        st.error(f"❌ Error saving to database: {e}")

            else:
                st.error("No parking data found in the uploaded file. Please check the file format.")

        except Exception as e:
            st.error(f"Error processing file: {e}")
            st.info("Please ensure the Excel file follows the Paschal parking format with title containing vehicle in brackets, date range, and proper table structure.")