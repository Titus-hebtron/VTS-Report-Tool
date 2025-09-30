# GPS Report Tool - Complete Documentation

## Project Overview

The GPS Report Tool is a comprehensive web-based application built with Streamlit for managing vehicle tracking system (VTS) data and generating various reports. It provides role-based access for different contractors to manage incident reports, analyze vehicle idle times, track breaks and pickups, and perform accident analysis.

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

### Incident Reporting

1. Select "Incident Report" from the sidebar
2. Choose incident type (Accident or Incident)
3. Select patrol vehicle
4. Fill in incident details including date, time, location, and description
5. Upload photos if available
6. Submit the report

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

### Vehicle Tracking

1. Select a vehicle from the sidebar dropdown
2. View patrol logs in table format
3. Explore locations on the interactive map

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

---

## Troubleshooting

### Common Issues

- **Database Connection Errors**: Verify PostgreSQL is running and connection settings are correct
- **Import Errors**: Ensure all dependencies are installed
- **Permission Errors**: Check user roles and access permissions
- **File Upload Issues**: Verify file formats and size limits

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

## Contact Information

Developed by Hebtron Technologies
Email: hebtron25@gmail.com
© 2025 Hebtron Technologies