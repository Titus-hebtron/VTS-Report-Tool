#!/usr/bin/env python3
"""
Setup Patrol Vehicles Script
This script sets up the correct patrol vehicle configuration:
- 3 Wizpro patrol cars
- 2 Paschal patrol cars
- 3 Avators patrol cars
- 2 Recovery/Backup vehicles

Run this script to ensure the database has the correct vehicles configured.
"""
from db_utils import get_sqlalchemy_engine, USE_SQLITE
from sqlalchemy import text

def setup_patrol_vehicles():
    """
    Setup the official patrol vehicle list in the database.
    This ensures we have exactly the vehicles specified and prevents duplicates.
    """
    engine = get_sqlalchemy_engine()
    
    # Official vehicle list as per requirements
    # Total: 3 Wizpro + 2 Paschal + 3 Avators + 2 Recovery = 10 patrol cars
    official_vehicles = [
        # Wizpro patrol cars (3 vehicles)
        ('Wizpro Patrol 1', 'Wizpro'),
        ('Wizpro Patrol 2', 'Wizpro'),
        ('Wizpro Patrol 3', 'Wizpro'),

        # Paschal patrol cars (2 vehicles)
        ('Paschal Patrol 1', 'Paschal'),
        ('Paschal Patrol 2', 'Paschal'),

        # Avators patrol cars (3 vehicles)
        ('Avators Patrol 1', 'Avators'),
        ('Avators Patrol 2', 'Avators'),
        ('Avators Patrol 3', 'Avators'),

        # Recovery/Backup vehicles (2 vehicles - managed by RE Office)
        ('Recovery Vehicle 1', 'RE Office'),
        ('Recovery Vehicle 2', 'RE Office'),
    ]

    print("\n" + "="*70)
    print("PATROL VEHICLES SETUP")
    print("="*70)
    print(f"\nConfiguring {len(official_vehicles)} official patrol vehicles...")
    
    with engine.begin() as conn:
        # Add each vehicle (will be ignored if already exists due to UNIQUE constraint)
        added_count = 0
        existing_count = 0
        
        for plate_number, contractor in official_vehicles:
            try:
                if USE_SQLITE:
                    result = conn.execute(text("""
                        INSERT OR IGNORE INTO vehicles (plate_number, contractor)
                        VALUES (:plate_number, :contractor)
                    """), {
                        "plate_number": plate_number,
                        "contractor": contractor
                    })
                    # SQLite doesn't return rowcount for INSERT OR IGNORE reliably
                    # Check if vehicle exists
                    check = conn.execute(text("""
                        SELECT id FROM vehicles WHERE plate_number = :plate_number
                    """), {"plate_number": plate_number})
                    
                    if check.fetchone():
                        print(f"  ✓ {plate_number} ({contractor})")
                        added_count += 1
                    else:
                        existing_count += 1
                else:
                    result = conn.execute(text("""
                        INSERT INTO vehicles (plate_number, contractor)
                        VALUES (:plate_number, :contractor)
                        ON CONFLICT (plate_number) DO NOTHING
                        RETURNING id
                    """), {
                        "plate_number": plate_number,
                        "contractor": contractor
                    })
                    
                    if result.fetchone():
                        print(f"  ✓ {plate_number} ({contractor})")
                        added_count += 1
                    else:
                        print(f"  - {plate_number} ({contractor}) [already exists]")
                        existing_count += 1
                        
            except Exception as e:
                print(f"  ✗ Error adding {plate_number}: {e}")

    print("\n" + "-"*70)
    print(f"Added: {added_count} vehicles")
    if existing_count > 0:
        print(f"Already existed: {existing_count} vehicles")
    print("-"*70)
    
    print("\n✅ Patrol vehicles setup completed!")
    print("\nVehicle Distribution:")
    print("  • Wizpro:          3 patrol cars")
    print("  • Paschal:         2 patrol cars")
    print("  • Avators:         3 patrol cars")
    print("  • Recovery/Backup: 2 vehicles")
    print("  • TOTAL:          10 patrol cars")

def show_current_vehicles():
    """Display current vehicles grouped by contractor"""
    engine = get_sqlalchemy_engine()
    
    print("\n" + "="*70)
    print("CURRENT VEHICLES IN DATABASE")
    print("="*70)
    
    with engine.begin() as conn:
        result = conn.execute(text("""
            SELECT contractor, COUNT(*) as count
            FROM vehicles
            GROUP BY contractor
            ORDER BY contractor
        """))
        
        summary = result.fetchall()
        
        if not summary:
            print("\n⚠️  No vehicles found in database.")
            return
        
        print("\nVehicles by Contractor:")
        total = 0
        for contractor, count in summary:
            print(f"  • {contractor:15} {count} vehicle(s)")
            total += count
        
        print(f"\n  TOTAL: {total} vehicles")
        
        # Show detailed list
        print("\n" + "-"*70)
        print("Detailed Vehicle List:")
        print("-"*70)
        
        result = conn.execute(text("""
            SELECT plate_number, contractor, 
                   CASE WHEN gps_tracking_enabled THEN 'Active' ELSE 'Inactive' END as gps_status,
                   created_at
            FROM vehicles
            ORDER BY contractor, plate_number
        """))
        
        vehicles = result.fetchall()
        current_contractor = None
        
        for plate, contractor, gps_status, created_at in vehicles:
            if contractor != current_contractor:
                print(f"\n{contractor}:")
                current_contractor = contractor
            print(f"  • {plate:30} GPS: {gps_status}")

def remove_duplicate_vehicles():
    """Remove any duplicate vehicle entries (keeping the oldest one)"""
    engine = get_sqlalchemy_engine()
    
    print("\n" + "="*70)
    print("CHECKING FOR DUPLICATE VEHICLES")
    print("="*70)
    
    with engine.begin() as conn:
        # Find duplicates
        result = conn.execute(text("""
            SELECT plate_number, COUNT(*) as count
            FROM vehicles
            GROUP BY plate_number
            HAVING COUNT(*) > 1
        """))
        
        duplicates = result.fetchall()
        
        if not duplicates:
            print("\n✅ No duplicate vehicles found.")
            return
        
        print(f"\n⚠️  Found {len(duplicates)} duplicate plate numbers:")
        for plate, count in duplicates:
            print(f"  • {plate}: {count} entries")
        
        print("\nRemoving duplicates (keeping oldest entry)...")
        
        if USE_SQLITE:
            for plate, _ in duplicates:
                conn.execute(text("""
                    DELETE FROM vehicles 
                    WHERE id NOT IN (
                        SELECT MIN(id) 
                        FROM vehicles 
                        WHERE plate_number = :plate
                    ) AND plate_number = :plate
                """), {"plate": plate})
        else:
            conn.execute(text("""
                DELETE FROM vehicles a USING vehicles b
                WHERE a.id > b.id 
                AND a.plate_number = b.plate_number
            """))
        
        print("✅ Duplicates removed successfully!")

if __name__ == "__main__":
    import sys
    
    print("\n" + "="*70)
    print("PATROL VEHICLES MANAGEMENT SCRIPT")
    print("="*70)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--show":
        # Just show current vehicles
        show_current_vehicles()
    elif len(sys.argv) > 1 and sys.argv[1] == "--clean":
        # Remove duplicates only
        remove_duplicate_vehicles()
        show_current_vehicles()
    else:
        # Full setup: remove duplicates, add official vehicles, show result
        remove_duplicate_vehicles()
        setup_patrol_vehicles()
        show_current_vehicles()
    
    print("\n" + "="*70)
    print("DONE")
    print("="*70 + "\n")