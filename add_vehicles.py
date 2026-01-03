#!/usr/bin/env python3
"""
Add/Update vehicles to the database
This script ensures the correct patrol cars are in the system:
- 3 Wizpro patrol cars
- 2 Paschal patrol cars  
- 3 Avators patrol cars
- 2 Recovery/Backup vehicles
"""
from db_utils import get_sqlalchemy_engine, USE_SQLITE
from sqlalchemy import text

def add_or_update_vehicles():
    """
    Add or update vehicles in the database.
    This ensures we have the correct set of patrol cars and prevents duplicates.
    """
    engine = get_sqlalchemy_engine()
    
    # Define the official vehicle list as per requirements
    # Total: 3 Wizpro + 2 Paschal + 3 Avators + 2 Recovery = 10 patrol cars
    vehicles = [
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

        # Recovery/Backup vehicles (2 vehicles - shared across contractors)
        ('Recovery Vehicle 1', 'RE Office'),
        ('Recovery Vehicle 2', 'RE Office'),
    ]

    print("Setting up patrol vehicles in database...")
    print(f"Total vehicles to configure: {len(vehicles)}")
    
    with engine.begin() as conn:
        for plate_number, contractor in vehicles:
            if USE_SQLITE:
                # For SQLite, use INSERT OR IGNORE to prevent duplicates
                conn.execute(text("""
                    INSERT OR IGNORE INTO vehicles (plate_number, contractor)
                    VALUES (:plate_number, :contractor)
                """), {
                    "plate_number": plate_number,
                    "contractor": contractor
                })
            else:
                # For PostgreSQL, use ON CONFLICT DO NOTHING
                conn.execute(text("""
                    INSERT INTO vehicles (plate_number, contractor)
                    VALUES (:plate_number, :contractor)
                    ON CONFLICT (plate_number) DO NOTHING
                """), {
                    "plate_number": plate_number,
                    "contractor": contractor
                })
            print(f"  ✓ {plate_number} ({contractor})")

    print("\n✅ Patrol vehicles configured successfully!")
    print("\nVehicle Summary:")
    print("  - Wizpro: 3 patrol cars")
    print("  - Paschal: 2 patrol cars")
    print("  - Avators: 3 patrol cars")
    print("  - Recovery/Backup: 2 vehicles")
    print("  - Total: 10 patrol cars")

def show_current_vehicles():
    """Display current vehicles in the database"""
    engine = get_sqlalchemy_engine()
    
    print("\n" + "="*60)
    print("CURRENT VEHICLES IN DATABASE")
    print("="*60)
    
    with engine.begin() as conn:
        result = conn.execute(text("""
            SELECT plate_number, contractor, 
                   CASE WHEN gps_tracking_enabled THEN 'Active' ELSE 'Inactive' END as gps_status
            FROM vehicles
            ORDER BY contractor, plate_number
        """))
        
        vehicles = result.fetchall()
        
        if not vehicles:
            print("No vehicles found in database.")
            return
        
        current_contractor = None
        for plate, contractor, gps_status in vehicles:
            if contractor != current_contractor:
                print(f"\n{contractor}:")
                current_contractor = contractor
            print(f"  • {plate} (GPS: {gps_status})")
        
        print(f"\nTotal vehicles: {len(vehicles)}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--show":
        show_current_vehicles()
    else:
        add_or_update_vehicles()
        show_current_vehicles()