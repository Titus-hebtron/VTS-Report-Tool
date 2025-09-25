#!/usr/bin/env python3
"""
Installation script for geopy package
Run this script to install geopy for address conversion features
"""

import subprocess
import sys
import os

def install_geopy():
    """Install geopy package in the virtual environment"""
    print("Installing geopy package for address conversion...")

    # Check if we're in a virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        # Already in virtual environment
        pip_cmd = [sys.executable, '-m', 'pip', 'install', 'geopy']
    else:
        # Try to use virtual environment
        venv_path = os.path.join(os.path.dirname(__file__), '.venv', 'Scripts', 'python.exe')
        if os.path.exists(venv_path):
            pip_cmd = [venv_path, '-m', 'pip', 'install', 'geopy']
        else:
            # Fall back to system pip
            pip_cmd = [sys.executable, '-m', 'pip', 'install', 'geopy']

    try:
        result = subprocess.run(pip_cmd, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            print("[SUCCESS] Geopy installed successfully!")
            print("Restart your Streamlit application to use address conversion features.")
        else:
            print("[ERROR] Installation failed:")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            print("\nTry manual installation:")
            print("1. Activate virtual environment: .venv\\Scripts\\activate")
            print("2. Install package: python -m pip install geopy")

    except subprocess.TimeoutExpired:
        print("[ERROR] Installation timed out. Try again or install manually.")
    except Exception as e:
        print(f"[ERROR] Installation error: {e}")

if __name__ == "__main__":
    install_geopy()