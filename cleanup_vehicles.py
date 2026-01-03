#!/usr/bin/env python3
"""
Script to clean up the vehicles table and keep only the designated patrol vehicles
"""

from db_utils import get_sqlalchemy_engine
from sqlalchemy import text

def cleanup_vehicles_table():
    """Remove all vehicles except the designated patrol vehicles"""

    # Define the vehicles to keep
    keep_vehicles = [
        # Wizpro patrol vehicles
        'Patrol_1 (KP1 - KDK 825Y)',
        'Patrol_2 (KP2 - KDS 374F)',
        'Patrol_3 (KP3 - KDG 320Z)',

        # Paschal patrol vehicles
        'Patrol_1 (KP1 - KDD 500X)',
        'Patrol_2 (KP2 - KDC 873G)',

        # Replacement cars
        'Replacement Car',  # Will be kept for all contractors
        'Backup Vehicle',   # Will be kept for all contractors

        # Avators vehicles (as specified)
        'KAV 444A',
        'KAV 555A',
        'KAV 666A',
    ]

    try:
        engine = get_sqlalchemy_engine()

        with engine.begin() as conn:
            # First, show current vehicle count
            result = conn.execute(text("SELECT COUNT(*) as count FROM vehicles"))
            total_before = result.fetchone()[0]
            print(f"Total vehicles before cleanup: {total_before}")

            # Show vehicles that will be kept
            kept_vehicles = []
            for vehicle_name in keep_vehicles:
                result = conn.execute(text("SELECT plate_number, contractor FROM vehicles WHERE plate_number = :name"), {"name": vehicle_name})
                vehicle = result.fetchone()
                if vehicle:
                    kept_vehicles.append(vehicle)

            print("\nVehicles to keep:")
            for vehicle in kept_vehicles:
                print(f"  - {vehicle[0]} ({vehicle[1]})")

            # Delete vehicles not in the keep list
            deleted_count = 0
            if keep_vehicles:
                # Delete vehicles one by one to avoid parameter issues
                for vehicle_name in keep_vehicles:
                    # Skip if this vehicle exists (we want to keep it)
                    pass

                # Delete all vehicles that are NOT in our keep list
                all_vehicles_result = conn.execute(text("SELECT plate_number FROM vehicles"))
                all_vehicles = [row[0] for row in all_vehicles_result.fetchall()]

                for vehicle_name in all_vehicles:
                    if vehicle_name not in keep_vehicles:
                        conn.execute(text("DELETE FROM vehicles WHERE plate_number = :name"), {"name": vehicle_name})
                        deleted_count += 1
            else:
                # If no vehicles to keep, delete all
                result = conn.execute(text("DELETE FROM vehicles"))
                deleted_count = result.rowcount

            print(f"\nDeleted {deleted_count} vehicles")

            # Show final count
            result = conn.execute(text("SELECT COUNT(*) as count FROM vehicles"))
            total_after = result.fetchone()[0]
            print(f"Total vehicles after cleanup: {total_after}")

            # Show remaining vehicles
            result = conn.execute(text("SELECT plate_number, contractor FROM vehicles ORDER BY contractor, plate_number"))
            remaining_vehicles = result.fetchall()

            print("\nRemaining vehicles:")
            for vehicle in remaining_vehicles:
                print(f"  - {vehicle[0]} ({vehicle[1]})")

        print("\nVehicle cleanup completed successfully!")

    except Exception as e:
        print(f"Error during vehicle cleanup: {e}")
        raise

if __name__ == "__main__":
    print("Starting vehicle cleanup...")
    cleanup_vehicles_table()