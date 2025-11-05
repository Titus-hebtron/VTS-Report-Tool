#!/usr/bin/env python3
"""
Database migration script to add GPS tracking columns to vehicles table
Run this script to update the database schema with GPS tracking support
"""

from db_utils import get_sqlalchemy_engine, USE_SQLITE
from sqlalchemy import text

def update_vehicles_schema():
    """Add GPS tracking columns to vehicles table if they don't exist"""
    try:
        engine = get_sqlalchemy_engine()

        with engine.begin() as conn:
            # Check if columns exist and add them if they don't
            if USE_SQLITE:
                # SQLite syntax
                try:
                    conn.execute(text("ALTER TABLE vehicles ADD COLUMN gps_tracking_enabled BOOLEAN DEFAULT FALSE"))
                    print("Added gps_tracking_enabled column")
                except Exception:
                    print("gps_tracking_enabled column already exists")

                try:
                    conn.execute(text("ALTER TABLE vehicles ADD COLUMN gps_tracking_activated_at TIMESTAMP"))
                    print("Added gps_tracking_activated_at column")
                except Exception:
                    print("gps_tracking_activated_at column already exists")

                try:
                    conn.execute(text("ALTER TABLE vehicles ADD COLUMN gps_tracking_deactivated_at TIMESTAMP"))
                    print("Added gps_tracking_deactivated_at column")
                except Exception:
                    print("gps_tracking_deactivated_at column already exists")
            else:
                # PostgreSQL syntax
                try:
                    conn.execute(text("ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS gps_tracking_enabled BOOLEAN DEFAULT FALSE"))
                    print("Added gps_tracking_enabled column")
                except Exception:
                    print("gps_tracking_enabled column already exists")

                try:
                    conn.execute(text("ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS gps_tracking_activated_at TIMESTAMP"))
                    print("Added gps_tracking_activated_at column")
                except Exception:
                    print("gps_tracking_activated_at column already exists")

                try:
                    conn.execute(text("ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS gps_tracking_deactivated_at TIMESTAMP"))
                    print("Added gps_tracking_deactivated_at column")
                except Exception:
                    print("gps_tracking_deactivated_at column already exists")

        print("[SUCCESS] GPS tracking columns added to vehicles table!")

    except Exception as e:
        print(f"[ERROR] Failed to update vehicles schema: {e}")
        raise

if __name__ == "__main__":
    update_vehicles_schema()