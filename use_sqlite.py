#!/usr/bin/env python3
"""
Quick script to disable PostgreSQL and use SQLite instead
This is the simplest solution for local development
"""

import os

print("🔄 Switching to SQLite for local development...")

# Check if .env exists
if os.path.exists('.env'):
    with open('.env', 'r') as f:
        lines = f.readlines()
    
    # Comment out DATABASE_URL
    new_lines = []
    for line in lines:
        if line.strip().startswith('DATABASE_URL='):
            new_lines.append(f"# {line}")
            print(f"  ✓ Commented out: {line.strip()[:50]}...")
        else:
            new_lines.append(line)
    
    with open('.env', 'w') as f:
        f.writelines(new_lines)
    
    print("✅ .env file updated - DATABASE_URL commented out")
else:
    print("ℹ️  No .env file found - app will use SQLite by default")

print("\n📊 Your app will now use SQLite (vts_database.db)")
print("   This is perfect for local development!")
print("\nRun your app with:")
print("   streamlit run auth.py")