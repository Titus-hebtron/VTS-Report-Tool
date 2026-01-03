#!/usr/bin/env python3
"""
Database migration script to add GPS tracking columns to vehicles table
and ensure UNIQUE constraint on plate_number to prevent duplicates
Run this script to update the database schema with GPS tracking support
"""

from db_utils import get_sqlalchemy_engine, USE_SQLITE
from sqlalchemy import text

def add_unique_constraint_to_plate_number():
    """Add UNIQUE constraint to plate_number column to prevent duplicate vehicles"""
    engine = get_sqlalchemy_engine()
    
    print("\n" + "="*60)
    print("Adding UNIQUE constraint to plate_number...")
    print("="*60)
    
    try:
        with engine.begin() as conn:
            if USE_SQLITE:
                # SQLite: Check if we need to recreate the table
                # First, check if there are duplicates
                result = conn.execute(text("""
                    SELECT plate_number, COUNT(*) as count
                    FROM vehicles
                    GROUP BY plate_number
                    HAVING COUNT(*) > 1
                """))
                duplicates = result.fetchall()
                
                if duplicates:
                    print(f"Found {len(duplicates)} duplicate plate numbers. Removing duplicates...")
                    for plate, count in duplicates:
                        print(f"  - {plate}: {count} entries")
                        # Keep only the first entry, delete others
                        conn.execute(text("""
                            DELETE FROM vehicles 
                            WHERE id NOT IN (
                                SELECT MIN(id) 
                                FROM vehicles 
                                WHERE plate_number = :plate
                            ) AND plate_number = :plate
                        """), {"plate": plate})
                    print("✅ Duplicates removed")
                
                # Now recreate table with UNIQUE constraint
                print("Recreating vehicles table with UNIQUE constraint...")
                
                # Create backup
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS vehicles_backup AS 
                    SELECT * FROM vehicles
                """))
                
                # Drop old table
                conn.execute(text("DROP TABLE vehicles"))
                
                # Create new table with UNIQUE constraint
                conn.execute(text("""
                    CREATE TABLE vehicles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        plate_number TEXT NOT NULL UNIQUE,
                        contractor TEXT NOT NULL,
                        gps_tracking_enabled BOOLEAN DEFAULT 0,
                        gps_tracking_activated_at TIMESTAMP,
                        gps_tracking_deactivated_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Restore data
                conn.execute(text("""
                    INSERT INTO vehicles 
                    SELECT * FROM vehicles_backup
                """))
                
                # Drop backup
                conn.execute(text("DROP TABLE vehicles_backup"))
                
                print("✅ SQLite: UNIQUE constraint added to plate_number")
                
            else:
                # PostgreSQL: Remove duplicates first
                result = conn.execute(text("""
                    SELECT plate_number, COUNT(*) as count
                    FROM vehicles
                    GROUP BY plate_number
                    HAVING COUNT(*) > 1
                """))
                duplicates = result.fetchall()
                
                if duplicates:
                    print(f"Found {len(duplicates)} duplicate plate numbers. Removing duplicates...")
                    for plate, count in duplicates:
                        print(f"  - {plate}: {count} entries")
                    
                    conn.execute(text("""
                        DELETE FROM vehicles a USING vehicles b
                        WHERE a.id > b.id 
                        AND a.plate_number = b.plate_number
                    """))
                    print("✅ Duplicates removed")
                
                # Check if constraint exists
                result = conn.execute(text("""
                    SELECT constraint_name 
                    FROM information_schema.table_constraints 
                    WHERE table_name = 'vehicles' 
                    AND constraint_type = 'UNIQUE'
                    AND constraint_name LIKE '%plate_number%'
                """))
                
                if result.fetchone() is None:
                    # Add UNIQUE constraint
                    conn.execute(text("""
                        ALTER TABLE vehicles 
                        ADD CONSTRAINT vehicles_plate_number_key 
                        UNIQUE (plate_number)
                    """))
                    print("✅ PostgreSQL: UNIQUE constraint added to plate_number")
                else:
                    print("✅ PostgreSQL: UNIQUE constraint already exists")
        
        print("✅ UNIQUE constraint setup completed!")
        
    except Exception as e:
        print(f"❌ Error adding UNIQUE constraint: {e}")
        import traceback
        traceback.print_exc()

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

        print("\n✅ GPS tracking columns added to vehicles table!")

    except Exception as e:
        print(f"❌ Failed to update vehicles schema: {e}")
        raise

if __name__ == "__main__":
    print("="*60)
    print("VEHICLES TABLE SCHEMA UPDATE")
    print("="*60)
    
    # First add GPS tracking columns
    update_vehicles_schema()
    
    # Then add UNIQUE constraint to prevent duplicates
    add_unique_constraint_to_plate_number()
    
    print("\n" + "="*60)
    print("✅ ALL SCHEMA UPDATES COMPLETED SUCCESSFULLY!")
    print("="*60)