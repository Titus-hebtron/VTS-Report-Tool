
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

    print("\nStarting web application...")
    print("The app will open in your default browser.")
    print("Press Ctrl+C to stop the server.\n")

    try:
        # Start the Streamlit app
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            "vts_report_tool.py",
            "--server.port", "8501",
            "--server.address", "localhost"
        ])
    except KeyboardInterrupt:
        print("\n\nVTS Report Tool stopped.")
    except Exception as e:
        print(f"\nError starting app: {e}")

if __name__ == "__main__":
    main()
