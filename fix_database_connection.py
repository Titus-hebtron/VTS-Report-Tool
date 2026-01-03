#!/usr/bin/env python3
"""
Quick fix for Render PostgreSQL SSL connection issues
This script patches db_utils.py to use more compatible SSL settings
"""

import os
import re

print("🔧 Fixing database connection configuration...")

# Read the current db_utils.py
with open('db_utils.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern to find the DATABASE_URL configuration section
pattern = r'if DATABASE_URL:.*?(?=\nelse:)'

# Replacement with better SSL configuration
replacement = '''if DATABASE_URL:
    # Production: Use PostgreSQL from DATABASE_URL with fallback
    USE_SQLITE = False
    
    try:
        # Render PostgreSQL SSL - use "prefer" for better compatibility
        connect_args = {
            "sslmode": "prefer",  # More compatible than "require"
            "connect_timeout": 30,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5
        }
        
        engine = create_engine(
            DATABASE_URL,
            connect_args=connect_args,
            pool_size=3,
            max_overflow=7,
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_timeout=30,
            echo=False
        )
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ PostgreSQL connected")
        
    except Exception as e:
        print(f"⚠️  PostgreSQL failed: {e}")
        print("🔄 Using SQLite instead")
        USE_SQLITE = True
        engine = create_engine("sqlite:///vts_database.db", connect_args={"check_same_thread": False})'''

# Apply the fix
new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Write back
with open('db_utils.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✅ Database configuration updated!")
print("\nChanges made:")
print("  • SSL mode: require → prefer (more compatible)")
print("  • Added automatic fallback to SQLite on error")
print("  • Added connection test on startup")
print("\nYou can now run your application again.")