import sqlite3
import pandas as pd

# Connect to the database
conn = sqlite3.connect('vts_database.db')

# Query the idle_reports table
query = """
SELECT id, vehicle, idle_start, idle_end, idle_duration_min,
       location_address, latitude, longitude, uploaded_by, uploaded_at, contractor_id
FROM idle_reports
WHERE vehicle LIKE '%KDG%'
ORDER BY id DESC
LIMIT 20
"""

# Also check specific ids
specific_query = """
SELECT id, vehicle, idle_start, idle_end, idle_duration_min,
       location_address, latitude, longitude, uploaded_by, uploaded_at, contractor_id
FROM idle_reports
WHERE id IN (1719, 1720, 1834, 1835)
"""

df = pd.read_sql_query(query, conn)
print("Idle reports with KDG in vehicle:")
print(df)

# Check specific ids
try:
    specific_df = pd.read_sql_query(specific_query, conn)
    print("\nSpecific ids (1719, 1720, 1834, 1835):")
    print(specific_df)
    # Show idle_start for these
    for idx, row in specific_df.iterrows():
        print(f"ID {row['id']}: idle_start = {row['idle_start']}")
except Exception as e:
    print(f"\nError querying specific ids: {e}")

# Check total count
total_count = pd.read_sql_query("SELECT COUNT(*) as total FROM idle_reports", conn)
print(f"\nTotal idle reports: {total_count.iloc[0,0]}")

# Check recent uploads
recent = pd.read_sql_query("SELECT id, vehicle, uploaded_at, contractor_id FROM idle_reports ORDER BY uploaded_at DESC LIMIT 10", conn)
print("\nMost recent uploads:")
print(recent)

conn.close()