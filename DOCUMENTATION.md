# GPS Report Tool - Complete Documentation

## Project Overview

The GPS Report Tool is a comprehensive web-based application built with Streamlit for managing vehicle tracking system (VTS) data and generating various reports. It provides role-based access for different contractors to manage incident reports, analyze vehicle idle times, track breaks and pickups, and perform accident analysis.

### Monitored Vehicles

The patrol cars being monitored through GPRS are the five vehicles from the two contractors: Wizpro (3 vehicles + recovery car) and Paschal (2 vehicles + recovery car). The recovery cars serve as additional slots for backup vehicles, ensuring continuous coverage and redundancy in the vehicle tracking system. The real-time GPS monitoring focuses on these vehicles from Wizpro and Paschal contractors only.

## Table of Contents

1. [Project Overview](#project-overview)
2. [Features](#features)
3. [Technology Stack](#technology-stack)
4. [Database Schema](#database-schema)
5. [Application Structure](#application-structure)
6. [Installation and Setup](#installation-and-setup)
7. [User Manual](#user-manual)
8. [API Documentation](#api-documentation)
9. [Troubleshooting](#troubleshooting)
10. [Contributing](#contributing)

---

## Features

### Core Functionality
- **Role-based Authentication**: Secure login system with different access levels (admin, control, patrol, re_admin)
- **Incident Reporting**: Comprehensive incident and accident reporting with photo uploads
- **Idle Time Analysis**: Automated analysis of vehicle idle periods from GPS data
- **Breaks & Pickups Management**: Track vehicle breaks and pickup activities
- **Report Search & Filtering**: Advanced search capabilities across all reports
- **Real-time Vehicle Tracking**: Live map view of vehicle locations and activities
- **Accident Analysis**: Specialized tools for accident data analysis

### User Roles & Permissions
- **Admin**: Full access to all features including incident reports, idle analysis, and management tools
- **Control**: Access to incident reports, idle analysis, and operational tools
- **Patrol**: Limited access to incident reporting and breaks/pickups
- **RE Admin**: Full administrative access across all contractors

### Supported Contractors
- Wizpro
- Paschal
- RE Office
- Avators

---

## Technology Stack

- **Frontend**: Streamlit
- **Backend**: Python
- **Database**: PostgreSQL
- **Mapping**: Folium, Streamlit-Folium
- **Data Processing**: Pandas, SQLAlchemy
- **Authentication**: bcrypt for password hashing

---

## Database Schema

The application uses a PostgreSQL database with the following main tables:

- `users`: User authentication and role management
- `contractors`: Contractor information
- `incident_reports`: Incident and accident reports with detailed information
- `incident_images`: Photo attachments for incidents
- `idle_reports`: Vehicle idle time records
- `breaks`: Vehicle break periods
- `pickups`: Vehicle pickup activities
- `accidents`: Accident records
- `vehicles`: Vehicle information
- `patrol_logs`: GPS tracking logs

---

## Application Structure

### Main Application Files
- `vts_report_tool.py`: Main Streamlit application with routing and authentication
- `app.py`: Standalone idle time analyzer
- `auth.py`: Authentication utilities

### Page Modules
- `incident_report.py`: Incident reporting interface
- `idle_time_analyzer_page.py`: Idle time analysis tools
- `breaks_pickups_page.py`: Breaks and pickups management
- `report_search.py`: Report search functionality
- `search_page.py`: General search interface
- `accident_analysis.py`: Accident data analysis

### Utilities
- `db_utils.py`: Database connection and utility functions
- `schema.sql`: Database schema definition

---

## Installation and Setup

### Prerequisites

- Python 3.8 or higher
- PostgreSQL database
- Git (for cloning the repository)

### Database Setup

1. Install PostgreSQL and create a database for the application
2. Run the schema.sql file to create the required tables:

```bash
psql -d your_database_name -f schema.sql
```

3. Configure database connection settings in `db_utils.py`

### Application Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd gps-report-tool
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables for database connection (if needed)

### Running the Application

#### Main VTS Report Tool
```bash
streamlit run vts_report_tool.py
```

#### Standalone Idle Time Analyzer
```bash
streamlit run app.py
```

The application will be available at `http://localhost:8501`

### Initial Setup

1. Add contractors using the provided scripts (e.g., `insert_contractors.py`)
2. Create user accounts with appropriate roles
3. Configure vehicle data if not already present

### Configuration

- Update database connection strings in `db_utils.py`
- Modify contractor options in the application files as needed
- Configure logo and branding assets

---

## Custom Calendar System

The application uses a custom calendar system for monthly reports:

- **Calendar Start**: June 9, 2025
- **Month Structure**: Every month has exactly 4 weeks
- **Week Structure**: Every week has exactly 7 days
- **Month Length**: Exactly 28 days (4 weeks × 7 days)

### Calendar Examples

**June 2025 (First Month)**:
- Data Range: 2025-06-09 to 2025-07-06 (28 days)
- Week 1: 2025-06-09 to 2025-06-15
- Week 2: 2025-06-16 to 2025-06-22
- Week 3: 2025-06-23 to 2025-06-29
- Week 4: 2025-06-30 to 2025-07-06

**July 2025 (Second Month)**:
- Data Range: 2025-07-07 to 2025-08-03 (28 days)
- Week 1: 2025-07-07 to 2025-07-13
- Week 2: 2025-07-14 to 2025-07-20
- Week 3: 2025-07-21 to 2025-07-27
- Week 4: 2025-07-28 to 2025-08-03

**August 2025 (Third Month)**:
- Data Range: 2025-08-04 to 2025-08-31 (28 days)
- Week 1: 2025-08-04 to 2025-08-10
- Week 2: 2025-08-11 to 2025-08-17
- Week 3: 2025-08-18 to 2025-08-24
- Week 4: 2025-08-25 to 2025-08-31

## User Manual

### Getting Started

1. **Login**: Access the application and log in with your contractor, username, and password
2. **Role Selection**: Your access level determines available features
3. **Navigation**: Use the sidebar to navigate between different modules

#### Login Page Screenshot
![Login Page](screenshots/login_page.png)
*Figure 1: Main login interface showing contractor selection and authentication fields*

#### Main Dashboard Screenshot
![Main Dashboard](screenshots/main_dashboard.png)
*Figure 2: Main application dashboard with sidebar navigation and contractor selection*

### Incident Reporting

1. Select "Incident Report" from the sidebar
2. Choose incident type (Accident or Incident)
3. Select patrol vehicle
4. Fill in incident details including date, time, location, and description
5. Upload photos if available
6. Submit the report

#### Incident Report Form Screenshot
![Incident Report Form](screenshots/incident_report_form.png)
*Figure 3: Incident reporting interface with all required fields and photo upload capability*

#### Incident Report Template Preview
![Incident Report Template](screenshots/incident_report_template.png)
*Figure 4: Generated Excel template showing incident details in professional format*

### Unified Idle/Parking Analyzer

1. Select "Idle Time Analyzer" from the sidebar
2. **System automatically detects file format** based on column structure:
    - **Wizpro format**: Detected by "Status" and "Stop position" columns
    - **Paschal format**: Detected by "Stop Duration" and "Address" columns
    - **HTML files**: Automatically detected and parsed for both Wizpro and Paschal formats (GPS systems sometimes export HTML with .xls extension)
3. Upload Excel file (.xls/.xlsx) or HTML file - no manual format selection needed
4. **Automatic processing**:
    - Wizpro: Scans for "Status" column (with various naming variations), filters only "stopped" records, uses corresponding "Stop Position" data for location_address
    - Paschal: Maps "Stop Duration" → `idle_duration_min` (parses formats like "1h42m49s"), "Address" → `location_address`
    - HTML: Parses table data for idle records, identifying column headers by name with Wizpro detection prioritized over Paschal
    - **HTML Address Parsing**: Extracts coordinates from Google Maps URLs (`q=-1.275198,36.812071`) and addresses from after `</a> - ` pattern
    - **Vehicle identification**: Saves extracted vehicle names for data tracking
    - **Debugging**: Shows available status values and filtering results for troubleshooting
    - **Format Detection**: Wizpro indicators ('wizpro', 'stopped', 'stop position') checked before Paschal indicators
    - **Coordinate Extraction**: Automatically parses latitude/longitude from HTML-formatted location data
5. View extracted records in clean table format
6. Save all data to unified database table (filtered by your contractor)
7. Download results as CSV

#### Idle Time Analyzer Interface Screenshot
![Idle Time Analyzer](screenshots/idle_time_analyzer.png)
*Figure 5: Idle time analyzer showing file upload, automatic format detection, and data processing*

#### Idle Reports View Screenshot
![Idle Reports View](screenshots/idle_reports_view.png)
*Figure 6: Saved idle reports interface with filtering and contractor-based access control*

#### Code Example: Idle Time Analysis
```python
# Example of how the idle time analyzer processes Wizpro format
def parse_wizpro_idle(df):
    df.columns = df.columns.str.strip().str.lower()

    # Filter for "stopped" status only
    if 'status' in df.columns:
        df = df[df['status'].str.lower().str.strip() == 'stopped']

    # Extract duration and convert to minutes
    df['idle_duration_min'] = pd.to_numeric(df['duration'], errors='coerce')

    # Parse timestamps with dayfirst=True for DD/MM/YYYY format
    df['idle_start'] = pd.to_datetime(df['start'], dayfirst=True, errors='coerce')
    df['idle_end'] = pd.to_datetime(df['end'], dayfirst=True, errors='coerce')

    return df[['vehicle', 'idle_start', 'idle_end', 'idle_duration_min', 'location']]
```

### Paschal Parking Analyzer (Alternative)

1. **Available for Paschal contractors only**: Dedicated page for complex Paschal formats
2. Select "Paschal Parking Analyzer" from the sidebar
3. Upload Excel file with Paschal's specific parking format:
   - **Row 1**: Title with vehicle plate in brackets, e.g., "Parking Details(KDC873G)"
   - **Row 2-3**: Date range and other metadata
   - **Row 5 onwards**: Parking data table with columns: "# | Start Time | End Time | Stop Duration | Address"
   - **Address column**: Spans two rows per entry:
     - First row: Coordinates (e.g., "1.161935S,36.957880E")
     - Second row: Place name (e.g., "A2, Ruiru, Kenya")
4. Advanced processing with address merging and vehicle extraction
5. View processed data in clean table format with summary statistics
6. Download results as CSV or save directly to database

### Managing Breaks & Pickups

1. Select "Breaks & Pickups" from the sidebar
2. Choose vehicle and date
3. Add break or pickup entries with start/end times
4. Save the records

### Report Search

1. Select "Report Search" from the sidebar
2. Choose report type and apply filters
3. View and export search results

#### Search Page Interface Screenshot
![Search Page](screenshots/search_page.png)
*Figure 7: Search interface showing contractor-based filtering and data export options*

#### Code Example: Contractor-Based Filtering
```python
# Example of contractor-based filtering in search_page.py
contractor = st.session_state.get("contractor")
if contractor and contractor.lower() in ['wizpro', 'paschal']:
    contractor_id = 1 if contractor.lower() == 'wizpro' else 2
    query += " AND contractor_id = ?"
    params = params + (contractor_id,)
```

### Vehicle Tracking

1. Select a vehicle from the sidebar dropdown
2. View patrol logs in table format
3. Explore locations on the interactive map

#### Vehicle Tracking Map Screenshot
![Vehicle Tracking](screenshots/vehicle_tracking.png)
*Figure 8: Interactive map showing vehicle patrol routes and locations*

#### Code Example: Map Integration
```python
# Example of Folium map integration for vehicle tracking
import folium
from streamlit_folium import st_folium

# Create map centered on vehicle location
m = folium.Map(location=[latitude, longitude], zoom_start=12)

# Add vehicle markers
folium.Marker(
    [row["latitude"], row["longitude"]],
    popup=f"Time: {row['timestamp']}<br>Activity: {row['activity']}",
    icon=folium.Icon(color="blue", icon="car", prefix="fa")
).add_to(m)

# Display in Streamlit
st_folium(m, width="100%", height=500)
```

### Accident Analysis

1. Select "Accident Analysis" (RE Admin only)
2. Upload accident data files
3. Generate analysis reports

### Monthly Consolidated Report (4 Weeks + Grand Total)

1. Select "Report Search" from the sidebar
2. Go to the "Monthly Consolidated Report" section
3. Pick any date in the desired month
4. The system shows the custom month date range (e.g., "Custom month range: 2025-06-09 to 2025-07-06")
5. Click "Preview Monthly Data" to view the data before downloading
6. The preview shows:
   - Vehicle summary with total idle minutes and record counts for your contractor
   - Information about how many unique vehicles have data
7. After reviewing the preview, click "📥 Download Full Monthly Report" to generate the complete Excel file
8. The system generates an Excel file with separate sheets for each vehicle that has data in that custom month
9. Sheet names are automatically created from normalized license plates (e.g., "KDK825Y", "KDG320Z")
10. Each sheet contains the 4-week breakdown with day-by-day data, weekly totals, and monthly grand total
11. Availability percentages are calculated for each week and overall month

---

## API Documentation

The application uses direct database connections rather than REST APIs. Key database operations include:

### Incident Reports
- `save_incident_report(data, uploaded_by)`: Save new incident report
- `get_recent_incident_reports(limit)`: Retrieve recent reports
- `save_incident_image(report_id, image_data, image_name)`: Save incident photos

### Idle Reports
- `save_idle_report(data)`: Save idle time analysis results
- `get_idle_reports_for_contractor(contractor_id)`: Retrieve idle reports

### Authentication
- User verification through bcrypt password checking
- Role-based access control

### Code Example: Database Connection
```python
# Example from db_utils.py - Database connection setup
def get_sqlalchemy_engine():
    """Create and return SQLAlchemy engine for database operations"""
    if USE_SQLITE:
        engine = create_engine("sqlite:///vts_database.db", connect_args={"check_same_thread": False})
    else:
        # PostgreSQL configuration
        engine = create_engine(f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    return engine

def save_idle_report(idle_df, uploaded_by):
    """Save multiple idle records using bulk insert"""
    if idle_df.empty:
        return
    contractor_id = get_active_contractor()
    idle_df = idle_df.copy()
    idle_df.columns = [c.lower() for c in idle_df.columns]
    idle_df['uploaded_by'] = uploaded_by
    idle_df['contractor_id'] = contractor_id

    # Only keep columns that exist in the database table
    valid_columns = ['vehicle', 'idle_start', 'idle_end', 'idle_duration_min',
                     'location_address', 'latitude', 'longitude', 'description',
                     'uploaded_by', 'contractor_id']
    idle_df = idle_df[[col for col in valid_columns if col in idle_df.columns]]

    engine = get_sqlalchemy_engine()
    try:
        idle_df.to_sql('idle_reports', engine, if_exists='append', index=False)
    except Exception as e:
        print("❌ Error saving idle report:", e)
        traceback.print_exc()
```

---

## Troubleshooting

### Common Issues

- **Database Connection Errors**: Verify PostgreSQL is running and connection settings are correct
- **Import Errors**: Ensure all dependencies are installed
- **Permission Errors**: Check user roles and access permissions
- **File Upload Issues**: Verify file formats and size limits

### Contractor-Based Access Issues

- **Can't see idle reports**: Ensure you're logged in with the correct contractor (Wizpro/Paschal)
- **Search results empty**: Check that the selected contractor in sidebar matches your login contractor
- **Date parsing errors**: The system uses DD/MM/YYYY format - ensure your data matches this format

### Code Example: Debugging Contractor Access
```python
# Debug contractor access in session
st.write("Current contractor:", st.session_state.get("contractor"))
st.write("Contractor ID:", st.session_state.get("contractor_id"))
st.write("User role:", st.session_state.get("role"))

# Check database records for your contractor
contractor_id = st.session_state.get("contractor_id")
if contractor_id:
    df = get_idle_reports_for_contractor(contractor_id)
    st.write(f"Found {len(df)} records for contractor {contractor_id}")
```

### Logs and Debugging

- Check Streamlit logs in the terminal for error messages
- Verify database logs for connection issues
- Ensure all required columns are present in uploaded files

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and test thoroughly
4. Submit a pull request

---

## Converting to PDF

To create a PDF version of this documentation:

1. Use a markdown to PDF converter like:
   - Pandoc: `pandoc DOCUMENTATION.md -o documentation.pdf`
   - Online converters like markdown-pdf.com
   - VS Code extensions for markdown PDF export

2. Or print the markdown file as PDF from your browser or text editor

---

## License

© 2025 Hebtron Technologies. All rights reserved.

## Screenshots Directory Structure

Create a `screenshots/` directory in your project root and add the following images:

```
screenshots/
├── login_page.png              # Login interface
├── main_dashboard.png          # Main app dashboard
├── incident_report_form.png    # Incident reporting form
├── incident_report_template.png # Excel template output
├── idle_time_analyzer.png      # Idle analyzer interface
├── idle_reports_view.png       # Saved idle reports view
├── search_page.png             # Search and filtering interface
└── vehicle_tracking.png        # Map view for vehicle tracking
```

## Project Preview Code Snippets

### Main Application Entry Point
```python
# vts_report_tool.py - Main application
import streamlit as st
from db_utils import init_database_if_needed

# Initialize database
init_database_if_needed()

# Main app logic with role-based routing
if not st.session_state["login_state"]:
    # Show login page
    show_login_page()
else:
    # Show main application based on user role
    show_main_app()
```

### Contractor-Based Data Filtering
```python
# Example from search_page.py
def search_page():
    # Get contractor from session
    contractor = st.session_state.get("contractor")
    if contractor and contractor.lower() in ['wizpro', 'paschal']:
        contractor_id = 1 if contractor.lower() == 'wizpro' else 2
        query += " AND contractor_id = ?"
        params = params + (contractor_id,)

    # Execute filtered query
    df = pd.read_sql_query(query, engine, params=params)
    return df
```

### Automatic File Format Detection
```python
# From idle_time_analyzer_page.py
def detect_idle_format(df):
    columns = df.columns.str.strip().str.lower()

    # Wizpro indicators
    wizpro_indicators = ['object', 'start', 'end', 'duration']
    wizpro_score = sum(1 for col in wizpro_indicators if col in columns)

    # Paschal indicators
    paschal_indicators = ['start time', 'end time', 'stop duration']
    paschal_score = sum(1 for col in paschal_indicators if col in columns)

    return 'wizpro' if wizpro_score > paschal_score else 'paschal'
```

## Contact Information

Developed by Hebtron Technologies
Email: hebtron25@gmail.com
© 2025 Hebtron Technologies