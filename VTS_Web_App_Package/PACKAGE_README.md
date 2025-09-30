
# VTS Report Tool - Web App Package

This is a standalone web application package for the VTS Report Tool.

## Quick Start

### Option 1: Run with Python Script
```bash
python run_app.py
```

### Option 2: Manual Start
```bash
# Install dependencies
pip install -r requirements.txt

# Start the web app
streamlit run vts_report_tool.py
```

## Requirements

- Python 3.8 or higher
- Internet connection for map features
- PostgreSQL database (configure in db_utils.py)

## Configuration

1. Set up your PostgreSQL database
2. Update database connection in `db_utils.py`
3. Run the application

## Access

Once started, the app will be available at: http://localhost:8501

## PWA Features

This web app supports Progressive Web App (PWA) features:
- **Install as App**: Click browser menu -> "Install VTS Report Tool"
- **Offline Access**: Works without internet (except maps)
- **Native App Feel**: Runs fullscreen like a mobile app
- **Auto-Updates**: Gets latest features automatically

## Mobile App

For native mobile access, download the mobile app source code from the web interface and build it with Flutter.

## Support

Contact: hebtron25@gmail.com
