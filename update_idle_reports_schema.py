#!/usr/bin/env python3
"""
Database migration script to add location columns to idle_reports table
Run this script to update the database schema with location support
"""

import psycopg2
import traceback

# Database configuration
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "Hebtron123"

def update_idle_reports_schema():
    """Add location columns to idle_reports table if they don't exist"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        cur = conn.cursor()

        # Check if location_address column exists
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'idle_reports' AND column_name = 'location_address'
        """)

        if not cur.fetchone():
            print("Adding location columns to idle_reports table...")

            # Add location columns
            cur.execute("""
                ALTER TABLE idle_reports
                ADD COLUMN IF NOT EXISTS location_address TEXT,
                ADD COLUMN IF NOT EXISTS latitude DECIMAL(10,8),
                ADD COLUMN IF NOT EXISTS longitude DECIMAL(11,8)
            """)

            conn.commit()
            print("[SUCCESS] Location columns added to idle_reports table!")
        else:
            print("[INFO] Location columns already exist in idle_reports table.")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"[ERROR] Failed to update database schema: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    update_idle_reports_schema()