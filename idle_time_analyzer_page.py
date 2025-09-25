import streamlit as st
import pandas as pd
from datetime import timedelta
from db_utils import save_idle_report, get_idle_reports, get_connection
from db_utils import get_connection
import re

# Reverse geocoder for address conversion
try:
    from geopy.geocoders import Nominatim
    geolocator = Nominatim(user_agent="idle_time_analyzer")

    def get_address_from_coords(lat, lon):
        """Convert coordinates to address using reverse geocoding"""
        try:
            if pd.isna(lat) or pd.isna(lon) or lat == 0 or lon == 0:
                return f"{lat}, {lon}"
            location = geolocator.reverse((lat, lon), language="en", timeout=10)
            return location.address if location else f"{lat}, {lon}"
        except Exception as e:
            st.warning(f"Could not get address for coordinates {lat}, {lon}: {e}")
            return f"{lat}, {lon}"

    GEOPY_AVAILABLE = True
except ImportError:
    GEOPY_AVAILABLE = False
    def get_address_from_coords(lat, lon):
        return f"{lat}, {lon}"

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

def clean_location_address(address_string):
    """Clean HTML-formatted location addresses to extract readable address only"""
    if not address_string or pd.isna(address_string):
        return None

    address_string = str(address_string).strip()

    # If it's already a clean address (no HTML), return as-is
    if not ('<' in address_string and '>' in address_string):
        return address_string

    # Extract address from HTML link format like:
    # "<a href="...">-1.182645 °, 36.937273 °</a> - Thika Road, Gatongora ward, Ruiru, Kiambu, Central Kenya, 00609, Kenya"

    # Look for pattern: </a> - [actual address]
    link_end_pattern = r'</a>\s*-\s*(.+)'
    match = re.search(link_end_pattern, address_string, re.IGNORECASE)
    if match:
        clean_address = match.group(1).strip()
        # Clean up extra spaces and commas
        clean_address = re.sub(r'\s+', ' ', clean_address)  # Multiple spaces to single
        clean_address = re.sub(r',\s*,', ',', clean_address)  # Double commas
        clean_address = clean_address.strip(', ')  # Remove leading/trailing commas/spaces
        return clean_address

    # Fallback: try to extract anything after coordinates and dash
    coord_dash_pattern = r'-?\d+\.\d+\s*°?\s*,\s*-?\d+\.\d+\s*°?\s*-\s*(.+)'
    match = re.search(coord_dash_pattern, address_string)
    if match:
        clean_address = match.group(1).strip()
        clean_address = re.sub(r'\s+', ' ', clean_address)
        clean_address = clean_address.strip(', ')
        return clean_address

    # Last resort: remove HTML tags and clean up
    # Remove HTML tags
    clean_text = re.sub(r'<[^>]+>', '', address_string)
    # Remove coordinates pattern
    clean_text = re.sub(r'-?\d+\.\d+\s*°?\s*,\s*-?\d+\.\d+\s*°?', '', clean_text)
    # Clean up dashes and extra spaces
    clean_text = re.sub(r'\s*-\s*', ' ', clean_text)
    clean_text = re.sub(r'\s+', ' ', clean_text)
    clean_text = clean_text.strip(', ')

    return clean_text if clean_text else None

def get_contractor_id_from_vehicle(vehicle_string):
    """Get contractor_id from vehicle string (may contain plate + contractor name)"""
    if not vehicle_string or vehicle_string.lower() in ['unknown', 'unknown vehicle', '']:
        return None

    # Extract license plate from the vehicle string
    license_plate = extract_license_plate(vehicle_string)
    if not license_plate:
        return None

    # st.write(f"Extracted license plate: '{license_plate}' from '{vehicle_string}'")  # Debug output

    # Normalize the vehicle plate for matching
    normalized_plate = license_plate.replace(' ', '').replace('-', '')

    try:
        conn = get_connection()
        cur = conn.cursor()

        # Try exact match first
        cur.execute("SELECT contractor FROM vehicles WHERE UPPER(REPLACE(REPLACE(plate_number, ' ', ''), '-', '')) = %s", (normalized_plate,))
        row = cur.fetchone()

        # If no exact match, try partial match
        if not row:
            cur.execute("SELECT contractor FROM vehicles WHERE UPPER(REPLACE(REPLACE(plate_number, ' ', ''), '-', '')) LIKE %s", (f'%{normalized_plate}%',))
            row = cur.fetchone()

        # If still no match, try original format
        if not row:
            cur.execute("SELECT contractor FROM vehicles WHERE plate_number = %s", (license_plate,))
            row = cur.fetchone()

        if row:
            contractor_name = row[0]
            # st.write(f"Found contractor: '{contractor_name}' for plate '{license_plate}'")  # Debug output
            # Then get id from contractors table
            cur.execute("SELECT id FROM contractors WHERE name = %s", (contractor_name,))
            contractor_row = cur.fetchone()
            if contractor_row:
                contractor_id = contractor_row[0]
                # st.write(f"Contractor ID: {contractor_id}")  # Debug output
                return contractor_id

        # If no contractor found, return None (this is not an error)
        # st.write(f"No contractor found for license plate: {license_plate}")  # Debug output
        return None

    except Exception as e:
        # Only show warning for actual database errors, not missing contractors
        if "no such table" in str(e).lower() or "does not exist" in str(e).lower():
            st.warning(f"Database table issue: {e}")
        # For missing contractors, just return None silently
        return None
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
    return None

def detect_idle_format(df):
    """Detect if Excel is Wizpro or Paschal format based on columns"""
    columns = df.columns.str.strip().str.lower()

    # Wizpro typically has 'object', 'start', 'end', 'duration'
    wizpro_indicators = ['object', 'start', 'end', 'duration']
    wizpro_score = sum(1 for col in wizpro_indicators if col in columns)

    # Paschal typically has 'start time', 'end time', 'stop duration'
    paschal_indicators = ['start time', 'end time', 'stop duration']
    paschal_score = sum(1 for col in paschal_indicators if col in columns)

    if wizpro_score > paschal_score:
        return 'wizpro'
    elif paschal_score > wizpro_score:
        return 'paschal'
    else:
        return 'unknown'

def parse_wizpro_idle(df):
    """Parse Wizpro format idle report"""
    df.columns = df.columns.str.strip().str.lower()

    # Store original vehicle string before extracting license plate
    df['original_vehicle'] = df.get('object', '')

    df = df.rename(columns={
        'object': 'numberplate',
        'start': 'idle_start',
        'end': 'idle_end',
        'duration': 'idle_duration_min',
        'stop position': 'location_address',
        'location': 'location_address',
        'address': 'location_address'
    })

    # Convert duration if it's not numeric
    if 'idle_duration_min' in df.columns:
        df['idle_duration_min'] = pd.to_numeric(df['idle_duration_min'], errors='coerce')

    # Convert times
    for col in ['idle_start', 'idle_end']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    # Extract coordinates if available (look for lat/lon patterns)
    df['latitude'] = None
    df['longitude'] = None

    # Look for coordinate columns
    coord_columns = ['latitude', 'longitude', 'lat', 'lon', 'gps', 'coordinates']
    for col in df.columns:
        if any(coord_term in col for coord_term in coord_columns):
            # Try to parse coordinates from the column
            df[col] = df[col].astype(str)
            # Simple coordinate extraction - look for decimal numbers
            coord_pattern = r'(-?\d+\.\d+),\s*(-?\d+\.\d+)'
            matches = df[col].str.extract(coord_pattern)
            if not matches.empty and matches[0].notna().any():
                df['latitude'] = pd.to_numeric(matches[0], errors='coerce')
                df['longitude'] = pd.to_numeric(matches[1], errors='coerce')

    # If no location_address column exists, try to create one from coordinates
    if 'location_address' not in df.columns:
        df['location_address'] = None

    # Add contact_id
    df['contact_id'] = df['numberplate'].apply(get_contractor_id_from_vehicle)

    return df[['original_vehicle', 'numberplate', 'idle_start', 'idle_end', 'idle_duration_min', 'location_address', 'latitude', 'longitude', 'contact_id']].dropna(subset=['numberplate', 'idle_start', 'idle_end', 'idle_duration_min'])

def parse_paschal_idle(df):
    """Parse Paschal format idle report"""
    df.columns = df.columns.str.strip().str.lower()
    df = df.rename(columns={
        'start time': 'idle_start',
        'end time': 'idle_end',
        'stop duration': 'idle_duration_min',
        'location': 'location_address',
        'address': 'location_address'
    })

    # Convert duration if it's not numeric
    if 'idle_duration_min' in df.columns:
        df['idle_duration_min'] = pd.to_numeric(df['idle_duration_min'], errors='coerce')

    # Convert times
    for col in ['idle_start', 'idle_end']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    # Extract coordinates if available
    df['latitude'] = None
    df['longitude'] = None

    # Look for coordinate columns
    coord_columns = ['latitude', 'longitude', 'lat', 'lon', 'gps', 'coordinates']
    for col in df.columns:
        if any(coord_term in col for coord_term in coord_columns):
            df[col] = df[col].astype(str)
            # Try to parse coordinates
            coord_pattern = r'(-?\d+\.\d+),\s*(-?\d+\.\d+)'
            matches = df[col].str.extract(coord_pattern)
            if not matches.empty and matches[0].notna().any():
                df['latitude'] = pd.to_numeric(matches[0], errors='coerce')
                df['longitude'] = pd.to_numeric(matches[1], errors='coerce')

    # For Paschal, numberplate might be in a column, try to find it
    numberplate_col = None
    for col in df.columns:
        if 'plate' in col.lower() or 'vehicle' in col.lower() or 'number' in col.lower():
            numberplate_col = col
            break

    if numberplate_col:
        df = df.rename(columns={numberplate_col: 'numberplate'})
    else:
        # If no clear numberplate column, assume it's not present or use a default
        df['numberplate'] = 'Unknown'

    # Add contact_id
    df['contact_id'] = df['numberplate'].apply(get_contractor_id_from_vehicle)

    return df[['numberplate', 'idle_start', 'idle_end', 'idle_duration_min', 'location_address', 'latitude', 'longitude', 'contact_id']].dropna(subset=['numberplate', 'idle_start', 'idle_end', 'idle_duration_min'])
import re

def parse_html_idle_report(html_content):
    # Extract vehicle name - try multiple patterns
    vehicle = "Unknown Vehicle"
    vehicle_patterns = [
        r'<td><strong>Object:</strong></td><td>([^<]+)</td>',
        r'Object:\s*([^<\n]+)',
        r'<strong>Object:</strong>\s*([^<\n]+)',
        r'Vehicle:\s*([^<\n]+)',
        r'<td[^>]*>Object:</td>\s*<td[^>]*>([^<]+)</td>',
        r'Object:\s*([A-Z0-9\s\-]+)'  # License plate pattern
    ]

    for pattern in vehicle_patterns:
        vehicle_match = re.search(pattern, html_content, re.IGNORECASE)
        if vehicle_match:
            vehicle = vehicle_match.group(1).strip()
            break

    st.write(f"Extracted vehicle: {vehicle}")

    # Find all table rows - be more flexible
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html_content, re.DOTALL | re.IGNORECASE)

    idle_data = []
    st.write(f"Found {len(rows)} table rows to analyze")

    for i, row in enumerate(rows):
        # Look for rows that contain idle/stopped information
        row_text = row.lower()

        # Check for idle indicators
        idle_indicators = ['stopped', 'idle', 'engine idle', 'parking']
        has_idle_indicator = any(indicator in row_text for indicator in idle_indicators)

        if has_idle_indicator and ('<td' in row or 'td>' in row):
            # Extract cells - try different patterns
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)

            # Also try without attributes
            if not cells:
                cells = re.findall(r'<td>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)

            if len(cells) >= 4:
                # Try to identify columns by content
                status = cells[0].strip()
                start_time = ""
                end_time = ""
                duration = ""
                engine_idle = ""

                # Look for time patterns in cells
                time_pattern = re.compile(r'\d{1,2}:\d{2}(?::\d{2})?|\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}')

                for j, cell in enumerate(cells):
                    cell_clean = cell.strip()
                    if time_pattern.search(cell_clean):
                        if not start_time:
                            start_time = cell_clean
                        elif not end_time:
                            end_time = cell_clean

                    # Look for duration patterns
                    if 'min' in cell_clean.lower() or 's' in cell_clean.lower() or ':' in cell_clean:
                        if not duration and ('min' in cell_clean.lower() or 's' in cell_clean.lower()):
                            duration = cell_clean
                        elif not engine_idle and j >= 3:  # Engine idle is usually later columns
                            engine_idle = cell_clean

                # Use duration if engine_idle not found
                if not engine_idle:
                    engine_idle = duration

                if engine_idle and engine_idle.lower() not in ['0', '0 s', '0 min', '', 'n/a']:
                    # Parse duration to minutes
                    idle_min = parse_duration_to_minutes(engine_idle)
                    if idle_min <= 0 and duration:
                        idle_min = parse_duration_to_minutes(duration)

                    # Extract location/address from table cells
                    location_address = None
                    if len(cells) > 4:
                        # Look for location in subsequent columns (skip status, start, end, duration)
                        for k in range(4, min(len(cells), 10)):  # Check next several columns
                            cell_content = cells[k].strip()
                            # Skip empty cells, times, and pure numeric cells
                            if (cell_content and
                                not re.match(r'^\d{1,2}:\d{2}', cell_content) and
                                not re.match(r'^\d+(\.\d+)?$', cell_content) and
                                not re.match(r'^\d+\.\d+,\s*\d+\.\d+$', cell_content) and  # Skip coordinates
                                len(cell_content) > 2):  # Must be reasonably long

                                # Look for address-like content (contains letters, spaces, commas)
                                if re.search(r'[a-zA-Z]{3,}', cell_content):
                                    location_address = cell_content
                                    break

                    if idle_min > 0:
                        idle_data.append({
                            'vehicle': vehicle,
                            'idle_start': pd.to_datetime(start_time, errors='coerce'),
                            'idle_end': pd.to_datetime(end_time, errors='coerce'),
                            'idle_duration_min': idle_min,
                            'location_address': location_address
                        })

    st.write(f"Total idle records found: {len(idle_data)}")
    return pd.DataFrame(idle_data)

def parse_duration_to_minutes(duration_str):
    """Parse various duration formats to minutes"""
    if not duration_str or duration_str.lower() in ['n/a', 'none', '']:
        return 0

    duration_str = duration_str.strip()

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

    # Handle decimal minutes like "5.5 min"
    decimal_match = re.match(r'(\d+(?:\.\d+)?)\s*min', duration_str, re.IGNORECASE)
    if decimal_match:
        return float(decimal_match.group(1))

    # Handle just seconds like "300 s"
    seconds_match = re.match(r'(\d+)\s*s', duration_str, re.IGNORECASE)
    if seconds_match:
        return int(seconds_match.group(1)) / 60

    # Try to convert to float directly
    try:
        return float(duration_str)
    except ValueError:
        pass

    return 0

def clean_data(df):
    df = df.dropna(how='all')
    for col in df.columns:
        if 'time' in col.lower() or 'date' in col.lower():
            try:
                df[col] = pd.to_datetime(df[col])
            except Exception:
                pass
    return df

def find_idle_times(df, vehicle_col, time_col, speed_col, idle_threshold=5):
    idle_report = []
    for vehicle_id, group in df.groupby(vehicle_col):
        group = group.sort_values(time_col).copy()
        # Convert speed to numeric, treat non-numeric as 0 (idle)
        group['speed_val'] = pd.to_numeric(group[speed_col], errors='coerce').fillna(0)
        # Idle if speed <= 2 or NaN
        group['is_idle'] = (group['speed_val'] <= 2) | group['speed_val'].isna()
        # Find idle periods using vectorized operations
        group['idle_start'] = group[time_col].where(group['is_idle'] & ~group['is_idle'].shift(1, fill_value=False), pd.NaT)
        group['idle_end'] = group[time_col].where(group['is_idle'] & ~group['is_idle'].shift(-1, fill_value=False), pd.NaT)
        # Forward fill idle_start for consecutive idle rows
        group['idle_start'] = group['idle_start'].fillna(method='ffill')
        # Filter to rows where idle_end is set
        idle_periods = group.dropna(subset=['idle_end'])
        for _, row in idle_periods.iterrows():
            idle_duration = (row['idle_end'] - row['idle_start']).total_seconds() / 60
            if idle_duration > idle_threshold:
                idle_report.append({
                    'vehicle': vehicle_id,
                    'idle_start': row['idle_start'],
                    'idle_end': row['idle_end'],
                    'idle_duration_min': round(idle_duration, 2)
                })
    return pd.DataFrame(idle_report)

def idle_time_analyzer_page():
    st.header("Idle Time Analyzer")
    st.info("Upload an Excel, CSV, or XLS file downloaded from your GPS website to analyze idle time. XLS files are parsed directly for idle reports.")

    uploaded_file = st.file_uploader('Upload Excel, CSV, or XLS file', type=['csv', 'xlsx', 'xls'])

    # Address conversion option
    if GEOPY_AVAILABLE:
        convert_to_address = st.checkbox("Convert coordinates to readable addresses (requires internet connection)", value=False)
        if convert_to_address:
            st.info("⚠️ Address conversion may take time for large datasets and requires an internet connection.")
    else:
        convert_to_address = False
        st.warning("📍 **Geopy package not found!** To enable coordinate-to-address conversion:")
        st.code(".venv\\Scripts\\activate\npython -m pip install geopy")
        st.info("After installation, restart the application to use address conversion features.")
    if uploaded_file:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
            df = clean_data(df)
            st.write('Cleaned Data:', df.head())
        elif uploaded_file.name.endswith('.xls'):
            # Try to read as Excel first
            try:
                df = pd.read_excel(uploaded_file, engine='xlrd')
                df = clean_data(df)
                st.write('Cleaned XLS Data:', df.head())
                st.write('XLS Columns:', df.columns.tolist())
                st.write('XLS Shape:', df.shape)
                st.info("XLS file read as Excel successfully. Processing with format detection...")

                # Detect format for XLS files too
                format_type = detect_idle_format(df)
                st.write(f'Detected format: {format_type}')

                if format_type == 'wizpro':
                    idle_df = parse_wizpro_idle(df)
                    st.session_state['idle_df'] = idle_df
                    st.write('Converted Wizpro Idle Data:', idle_df)
                elif format_type == 'paschal':
                    idle_df = parse_paschal_idle(df)
                    st.session_state['idle_df'] = idle_df
                    st.write('Converted Paschal Idle Data:', idle_df)
                else:
                    st.warning("Unknown XLS format. Treating as raw idle data.")
                    # Assume it's already idle data format
                    if {'Vehicle', 'Idle Start', 'Idle End', 'Idle Duration (min)'}.issubset(df.columns):
                        df.columns = df.columns.str.lower()
                        df = df.rename(columns={
                            'vehicle': 'numberplate',
                            'idle start': 'idle_start',
                            'idle end': 'idle_end',
                            'idle duration (min)': 'idle_duration_min'
                        })

                        # Store original vehicle string
                        df['original_vehicle'] = df.get('vehicle', df['numberplate'])

                        # Convert duration if it's not numeric
                        if 'idle_duration_min' in df.columns:
                            df['idle_duration_min'] = pd.to_numeric(df['idle_duration_min'], errors='coerce')

                        # Convert times
                        for col in ['idle_start', 'idle_end']:
                            if col in df.columns:
                                df[col] = pd.to_datetime(df[col], errors='coerce')

                        # Extract location address from Excel columns
                        df['location_address'] = None
                        location_columns = ['location', 'address', 'stop position', 'location_address']
                        for col in df.columns:
                            if any(loc_term in col for loc_term in location_columns):
                                df['location_address'] = df[col]
                                break

                        # Extract coordinates if available
                        df['latitude'] = None
                        df['longitude'] = None

                        coord_columns = ['latitude', 'longitude', 'lat', 'lon', 'gps', 'coordinates']
                        for col in df.columns:
                            if any(coord_term in col for coord_term in coord_columns):
                                df[col] = df[col].astype(str)
                                coord_pattern = r'(-?\d+\.\d+),\s*(-?\d+\.\d+)'
                                matches = df[col].str.extract(coord_pattern)
                                if not matches.empty and matches[0].notna().any():
                                    df['latitude'] = pd.to_numeric(matches[0], errors='coerce')
                                    df['longitude'] = pd.to_numeric(matches[1], errors='coerce')

                        df['contact_id'] = df['numberplate'].apply(get_contractor_id_from_vehicle)
                        st.session_state['idle_df'] = df[['original_vehicle', 'numberplate', 'idle_start', 'idle_end', 'idle_duration_min', 'location_address', 'latitude', 'longitude', 'contact_id']].dropna(subset=['numberplate', 'idle_start', 'idle_end', 'idle_duration_min'])
                        st.write('Processed XLS Idle Data:', st.session_state['idle_df'])
                    else:
                        st.error("XLS file doesn't contain expected idle report columns.")
            except Exception as e:
                st.warning(f"Could not read as Excel: {e}. Trying HTML parsing...")
                # Fallback to HTML parsing
                uploaded_file.seek(0)  # Reset file pointer
                html_content = uploaded_file.read().decode('utf-8', errors='ignore')
                st.write('HTML Content Preview:', html_content[:500])  # Show first 500 chars for debugging
                df = parse_html_idle_report(html_content)
                st.write('Parsed HTML Idle Data:', df.head())
                st.write('HTML parsing found', len(df), 'rows')
                if not df.empty:
                    # Add contact_id for HTML parsed data
                    df = df.rename(columns={'vehicle': 'numberplate'})
                    df['contact_id'] = df['numberplate'].apply(get_contractor_id_from_vehicle)
                    st.session_state['idle_df'] = df
                    st.success("Idle report parsed successfully!")
                else:
                    st.error("No idle data found in XLS file. Please check the file format.")
        else:
            df = pd.read_excel(uploaded_file)
            df = clean_data(df)
            st.write('Cleaned Data:', df.head())

            # Detect format
            format_type = detect_idle_format(df)
            st.write(f'Detected format: {format_type}')

            if format_type == 'wizpro':
                idle_df = parse_wizpro_idle(df)
                st.session_state['idle_df'] = idle_df
                st.write('Converted Wizpro Idle Data:', idle_df)
            elif format_type == 'paschal':
                idle_df = parse_paschal_idle(df)
                st.session_state['idle_df'] = idle_df
                st.write('Converted Paschal Idle Data:', idle_df)
            else:
                # Check if it's already processed idle data format
                if {'Vehicle', 'Idle Start', 'Idle End', 'Idle Duration (min)'}.issubset(df.columns):
                    st.info("Detected processed idle data format. Processing directly...")
                    df.columns = df.columns.str.lower()
                    df = df.rename(columns={
                        'vehicle': 'numberplate',
                        'idle start': 'idle_start',
                        'idle end': 'idle_end',
                        'idle duration (min)': 'idle_duration_min',
                        'location': 'location_address',
                        'address': 'location_address'
                    })

                    # Store original vehicle string
                    df['original_vehicle'] = df.get('vehicle', df['numberplate'])

                    # Convert duration if it's not numeric
                    if 'idle_duration_min' in df.columns:
                        df['idle_duration_min'] = pd.to_numeric(df['idle_duration_min'], errors='coerce')

                    # Convert times
                    for col in ['idle_start', 'idle_end']:
                        if col in df.columns:
                            df[col] = pd.to_datetime(df[col], errors='coerce')

                    # Extract location address from Excel columns
                    df['location_address'] = None
                    location_columns = ['location', 'address', 'stop position', 'location_address']
                    for col in df.columns:
                        if any(loc_term in col for loc_term in location_columns):
                            df['location_address'] = df[col]
                            break

                    # Extract coordinates if available
                    df['latitude'] = None
                    df['longitude'] = None

                    # Look for coordinate columns in the data
                    coord_columns = ['latitude', 'longitude', 'lat', 'lon', 'gps', 'coordinates']
                    for col in df.columns:
                        if any(coord_term in col for coord_term in coord_columns):
                            df[col] = df[col].astype(str)
                            coord_pattern = r'(-?\d+\.\d+),\s*(-?\d+\.\d+)'
                            matches = df[col].str.extract(coord_pattern)
                            if not matches.empty and matches[0].notna().any():
                                df['latitude'] = pd.to_numeric(matches[0], errors='coerce')
                                df['longitude'] = pd.to_numeric(matches[1], errors='coerce')

                    df['contact_id'] = df['numberplate'].apply(get_contractor_id_from_vehicle)
                    st.session_state['idle_df'] = df[['original_vehicle', 'numberplate', 'idle_start', 'idle_end', 'idle_duration_min', 'location_address', 'latitude', 'longitude', 'contact_id']].dropna(subset=['numberplate', 'idle_start', 'idle_end', 'idle_duration_min'])
                    st.write('Processed Idle Data:', st.session_state['idle_df'])
                else:
                    # Fallback to manual selection for unknown formats
                    st.warning("Unknown format detected. Please select columns manually.")
                    columns = df.columns.tolist()
                    vehicle_col = st.selectbox('Select vehicle ID column', columns, key="vehicle_col")
                    time_col = st.selectbox('Select timestamp column', columns, key="time_col")
                    speed_col = st.selectbox('Select speed column (0 = idle)', columns, key="speed_col")
                    threshold = st.number_input('Idle threshold (minutes)', min_value=1, value=5, key="idle_threshold")

                    if st.button('Analyze Idle Times'):
                        idle_df = find_idle_times(df, vehicle_col, time_col, speed_col, idle_threshold=threshold)
                        st.session_state['idle_df'] = idle_df
                        st.write('Idle Periods (> threshold):', idle_df)

        # Show results if analysis has been done
        idle_df = st.session_state.get('idle_df', pd.DataFrame())
        if not idle_df.empty:
            # Convert coordinates to addresses if requested
            display_df = idle_df.copy()

            # Add a column showing the original vehicle string for display purposes
            if 'original_vehicle' not in display_df.columns:
                display_df['original_vehicle'] = display_df.get('original_vehicle', display_df['numberplate'])

            if convert_to_address and 'latitude' in display_df.columns and 'longitude' in display_df.columns:
                st.info("🔄 Converting coordinates to addresses... This may take a moment.")
                progress_bar = st.progress(0)
                total_rows = len(display_df)

                addresses = []
                for i, row in display_df.iterrows():
                    addr = get_address_from_coords(row.get('latitude'), row.get('longitude'))
                    addresses.append(addr)
                    progress_bar.progress((i + 1) / total_rows)

                display_df['readable_address'] = addresses
                progress_bar.empty()

                # Reorder columns to show address prominently
                cols = display_df.columns.tolist()
                if 'readable_address' in cols:
                    cols.remove('readable_address')
                    cols.insert(cols.index('location_address') + 1 if 'location_address' in cols else 2, 'readable_address')

            # Rename columns for better display - show full vehicle name for linking
            display_df = display_df.rename(columns={
                'idle_start': 'Idle Start',
                'idle_end': 'Idle End',
                'idle_duration_min': 'Duration (min)',
                'location_address': 'Location',
                'latitude': 'Latitude',
                'longitude': 'Longitude',
                'readable_address': 'Readable Address',
                'contact_id': 'Contractor ID'
            })

            # Show full vehicle name for incident report linking
            if 'original_vehicle' in display_df.columns and not display_df['original_vehicle'].isna().all():
                display_df = display_df.rename(columns={'original_vehicle': 'Vehicle'})
            else:
                # Fallback to license plate if no original vehicle name
                display_df = display_df.rename(columns={'numberplate': 'Vehicle'})

            # Keep license plate as separate column for reference
            display_df = display_df.rename(columns={'numberplate': 'License Plate'})

            st.write('Converted Idle Data:', display_df)
            st.download_button('Download Converted Idle Report', display_df.to_csv(index=False), file_name='converted_idle_report.csv', key="download2")

            # Show contractor matching summary
            matched_count = idle_df['contact_id'].notna().sum()
            total_count = len(idle_df)
            st.info(f"✅ Contractor matching: {matched_count}/{total_count} vehicles matched to contractors.")

            # Show unmatched vehicles
            unmatched = idle_df[idle_df['contact_id'].isna()]
            if not unmatched.empty:
                unmatched_vehicles = unmatched['numberplate'].unique()
                with st.expander("⚠️ Vehicles without contractor match"):
                    st.write("The following vehicles could not be matched to contractors:")
                    for vehicle in unmatched_vehicles:
                        st.write(f"• {vehicle}")
                    st.info("These records will not be saved to the database. Please ensure vehicle plates are registered in the system.")

            # Save to database option
            if st.button("💾 Save Idle Report to Database"):
                try:
                    # Prepare data for saving - rename columns to match database schema
                    save_df = idle_df.copy()

                    # Use only the license plate formatted with quotes and leading space
                    save_df['vehicle'] = '"' + save_df['numberplate']

                    # Clean and prepare location_address from Excel file
                    save_df['location_address'] = save_df['location_address'].apply(clean_location_address)

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
                        st.success(f"✅ Idle report saved to database! ({len(save_df)} records with valid contractor IDs)")
                    else:
                        st.error("❌ No records with valid contractor IDs to save.")
                except Exception as e:
                    st.error(f"❌ Error saving to database: {e}")

def view_idle_reports_page():
    st.header("Saved Idle Reports")
    df = get_idle_reports(limit=1000)

    # --- FILTERS ---
    st.subheader("Filter Idle Reports")
    # Define all possible patrol vehicles
    all_vehicles = ["KDG 320Z", "KDK 825Y", "KDS 374F"]
    vehicles_in_data = sorted(set(df['vehicle'].dropna().unique()))
    vehicles = sorted(set(all_vehicles) | set(vehicles_in_data))
    selected_vehicle = st.selectbox("Vehicle", options=["All"] + list(vehicles), key="vehicle_filter")
    if selected_vehicle != "All":
        # Extract license plate from selected vehicle for matching
        selected_plate = extract_license_plate(selected_vehicle)
        if selected_plate:
            # Filter by matching license plates in stored vehicle data
            df['extracted_plate'] = df['vehicle'].apply(extract_license_plate)
            df = df[df['extracted_plate'] == selected_plate]
            df = df.drop('extracted_plate', axis=1)
        else:
            # Fallback to original logic if license plate extraction fails
            selected_norm = selected_vehicle.strip().upper().rstrip('-')
            df = df[df['vehicle'].str.strip().str.upper().apply(lambda v: v.rstrip('-')) == selected_norm]

    date_min = df['idle_start'].min()
    date_max = df['idle_start'].max()
    if pd.isna(date_min) or pd.isna(date_max):
        st.warning("No idle start dates available to filter.")
        date_range = []
    else:
        date_range = st.date_input("Idle Start Date Range", [date_min, date_max], key="date_range")
        if date_range and len(date_range) == 2:
            df = df[(df['idle_start'] >= pd.to_datetime(date_range[0])) & (df['idle_start'] <= pd.to_datetime(date_range[1]))]
        else:
            st.warning("Please select a valid date range to filter reports.")

    # Delete
    delete_ids = st.multiselect("Select rows to delete (by ID)", df['id'], key="delete_ids")
    if st.button("Delete Selected"):
        if delete_ids:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM idle_reports WHERE id = ANY(%s)", (delete_ids,))
            conn.commit()
            cur.close()
            conn.close()
            st.success(f"Deleted {len(delete_ids)} row(s). Please refresh to see changes.")

    # Download
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download as CSV",
        data=csv,
        file_name="filtered_idle_reports.csv",
        mime="text/csv"
    )

    import io
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False)
    st.download_button(
        label="Download as Excel",
        data=excel_buffer.getvalue(),
        file_name="filtered_idle_reports.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.dataframe(df)