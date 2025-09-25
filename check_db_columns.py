#!/usr/bin/env python3
"""
Check what columns exist in the idle_reports table
"""

import psycopg2

# Database configuration
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "Hebtron123"

def check_idle_reports_columns():
    """Check what columns exist in idle_reports table"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        cur = conn.cursor()

        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'idle_reports'
            ORDER BY ordinal_position
        """)

        columns = cur.fetchall()
        print("Columns in idle_reports table:")
        for col in columns:
            print(f"  {col[0]}: {col[1]} ({'NULL' if col[2] == 'YES' else 'NOT NULL'})")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"[ERROR] Failed to check database: {e}")

if __name__ == "__main__":
    check_idle_reports_columns()