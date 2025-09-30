#!/usr/bin/env python3
"""
Web App Packager for VTS Report Tool
Creates a standalone executable from the Streamlit app
"""

import os
import subprocess
import sys
import shutil
from pathlib import Path
import argparse

def create_executable():
    """Create a standalone executable using PyInstaller"""

    print("Creating standalone executable for VTS Report Tool...")

    # Ensure PyInstaller is installed
    try:
        subprocess.run([sys.executable, "-c", "import pyinstaller"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # Create spec file for PyInstaller
    spec_content = '''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['vts_report_tool.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('Kenhalogo.png', '.'),
        ('dejavu-fonts-ttf-2.37', 'dejavu-fonts-ttf-2.37'),
    ],
    hiddenimports=[
        'streamlit',
        'pandas',
        'psycopg2',
        'bcrypt',
        'sqlalchemy',
        'folium',
        'streamlit_folium',
        'streamlit_autorefresh',
        'PIL',
        'matplotlib',
        'seaborn',
        'calendar',
        'datetime',
        'time',
        'io',
        're',
        'json',
        'base64',
        'jwt',
        'jose',
        'passlib',
        'uvicorn',
        'fastapi',
        'pydantic',
        'starlette',
        'uvicorn',
        'click',
        'h11',
        'anyio',
        'sniffio',
        'idna',
        'annotated_types',
        'pydantic_core',
        'typing_extensions',
        'typing_inspection',
        'colorama',
        'bcrypt',
        'cryptography',
        'cffi',
        'pycparser',
        'pyasn1',
        'rsa',
        'ecdsa',
        'python_jose',
        'passlib',
        'fastapi',
        'uvicorn',
        'python_jose',
        'passlib',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='VTS_Report_Tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='Kenhalogo.png' if os.path.exists('Kenhalogo.png') else None,
)
'''

    # Write spec file
    with open('vts_report_tool.spec', 'w') as f:
        f.write(spec_content)

    print("Created PyInstaller spec file")

    # Run PyInstaller
    print("Building executable with PyInstaller...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pyinstaller",
            "--clean",
            "--onefile",
            "vts_report_tool.spec"
        ])

        print("Executable created successfully!")
        print("Find the executable in the 'dist' folder")

        # Create a simple launcher script for users
        launcher_content = '''#!/bin/bash
# VTS Report Tool Launcher
echo "Starting VTS Report Tool..."
echo "The web app will open in your default browser."
echo "Press Ctrl+C to stop the server."
echo ""

# Run the executable
./VTS_Report_Tool

echo ""
echo "VTS Report Tool stopped."
'''

        with open('run_vts_app.sh', 'w') as f:
            f.write(launcher_content)

        # Make launcher executable on Unix systems
        if os.name != 'nt':
            os.chmod('run_vts_app.sh', 0o755)

        print("Created launcher script: run_vts_app.sh")

    except subprocess.CalledProcessError as e:
        print(f"Failed to create executable: {e}")
        return False

    return True

def create_web_app_package():
    """Create a web app package with all necessary files"""

    print("Creating web app package...")

    # Create package directory
    package_dir = "VTS_Web_App_Package"
    if os.path.exists(package_dir):
        shutil.rmtree(package_dir)
    os.makedirs(package_dir)

    # Copy necessary files
    files_to_copy = [
        'vts_report_tool.py',
        'api.py',
        'db_utils.py',
        'schema.sql',
        'requirements.txt',
        'Kenhalogo.png',
        'README.md',
    ]

    dirs_to_copy = [
        'dejavu-fonts-ttf-2.37',
        'static',
    ]

    for file in files_to_copy:
        if os.path.exists(file):
            shutil.copy2(file, package_dir)
            print(f"Copied {file}")

    for dir_name in dirs_to_copy:
        if os.path.exists(dir_name):
            shutil.copytree(dir_name, os.path.join(package_dir, dir_name))
            print(f"Copied {dir_name}")

    # Create requirements.txt if it doesn't exist
    requirements_path = os.path.join(package_dir, 'requirements.txt')
    if not os.path.exists(requirements_path):
        requirements = '''
streamlit>=1.28.0
pandas>=2.0.0
psycopg2-binary>=2.9.0
bcrypt>=4.0.0
sqlalchemy>=2.0.0
folium>=0.14.0
streamlit-folium>=0.17.0
streamlit-autorefresh>=1.0.0
Pillow>=10.0.0
matplotlib>=3.7.0
seaborn>=0.12.0
fastapi>=0.104.0
uvicorn>=0.24.0
python-jose[cryptography]>=3.5.0
passlib[bcrypt]>=1.7.0
python-multipart>=0.0.6
        '''.strip()

        with open(requirements_path, 'w') as f:
            f.write(requirements)
        print("Created requirements.txt")

    # Create run script
    run_script = os.path.join(package_dir, 'run_app.py')
    run_content = '''
#!/usr/bin/env python3
"""
VTS Report Tool Launcher
Run this script to start the web application
"""

import subprocess
import sys
import os

def main():
    print("VTS Report Tool Web App")
    print("=" * 40)

    # Check if required packages are installed
    try:
        import streamlit
        import pandas
        import fastapi
        print("Required packages are installed")
    except ImportError as e:
        print(f"Missing required package: {e}")
        print("Installing requirements...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Packages installed successfully")

    print("\\nStarting web application...")
    print("The app will open in your default browser.")
    print("Press Ctrl+C to stop the server.\\n")

    try:
        # Start the Streamlit app
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            "vts_report_tool.py",
            "--server.port", "8501",
            "--server.address", "localhost"
        ])
    except KeyboardInterrupt:
        print("\\n\\nVTS Report Tool stopped.")
    except Exception as e:
        print(f"\\nError starting app: {e}")

if __name__ == "__main__":
    main()
'''

    with open(run_script, 'w') as f:
        f.write(run_content)

    if os.name != 'nt':  # Make executable on Unix
        os.chmod(run_script, 0o755)

    print("Created run_app.py launcher")

    # Create README for the package
    readme_content = '''
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
'''

    with open(os.path.join(package_dir, 'PACKAGE_README.md'), 'w') as f:
        f.write(readme_content)

    print("Created package README")

    # Create ZIP archive
    shutil.make_archive(package_dir, 'zip', package_dir)
    print(f"Created ZIP archive: {package_dir}.zip")

    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VTS Report Tool - Web App Packager")
    parser.add_argument("method", choices=["exe", "package"], help="Packaging method: exe for executable, package for Python package")
    parser.add_argument("--auto", action="store_true", help="Run without interactive prompts")

    args = parser.parse_args()

    print("VTS Report Tool - Web App Packager")
    print("=" * 40)

    if args.method == "exe":
        print("Creating standalone executable...")
        success = create_executable()
    elif args.method == "package":
        print("Creating web app package...")
        success = create_web_app_package()
    else:
        print("Invalid method")
        sys.exit(1)

    if success:
        print("\\nPackaging completed successfully!")
        print("Check the output files in the current directory")
    else:
        print("\\nPackaging failed")
        sys.exit(1)