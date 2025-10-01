import streamlit as st
import pandas as pd
from datetime import timedelta
from db_utils import save_idle_report, get_idle_reports, get_connection, get_active_contractor
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
    """Extract standardized license plate from vehicle string, normalizing variations"""
    if not vehicle_string or vehicle_string.lower() in ['unknown', 'unknown vehicle', '']:
        return None

    # Clean the string: remove extra whitespace, newlines, tabs, quotes, and special chars
    vehicle_string = re.sub(r'[\s\t\n\r"\'-]+', ' ', vehicle_string.strip())

    # Primary pattern: 3 letters + space + 3-4 digits + optional letter (e.g., "KDK 825Y")
    plate_pattern = re.search(r'\b([A-Z]{3}\s+\d{3,4}[A-Z]?)\b', vehicle_string.upper())
    if plate_pattern:
        plate = plate_pattern.group(1)
        # Normalize spacing (ensure single space between letters and numbers)
        plate = re.sub(r'\s+', ' ', plate)
        return plate

    # Secondary pattern: 3 letters + 3-4 digits + optional letter (no space, may have company name after)
    # This handles cases like "KDG320ZWIZPROENTERPRISESLTD" -> "KDG320Z"
    compact_pattern = re.search(r'\b([A-Z]{3}\d{3,4}[A-Z]?)(?:[A-Z]*)*\b', vehicle_string.upper())
    if compact_pattern:
        plate = compact_pattern.group(1)
        # Add space between letters and numbers for consistency
        plate = re.sub(r'([A-Z]{3})(\d)', r'\1 \2', plate)
        return plate

    # Fallback: any license plate-like pattern
    fallback_pattern = re.search(r'\b([A-Z]{2,4}\s*\d{1,4}[A-Z]*)\b', vehicle_string.upper())
    if fallback_pattern:
        plate = fallback_pattern.group(1)
        # Normalize spacing
        plate = re.sub(r'\s+', ' ', plate).strip()
        return plate

    # Last resort: clean and return as-is
    return re.sub(r'[^\w]', '', vehicle_string.upper())

def clean_location_address(address_string):
    """Clean HTML-formatted location addresses to extract readable address only"""
    if not address_string or pd.isna(address_string):
        return None

    address_string = str(address_string).strip()

    # If it's already a clean address (no HTML), return as-is
    if not ('<' in address_string and '>' in address_string):
        return address_string

    # Extract address from HTML link format like:
    # "<a href=""https://maps.google.com/maps?q=-1.172250,36.947549&t=m"" target=""_blank"">-1.172250 °, 36.947549 °</a> - Gatongora ward, Ruiru, Kiambu, Central Kenya, 00609, Kenya"

    # Look for pattern: </a> - [actual address] (handle escaped quotes)
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
        'stop position': 'location_address',  # ✅ Use stop position column for address
        'location': 'location_address',
        'address': 'location_address'
    })

    # ✅ Filter for Wizpro: only process vehicles with "stopped" status
    # Check for status column with various possible names
    status_col = None
    status_column_names = ['status', 'Status', 'STATUS', 'state', 'State', 'STATE']

    for col_name in status_column_names:
        if col_name in df.columns:
            status_col = col_name
            break

    if status_col:
        original_count = len(df)
        # Show what status values exist before filtering
        unique_statuses = df[status_col].dropna().unique()
        st.write(f"📊 Found status values in '{status_col}' column: {list(unique_statuses)}")

        # Filter for "stopped" status (case-insensitive, strip whitespace)
        df = df[df[status_col].str.lower().str.strip() == 'stopped']
        filtered_count = len(df)
        st.write(f"✅ Filtered Wizpro data: {original_count} → {filtered_count} 'stopped' records")

        # If no records remain after filtering, show a warning
        if filtered_count == 0:
            st.warning(f"⚠️ No records with 'stopped' status found in '{status_col}' column. Available values: {list(unique_statuses)}")
    elif 'idle_duration_min' in df.columns:
        # If no status column but we have duration, assume these are idle records
        original_count = len(df)
        df = df[df['idle_duration_min'] > 0]
        filtered_count = len(df)
        st.write(f"✅ Filtered Wizpro data: {original_count} → {filtered_count} records with duration > 0")
    else:
        st.warning("⚠️ No 'status' column found in Wizpro file. Available columns: " + ", ".join(df.columns.tolist()))
        st.info("💡 Wizpro files should have a 'Status' column with 'stopped' values for idle records.")

    # Convert duration if it's not numeric
    if 'idle_duration_min' in df.columns:
        df['idle_duration_min'] = pd.to_numeric(df['idle_duration_min'], errors='coerce')

    # Convert times
    for col in ['idle_start', 'idle_end']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    # ✅ For Wizpro: Use the "stop position" column directly as location_address
    # No HTML parsing needed - just use the data as-is from the Excel column
    df['latitude'] = None
    df['longitude'] = None

    # If location_address column doesn't exist (should be mapped from "stop position"), create it
    if 'location_address' not in df.columns:
        df['location_address'] = None
        st.write("⚠️ No 'stop position' column found in Wizpro file")

    # Add contact_id
    df['contact_id'] = df['numberplate'].apply(get_contractor_id_from_vehicle)

    return df[['original_vehicle', 'numberplate', 'idle_start', 'idle_end', 'idle_duration_min', 'location_address', 'latitude', 'longitude', 'contact_id']].dropna(subset=['numberplate', 'idle_start', 'idle_end', 'idle_duration_min'])

def parse_paschal_idle_report(df):
    """Parse Paschal idle report format: scan file to find headers and vehicle info"""
    try:
        # Must have at least 3 rows
        if len(df) < 3:
            st.warning("Paschal idle report file is too short, expected at least 3 rows.")
            return pd.DataFrame()

        # Expected header columns for Paschal idle reports
        expected_headers = ['#', 'start time', 'end time', 'stop duration', 'coordinate', 'address']

        # Scan the file to find the header row (row with most matching headers)
        header_row = None
        max_matches = 0

        for row_idx in range(min(len(df), 10)):  # Check first 10 rows for headers
            row_values = df.iloc[row_idx].astype(str).str.strip().str.lower()
            matches = sum(1 for header in expected_headers if any(header in cell for cell in row_values.values))
            if matches > max_matches:
                max_matches = matches
                header_row = row_idx

        if header_row is None or max_matches < 2:
            st.warning("Could not find header row with expected columns in Paschal idle report")
            return pd.DataFrame()

        st.write(f"Found header row at position {header_row} with {max_matches} matching columns")

        # Extract vehicle from rows before header (typically row 0)
        vehicle_info = None
        for row_idx in range(header_row):
            row_values = df.iloc[row_idx].astype(str).str.strip()

            # Look for license plate pattern in any cell
            for cell in row_values:
                # Try various patterns for Kenyan license plates
                plate_patterns = [
                    r'\b([A-Z]{3}\s*\d{1,4}[A-Z]*)\b',  # KDG 320Z, KDK825Y
                    r'\b([A-Z]{2,4}\d{1,4}[A-Z]*)\b',   # KDG320Z, KDK825Y
                    r'\(([^)]+)\)',                      # (KDG 320Z)
                ]

                for pattern in plate_patterns:
                    match = re.search(pattern, cell, re.IGNORECASE)
                    if match:
                        vehicle_info = match.group(1).strip()
                        # Clean up spacing
                        vehicle_info = re.sub(r'\s+', '', vehicle_info).upper()
                        break
                if vehicle_info:
                    break
            if vehicle_info:
                break

        if not vehicle_info:
            st.warning("Could not extract vehicle information from rows before header")
            vehicle_info = "Unknown Vehicle"

        st.write(f"Extracted vehicle: {vehicle_info}")

        # Set headers from detected header row
        df.columns = df.iloc[header_row].astype(str).str.strip()

        # Data starts from row after header
        df = df.iloc[header_row + 1:].reset_index(drop=True)

        # Standardize column names
        df.columns = df.columns.str.strip().str.lower()

        # Rename columns to match expected format
        column_mapping = {
            '#': 'serial_number',
            'start time': 'idle_start',
            'end time': 'idle_end',
            'stop duration': 'idle_duration_min',
            'coordinate': 'coordinates',
            'coordinates': 'coordinates',
            'address': 'location_address',
            'location': 'location_address'
        }

        df = df.rename(columns=column_mapping)

        # Convert duration to minutes if it's in time format
        if 'idle_duration_min' in df.columns:
            df['idle_duration_min'] = df['idle_duration_min'].apply(parse_duration_to_minutes)

        # Convert timestamps
        for col in ['idle_start', 'idle_end']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

        # Extract coordinates from coordinate column
        df['latitude'] = None
        df['longitude'] = None

        if 'coordinates' in df.columns:
            coord_pattern = r'(-?\d+\.\d+),\s*(-?\d+\.\d+)'
            df['coordinates'] = df['coordinates'].astype(str)

            # Extract lat/lon from coordinate strings
            coords_extracted = df['coordinates'].str.extract(coord_pattern)
            if not coords_extracted.empty:
                df['latitude'] = pd.to_numeric(coords_extracted[0], errors='coerce')
                df['longitude'] = pd.to_numeric(coords_extracted[1], errors='coerce')

        # Add vehicle info to all rows
        df['numberplate'] = vehicle_info

        # Get contractor ID
        df['contact_id'] = df['numberplate'].apply(get_contractor_id_from_vehicle)

        # Select and clean final columns
        result_df = df[['numberplate', 'idle_start', 'idle_end', 'idle_duration_min',
                        'location_address', 'latitude', 'longitude', 'contact_id']].copy()

        # Drop rows with missing essential data
        result_df = result_df.dropna(subset=['idle_start', 'idle_end', 'idle_duration_min'])

        st.write(f"Paschal idle report parsing complete. Found {len(result_df)} records.")
        return result_df

    except Exception as e:
        st.error(f"Error parsing Paschal idle report: {e}")
        return pd.DataFrame()

def parse_paschal_idle(df):
    """Parse Paschal format idle report - vehicle in first row, headers in 4th row"""
    try:
        # ✅ Must have at least 4 rows
        if len(df) < 4:
            st.warning("Paschal file is too short, expected at least 4 rows.")
            return pd.DataFrame()

        # 🔹 Extract vehicle info from 1st row
        first_row = df.iloc[0].astype(str).tolist()
        vehicle_info = None

        # Try bracket pattern (e.g. (KDG 320Z))
        for cell in first_row:
            bracket_match = re.search(r'\(([^)]+)\)', cell)
            if bracket_match:
                vehicle_info = bracket_match.group(1).strip()
                break

        # Fallback: try license plate pattern
        if not vehicle_info:
            for cell in first_row:
                plate_match = re.search(r'[A-Z]{2,4}\s*\d{1,4}[A-Z]*', cell)
                if plate_match:
                    vehicle_info = plate_match.group(0).strip()
                    break

        # 🔹 Set headers from 4th row
        df.columns = df.iloc[3].astype(str)
        df = df.iloc[4:].reset_index(drop=True)

        # 🔹 Standardize columns
        df.columns = df.columns.str.strip().str.lower()
        df = df.rename(columns={
            'start time': 'idle_start',
            'end time': 'idle_end',
            'stop duration': 'idle_duration_min',
            'location': 'location_address',
            'address': 'location_address',
            'vehicle': 'numberplate',
            'plate': 'numberplate',
            'number': 'numberplate'
        })

        # Apply vehicle info if extracted
        df['numberplate'] = vehicle_info if vehicle_info else df.get('numberplate', 'Unknown Vehicle')

        # 🔹 Convert types
        df['idle_duration_min'] = pd.to_numeric(df['idle_duration_min'], errors='coerce')
        df['idle_start'] = pd.to_datetime(df['idle_start'], errors='coerce')
        df['idle_end'] = pd.to_datetime(df['idle_end'], errors='coerce')

        # 🔹 Coordinates extraction
        df['latitude'], df['longitude'] = None, None
        coord_pattern = r'(-?\d+\.\d+),\s*(-?\d+\.\d+)'
        for col in df.columns:
            if any(term in col for term in ['lat', 'lon', 'coordinates', 'gps']):
                matches = df[col].astype(str).str.extract(coord_pattern)
                if not matches.empty and matches[0].notna().any():
                    df['latitude'] = pd.to_numeric(matches[0], errors='coerce')
                    df['longitude'] = pd.to_numeric(matches[1], errors='coerce')

        # 🔹 Contractor ID
        df['contact_id'] = df['numberplate'].apply(get_contractor_id_from_vehicle)

        # 🔹 Final clean DataFrame
        return df[['numberplate', 'idle_start', 'idle_end', 'idle_duration_min',
                    'location_address', 'latitude', 'longitude', 'contact_id']].dropna(
                        subset=['idle_start', 'idle_end', 'idle_duration_min']
                    )

    except Exception as e:
        st.error(f"Paschal parser failed: {e}")
        return pd.DataFrame()
import re

def parse_html_idle_report(html_content):
    """Parse HTML idle/parking reports - handles both Wizpro and Paschal HTML formats"""
    try:
        st.write("🔍 Analyzing HTML content structure...")

        # First, try to determine if this is Wizpro or Paschal format by looking for specific patterns
        is_paschal = False
        is_wizpro = False

        html_lower = html_content.lower()

        # Check for Wizpro indicators first (status column is a strong Wizpro indicator)
        wizpro_indicators = ['wizpro', 'stopped', 'stop position', 'idle time', 'status']
        if any(indicator in html_lower for indicator in wizpro_indicators):
            is_wizpro = True
            st.write("📊 Detected Wizpro HTML format (status/stop position indicators)")

        # Check for Paschal indicators (only if not Wizpro)
        if not is_wizpro:
            paschal_indicators = ['engine idle report', 'engine idle', 'idle report', 'coordinate', 'start time', 'end time', 'stop duration']
            if any(indicator in html_lower for indicator in paschal_indicators):
                is_paschal = True
                st.write("📊 Detected Paschal HTML format (idle report)")

        # Extract vehicle name - try multiple patterns for both formats
        vehicle = "Unknown Vehicle"
        vehicle_patterns = [
            r'<td><strong>Object:</strong></td><td>([^<]+)</td>',
            r'Object:\s*([^<\n]+)',
            r'<strong>Object:</strong>\s*([^<\n]+)',
            r'Vehicle:\s*([^<\n]+)',
            r'<td[^>]*>Object:</td>\s*<td[^>]*>([^<]+)</td>',
            r'Object:\s*([A-Z0-9\s\-]+)',  # License plate pattern
            r'Parking\s*Details\s*\(([^)]+)\)',  # Paschal format: Parking Details(KDC873G)
            r'ParkingDetails-([A-Z0-9]+)',  # Alternative Paschal format
            r'([A-Z]{3}\s*\d{1,4}[A-Z]*)-Engine\s*Idle\s*Report',  # KDD 500X-Engine Idle Report
            r'Engine\s*Idle\s*Report-([A-Z0-9]+)',  # EngineIdleReport-KDD500X
            r'([A-Z0-9]{3,8})-Engine\s*Idle\s*Report',  # KDD500X-Engine Idle Report (no space)
        ]

        for pattern in vehicle_patterns:
            vehicle_match = re.search(pattern, html_content, re.IGNORECASE)
            if vehicle_match:
                vehicle = vehicle_match.group(1).strip()
                # Clean up the vehicle name (remove extra spaces, standardize format)
                vehicle = re.sub(r'\s+', '', vehicle).upper()
                st.write(f"✅ Extracted vehicle: {vehicle}")
                break

        # Find all table rows - be more flexible
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html_content, re.DOTALL | re.IGNORECASE)
        st.write(f"📋 Found {len(rows)} table rows")

        idle_data = []

        if is_wizpro:
            # Handle Wizpro HTML format - look for status column and filter for "stopped"
            st.write("🔄 Processing Wizpro HTML format...")

            # First, try to identify column positions by looking for headers
            status_col = -1
            stop_position_col = -1
            start_time_col = -1
            end_time_col = -1
            duration_col = -1

            # Look for header row
            for row in rows[:5]:  # Check first few rows for headers
                cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)
                if not cells:
                    cells = re.findall(r'<td>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)

                for col_idx, cell in enumerate(cells):
                    cell_text = cell.strip().lower()
                    if 'status' in cell_text:
                        status_col = col_idx
                        st.write(f"✅ Found 'Status' column at position {col_idx}")
                    elif 'stop position' in cell_text:
                        stop_position_col = col_idx
                        st.write(f"✅ Found 'Stop Position' column at position {col_idx}")
                    elif 'start' in cell_text and 'time' in cell_text:
                        start_time_col = col_idx
                    elif 'end' in cell_text and 'time' in cell_text:
                        end_time_col = col_idx
                    elif 'duration' in cell_text:
                        duration_col = col_idx

            # If we found the key columns, use positional extraction
            if status_col >= 0 and stop_position_col >= 0:
                st.write("🔍 Using column position mapping for Wizpro HTML")

                for row in rows:
                    cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)
                    if not cells:
                        cells = re.findall(r'<td>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)

                    if len(cells) > max(status_col, stop_position_col):
                        # Check if status is "stopped"
                        status_value = cells[status_col].strip().lower() if status_col < len(cells) else ""
                        if status_value == "stopped":
                            # Extract stop position for address
                            address_text = cells[stop_position_col].strip() if stop_position_col < len(cells) else ""

                            # Look for time and duration data in other cells
                            start_time = None
                            end_time = None
                            duration_text = None

                            for cell in cells:
                                cell_clean = cell.strip()
                                if not cell_clean or cell_clean.lower() in ['n/a', 'none', '']:
                                    continue

                                time_match = re.search(r'\d{1,2}:\d{2}(?::\d{2})?|\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}', cell_clean)
                                if time_match:
                                    if not start_time:
                                        start_time = cell_clean
                                    elif not end_time:
                                        end_time = cell_clean

                                # Look for duration
                                if ('min' in cell_clean.lower() or 's' in cell_clean.lower()) and not duration_text:
                                    duration_text = cell_clean

                            if start_time and end_time:
                                idle_min = parse_duration_to_minutes(duration_text) if duration_text else 0

                                idle_data.append({
                                    'vehicle': vehicle,
                                    'idle_start': pd.to_datetime(start_time, errors='coerce'),
                                    'idle_end': pd.to_datetime(end_time, errors='coerce'),
                                    'idle_duration_min': idle_min,
                                    'location_address': address_text if address_text else None
                                })
            else:
                # Fallback: generic parsing if column headers not found
                st.write("⚠️ Column headers not found, using generic parsing")

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

                                # Extract location/address from table cells with coordinate parsing
                                location_address = None
                                latitude = None
                                longitude = None

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

                                            # Check if this cell contains HTML-formatted address
                                            if '<a' in cell_content:
                                                # Extract coordinates from href: q=-1.275198,36.812071&t=m
                                                coord_match = re.search(r'q=([+-]?\d+\.\d+),([+-]?\d+\.\d+)', cell_content)
                                                if coord_match:
                                                    latitude = float(coord_match.group(1))
                                                    longitude = float(coord_match.group(2))

                                                # Extract address from after </a> -
                                                addr_match = re.search(r'</a>\s*-\s*(.+)', cell_content)
                                                if addr_match:
                                                    location_address = addr_match.group(1).strip()
                                                else:
                                                    location_address = cell_content  # Fallback to raw if parsing fails
                                            else:
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
                                        'location_address': location_address,
                                        'latitude': latitude,
                                        'longitude': longitude
                                    })

        elif is_paschal:
            # Handle Paschal HTML format - look for idle report columns
            st.write("🔄 Processing Paschal HTML format (idle report)...")

            # First, try to identify column positions by looking for headers
            serial_col = -1
            start_time_col = -1
            end_time_col = -1
            stop_duration_col = -1
            coordinate_col = -1
            address_col = -1

            # Look for header row
            for row in rows[:10]:  # Check first 10 rows for headers
                cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)
                if not cells:
                    cells = re.findall(r'<td>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)

                for col_idx, cell in enumerate(cells):
                    cell_text = cell.strip().lower()
                    if cell_text == '#':
                        serial_col = col_idx
                        st.write(f"✅ Found '#' column at position {col_idx}")
                    elif 'start time' in cell_text:
                        start_time_col = col_idx
                        st.write(f"✅ Found 'Start Time' column at position {col_idx}")
                    elif 'end time' in cell_text:
                        end_time_col = col_idx
                        st.write(f"✅ Found 'End Time' column at position {col_idx}")
                    elif 'stop duration' in cell_text:
                        stop_duration_col = col_idx
                        st.write(f"✅ Found 'Stop Duration' column at position {col_idx}")
                    elif 'coordinate' in cell_text:
                        coordinate_col = col_idx
                        st.write(f"✅ Found 'Coordinate' column at position {col_idx}")
                    elif 'address' in cell_text and address_col == -1:  # Take first address column
                        address_col = col_idx
                        st.write(f"✅ Found 'Address' column at position {col_idx}")

            # If we found the key columns, use positional extraction
            if start_time_col >= 0 and end_time_col >= 0 and stop_duration_col >= 0:
                st.write("🔍 Using column position mapping for Paschal HTML idle report")

                for row in rows:
                    cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)
                    if not cells:
                        cells = re.findall(r'<td>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)

                    if len(cells) > max(start_time_col, end_time_col, stop_duration_col):
                        # Extract data from known column positions
                        start_time = cells[start_time_col].strip() if start_time_col < len(cells) else ""
                        end_time = cells[end_time_col].strip() if end_time_col < len(cells) else ""
                        duration_text = cells[stop_duration_col].strip() if stop_duration_col < len(cells) else ""

                        # Extract coordinates if available
                        coordinate_text = ""
                        if coordinate_col >= 0 and coordinate_col < len(cells):
                            coordinate_text = cells[coordinate_col].strip()

                        # Extract address if available
                        address_text = ""
                        if address_col >= 0 and address_col < len(cells):
                            address_text = cells[address_col].strip()

                        # Parse coordinates
                        latitude = None
                        longitude = None
                        if coordinate_text:
                            coord_match = re.search(r'([+-]?\d+\.\d+),\s*([+-]?\d+\.\d+)', coordinate_text)
                            if coord_match:
                                latitude = float(coord_match.group(1))
                                longitude = float(coord_match.group(2))

                        # Clean address (remove HTML if present)
                        clean_address = address_text
                        if '<a' in address_text:
                            # Extract address from HTML link
                            addr_match = re.search(r'</a>\s*-\s*(.+)', address_text)
                            if addr_match:
                                clean_address = addr_match.group(1).strip()
                            else:
                                # Remove HTML tags
                                clean_address = re.sub(r'<[^>]+>', '', address_text).strip()

                        if start_time and end_time and duration_text:
                            idle_min = parse_duration_to_minutes(duration_text)

                            idle_data.append({
                                'vehicle': vehicle,
                                'idle_start': pd.to_datetime(start_time, errors='coerce'),
                                'idle_end': pd.to_datetime(end_time, errors='coerce'),
                                'idle_duration_min': idle_min,
                                'location_address': clean_address if clean_address else None,
                                'latitude': latitude,
                                'longitude': longitude
                            })
            else:
                # Fallback: generic parsing if column headers not found
                st.write("⚠️ Column headers not found, using generic parsing for Paschal idle report")

                for i, row in enumerate(rows):
                    cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)
                    if not cells:
                        cells = re.findall(r'<td>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)

                    # Look for rows with coordinate data (indicates idle report format)
                    if len(cells) >= 5:
                        coordinate_found = any('coordinate' in cell.lower() for cell in cells)
                        if coordinate_found:
                            continue  # Skip header row

                        # Look for coordinate pattern in cells
                        coordinate_text = ""
                        for cell in cells:
                            if re.search(r'[+-]?\d+\.\d+,\s*[+-]?\d+\.\d+', cell):
                                coordinate_text = cell
                                break

                        if coordinate_text:  # This looks like an idle report row
                            time_pattern = re.compile(r'\d{1,2}:\d{2}(?::\d{2})?|\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}')
                            duration_pattern = re.compile(r'\d+\s*(?:min|minutes?|hrs?|hours?|s|sec|:)')

                            start_time = ""
                            end_time = ""
                            duration = ""
                            address_text = ""

                            # Scan cells for data
                            for cell in cells:
                                cell_clean = cell.strip()
                                if not cell_clean or cell_clean.lower() in ['n/a', 'none', '']:
                                    continue

                                # Check for time
                                if time_pattern.search(cell_clean):
                                    if not start_time:
                                        start_time = cell_clean
                                    elif not end_time:
                                        end_time = cell_clean

                                # Check for duration
                                elif duration_pattern.search(cell_clean.lower()):
                                    duration = cell_clean

                                # Check for address (long text that's not coordinate)
                                elif (len(cell_clean) > 5 and
                                      not re.search(r'[+-]?\d+\.\d+,\s*[+-]?\d+\.\d+', cell_clean) and
                                      not time_pattern.search(cell_clean) and
                                      not duration_pattern.search(cell_clean.lower()) and
                                      not cell_clean.isdigit()):
                                    address_text = cell_clean

                            # Parse coordinates
                            latitude = None
                            longitude = None
                            coord_match = re.search(r'([+-]?\d+\.\d+),\s*([+-]?\d+\.\d+)', coordinate_text)
                            if coord_match:
                                latitude = float(coord_match.group(1))
                                longitude = float(coord_match.group(2))

                            if start_time and end_time:
                                idle_min = parse_duration_to_minutes(duration) if duration else 0

                                idle_data.append({
                                    'vehicle': vehicle,
                                    'idle_start': pd.to_datetime(start_time, errors='coerce'),
                                    'idle_end': pd.to_datetime(end_time, errors='coerce'),
                                    'idle_duration_min': idle_min,
                                    'location_address': address_text if address_text else None,
                                    'latitude': latitude,
                                    'longitude': longitude
                                })

        else:
            # Handle Wizpro HTML format - look for status column and filter for "stopped"
            st.write("🔄 Processing Wizpro HTML format...")

            # First, try to identify column positions by looking for headers
            status_col = -1
            stop_position_col = -1
            start_time_col = -1
            end_time_col = -1
            duration_col = -1

            # Look for header row
            for row in rows[:5]:  # Check first few rows for headers
                cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)
                if not cells:
                    cells = re.findall(r'<td>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)

                for col_idx, cell in enumerate(cells):
                    cell_text = cell.strip().lower()
                    if 'status' in cell_text:
                        status_col = col_idx
                        st.write(f"✅ Found 'Status' column at position {col_idx}")
                    elif 'stop position' in cell_text:
                        stop_position_col = col_idx
                        st.write(f"✅ Found 'Stop Position' column at position {col_idx}")
                    elif 'start' in cell_text and 'time' in cell_text:
                        start_time_col = col_idx
                    elif 'end' in cell_text and 'time' in cell_text:
                        end_time_col = col_idx
                    elif 'duration' in cell_text:
                        duration_col = col_idx

            # If we found the key columns, use positional extraction
            if status_col >= 0 and stop_position_col >= 0:
                st.write("🔍 Using column position mapping for Wizpro HTML")

                for row in rows:
                    cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)
                    if not cells:
                        cells = re.findall(r'<td>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)

                    if len(cells) > max(status_col, stop_position_col):
                        # Check if status is "stopped"
                        status_value = cells[status_col].strip().lower() if status_col < len(cells) else ""
                        if status_value == "stopped":
                            # Extract stop position for address with coordinate parsing
                            raw_address = cells[stop_position_col].strip() if stop_position_col < len(cells) else ""
                            address_text = None
                            latitude = None
                            longitude = None

                            # Parse HTML-formatted address with coordinates
                            if raw_address and '<a' in raw_address:
                                # Extract coordinates from href: q=-1.275198,36.812071&t=m
                                coord_match = re.search(r'q=([+-]?\d+\.\d+),([+-]?\d+\.\d+)', raw_address)
                                if coord_match:
                                    latitude = float(coord_match.group(1))
                                    longitude = float(coord_match.group(2))

                                # Extract address from after </a> -
                                addr_match = re.search(r'</a>\s*-\s*(.+)', raw_address)
                                if addr_match:
                                    address_text = addr_match.group(1).strip()
                                else:
                                    address_text = raw_address  # Fallback to raw if parsing fails
                            else:
                                address_text = raw_address  # Use as-is if not HTML formatted

                            # Look for time and duration data in other cells
                            start_time = None
                            end_time = None
                            duration_text = None

                            for cell in cells:
                                cell_clean = cell.strip()
                                if not cell_clean or cell_clean.lower() in ['n/a', 'none', '']:
                                    continue

                                time_match = re.search(r'\d{1,2}:\d{2}(?::\d{2})?|\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}', cell_clean)
                                if time_match:
                                    if not start_time:
                                        start_time = cell_clean
                                    elif not end_time:
                                        end_time = cell_clean

                                # Look for duration
                                if ('min' in cell_clean.lower() or 's' in cell_clean.lower()) and not duration_text:
                                    duration_text = cell_clean

                            if start_time and end_time:
                                idle_min = parse_duration_to_minutes(duration_text) if duration_text else 0

                                idle_data.append({
                                    'vehicle': vehicle,
                                    'idle_start': pd.to_datetime(start_time, errors='coerce'),
                                    'idle_end': pd.to_datetime(end_time, errors='coerce'),
                                    'idle_duration_min': idle_min,
                                    'location_address': address_text if address_text else None,
                                    'latitude': latitude,
                                    'longitude': longitude
                                })
            else:
                # Fallback: generic parsing if column headers not found
                st.write("⚠️ Column headers not found, using generic parsing")

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

        st.write(f"✅ Total idle records found: {len(idle_data)}")
        return pd.DataFrame(idle_data)

    except Exception as e:
        st.error(f"❌ Error parsing HTML: {e}")
        return pd.DataFrame()

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

    # Handle "XhYmZs" format (e.g., "1h42m49s")
    hms_match = re.match(r'(?:(\d+)\s*h\s*)?(?:(\d+)\s*m\s*)?(?:(\d+)\s*s)?', duration_str, re.IGNORECASE)
    if hms_match:
        hours = int(hms_match.group(1) or 0)
        minutes = int(hms_match.group(2) or 0)
        seconds = int(hms_match.group(3) or 0)
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
    st.header("🛑 Idle / Parking Analyzer")
    st.info("Upload GPS Excel file (.xls/.xlsx) to analyze idle time or parking data. System automatically detects Wizpro or Paschal format.")

    # Get current contractor from session state
    current_contractor = st.session_state.get("contractor", "Unknown")
    contractor_id = get_active_contractor()  # Use active contractor for proper RE admin support
    user_role = st.session_state.get("role", "unknown")

    st.info(f"📋 Current Contractor: {current_contractor}")

    uploaded_file = st.file_uploader("Upload GPS Excel file", type=["xls", "xlsx"])

    if uploaded_file:
        try:
            # Try to read Excel with better error handling
            try:
                df = pd.read_excel(uploaded_file, engine='xlrd')  # Try xlrd for .xls files
                st.info("Excel file (.xls) loaded successfully with xlrd engine.")
            except Exception as excel_error:
                try:
                    df = pd.read_excel(uploaded_file, engine='openpyxl')  # Try openpyxl for .xlsx files
                    st.info("Excel file (.xlsx) loaded successfully with openpyxl engine.")
                except Exception as excel_error2:
                    # Check if it's actually an HTML file masquerading as Excel
                    try:
                        uploaded_file.seek(0)  # Reset file pointer
                        content = uploaded_file.read(100).decode('utf-8', errors='ignore')
                        if '<html' in content.lower() or '<meta' in content.lower():
                            st.info("📄 Detected HTML file (GPS systems sometimes export HTML with .xls extension)")
                            uploaded_file.seek(0)  # Reset file pointer
                            html_content = uploaded_file.read().decode('utf-8', errors='ignore')
                            df = parse_html_idle_report(html_content)
                            if not df.empty:
                                st.success(f"Successfully parsed HTML file! Found {len(df)} idle records.")
                                # For HTML files, we'll treat them as Wizpro format for now
                                file_type = "wizpro"
                                # Skip the format detection and go straight to processing
                                records = []
                                for _, row in df.iterrows():
                                    records.append({
                                        "idle_start": row.get("idle_start"),
                                        "idle_end": row.get("idle_end"),
                                        "idle_duration_min": row.get("idle_duration_min"),
                                        "location_address": row.get("location_address"),
                                        "vehicle": row.get("vehicle", "Unknown Vehicle"),  # ✅ Save vehicle identifier
                                        "contractor_id": contractor_id
                                    })

                                if not records:
                                    st.warning("⚠️ No idle records found in HTML file.")
                                    return

                                result_df = pd.DataFrame(records)
                                st.subheader("📋 Extracted Idle Records from HTML")
                                st.dataframe(result_df)

                                # Save to database option
                                if st.button("💾 Save to Database"):
                                    try:
                                        save_df = result_df.copy()
                                        # Vehicle is already included in result_df
                                        save_df = save_df.rename(columns={
                                            'idle_start': 'idle_start',
                                            'idle_end': 'idle_end',
                                            'idle_duration_min': 'idle_duration_min',
                                            'location_address': 'location_address',
                                            'vehicle': 'vehicle',  # ✅ Keep vehicle identifier
                                            'contractor_id': 'contractor_id'
                                        })
                                        save_df = save_df.dropna(subset=['contractor_id'])
                                        if not save_df.empty:
                                            save_idle_report(save_df, st.session_state.get('user_name', 'Unknown'))
                                            st.success(f"✅ Records saved to database! ({len(save_df)} records)")
                                        else:
                                            st.error("❌ No records with valid contractor IDs to save.")
                                    except Exception as save_error:
                                        st.error(f"❌ Error saving to database: {save_error}")

                                return  # Exit early for HTML files
                            else:
                                st.error("❌ Could not parse HTML content. No idle data found.")
                                return
                        else:
                            st.error(f"Failed to read Excel file: {excel_error}")
                            st.info("Please ensure the file is a valid Excel format (.xls or .xlsx)")
                            return
                    except Exception as html_error:
                        st.error(f"Failed to read file: {excel_error}")
                        st.info("Please ensure the file is a valid Excel or HTML format")
                        return

            st.write(f"File loaded with {len(df)} rows and {len(df.columns)} columns")

            # Detect file type based on columns
            wizpro_cols = ["Status", "Stop position"]
            paschal_cols = ["Stop Duration", "Address"]

            wizpro_score = sum(1 for col in wizpro_cols if col in df.columns)
            paschal_score = sum(1 for col in paschal_cols if col in df.columns)

            if wizpro_score >= paschal_score and wizpro_score > 0:
                file_type = "wizpro"
                st.info("📊 Detected Wizpro format (Status + Stop position columns)")
            elif paschal_score > wizpro_score:
                file_type = "paschal"
                st.info("📊 Detected Paschal format (Stop Duration + Address columns)")
            else:
                st.error("❌ Unknown file format. Expected columns not found.")
                st.error("For Wizpro: 'Status' and 'Stop position' columns")
                st.error("For Paschal: 'Stop Duration' and 'Address' columns")
                st.write("Available columns:", df.columns.tolist())
                return

            records = []

            if file_type == "wizpro":
                st.info("🔄 Processing Wizpro idle data...")
                wizpro_df = parse_wizpro_idle(df)
                if not wizpro_df.empty:
                    # Convert to records format
                    for _, row in wizpro_df.iterrows():
                        records.append({
                            "idle_start": row.get("idle_start"),
                            "idle_end": row.get("idle_end"),
                            "idle_duration_min": row.get("idle_duration_min"),
                            "location_address": row.get("location_address"),
                            "vehicle": row.get("numberplate", "Unknown Vehicle"),  # ✅ Save vehicle identifier
                            "contractor_id": contractor_id
                        })

            elif file_type == "paschal":
                st.info("🔄 Processing Paschal parking data...")
                paschal_df = parse_paschal_idle(df)
                if not paschal_df.empty:
                    # Convert to records format - use duration directly from "Stop Duration" column
                    for _, row in paschal_df.iterrows():
                        records.append({
                            "idle_start": row.get("idle_start"),
                            "idle_end": row.get("idle_end"),
                            "idle_duration_min": row.get("idle_duration_min"),  # ✅ Use from Stop Duration column
                            "location_address": row.get("location_address"),
                            "vehicle": row.get("numberplate", "Unknown Vehicle"),  # ✅ Save vehicle identifier
                            "contractor_id": contractor_id
                        })

            if not records:
                st.warning("⚠️ No idle/parking records found in this file.")
                st.write("This might be because:")
                st.write("- Wizpro files need 'Status' = 'stopped' records")
                st.write("- Paschal files need valid Start/End times")
                return

            result_df = pd.DataFrame(records)
            st.subheader("📋 Extracted Idle/Parking Records")
            st.dataframe(result_df)

            # Save to database option
            if st.button("💾 Save to Database"):
                try:
                    # Prepare data for saving - rename columns to match database schema
                    save_df = result_df.copy()

                    # Vehicle is already included in result_df from records

                    save_df = save_df.rename(columns={
                        'idle_start': 'idle_start',
                        'idle_end': 'idle_end',
                        'idle_duration_min': 'idle_duration_min',
                        'location_address': 'location_address',
                        'vehicle': 'vehicle',  # ✅ Keep vehicle identifier
                        'contractor_id': 'contractor_id'
                    })

                    # Filter out rows without contractor_id
                    save_df = save_df.dropna(subset=['contractor_id'])

                    if not save_df.empty:
                        save_idle_report(save_df, st.session_state.get('user_name', 'Unknown'))
                        st.success(f"✅ Records saved to database! ({len(save_df)} records)")
                    else:
                        st.error("❌ No records with valid contractor IDs to save.")

                except Exception as e:
                    st.error(f"❌ Error saving to database: {e}")

        except Exception as e:
            st.error(f"Error processing file: {e}")
            st.info("Please ensure the file is a valid Excel format (.xls or .xlsx)")

def view_idle_reports_page():
    st.header("📊 Saved Idle/Parking Reports")

    # Get current user role and contractor
    user_role = st.session_state.get("role", "unknown")
    contractor_id = st.session_state.get("contractor_id")

    # Get data with contractor filtering
    if user_role == "re_admin":
        # RE admin can see all data
        df = get_idle_reports(limit=1000)
    else:
        # Regular users see only their contractor's data
        df = get_idle_reports(limit=1000)
        if contractor_id:
            df = df[df['contractor_id'] == contractor_id]

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

    # Ensure idle_start is datetime type and handle mixed data types
    df['idle_start'] = pd.to_datetime(df['idle_start'], errors='coerce')

    # Filter out rows where idle_start is NaT (invalid dates)
    df = df.dropna(subset=['idle_start'])

    if df.empty:
        st.warning("No valid idle start dates available to filter.")
        date_range = []
    else:
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