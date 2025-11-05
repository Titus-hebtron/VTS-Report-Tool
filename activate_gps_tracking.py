#!/usr/bin/env python3
"""
Script to activate GPS tracking for patrol vehicles permanently (24/7)
This script activates GPS tracking for all patrol vehicles and keeps them active
unless manually deactivated by an administrator.
"""

from db_utils import get_sqlalchemy_engine
from sqlalchemy import text
from datetime import datetime

def activate_gps_tracking_for_patrol_vehicles():
    """Activate GPS tracking for all patrol vehicles that contain 'Patrol' in their name"""
    try:
        engine = get_sqlalchemy_engine()

        with engine.begin() as conn:
            # Update all patrol vehicles to have GPS tracking enabled
            result = conn.execute(text("""
                UPDATE vehicles
                SET gps_tracking_enabled = TRUE,
                    gps_tracking_activated_at = CURRENT_TIMESTAMP,
                    gps_tracking_deactivated_at = NULL
                WHERE plate_number LIKE '%Patrol%'
            """))

            print(f"Activated GPS tracking for {result.rowcount} patrol vehicles")

            # Show which vehicles were activated
            activated_vehicles = conn.execute(text("""
                SELECT plate_number, contractor
                FROM vehicles
                WHERE gps_tracking_enabled = TRUE AND plate_number LIKE '%Patrol%'
                ORDER BY contractor, plate_number
            """)).fetchall()

            if activated_vehicles:
                print("\nPatrol vehicles with active GPS tracking:")
                for vehicle in activated_vehicles:
                    print(f"  - {vehicle[0]} ({vehicle[1]})")

        print("\nGPS tracking is now permanently active (24/7) for all patrol vehicles!")
        print("Note: GPS tracking will remain active until manually deactivated by an administrator.")

    except Exception as e:
        print(f"❌ Error activating GPS tracking: {e}")
        raise

def deactivate_gps_tracking(vehicle_id=None, plate_number=None):
    """Deactivate GPS tracking for a specific vehicle or all vehicles"""
    try:
        engine = get_sqlalchemy_engine()

        with engine.begin() as conn:
            if vehicle_id:
                # Deactivate specific vehicle by ID
                result = conn.execute(text("""
                    UPDATE vehicles
                    SET gps_tracking_enabled = FALSE,
                        gps_tracking_deactivated_at = CURRENT_TIMESTAMP
                    WHERE id = :vehicle_id
                """), {"vehicle_id": vehicle_id})
            elif plate_number:
                # Deactivate specific vehicle by plate number
                result = conn.execute(text("""
                    UPDATE vehicles
                    SET gps_tracking_enabled = FALSE,
                        gps_tracking_deactivated_at = CURRENT_TIMESTAMP
                    WHERE plate_number = :plate_number
                """), {"plate_number": plate_number})
            else:
                # Deactivate all vehicles
                result = conn.execute(text("""
                    UPDATE vehicles
                    SET gps_tracking_enabled = FALSE,
                        gps_tracking_deactivated_at = CURRENT_TIMESTAMP
                    WHERE gps_tracking_enabled = TRUE
                """))

            print(f"✅ Deactivated GPS tracking for {result.rowcount} vehicles")

    except Exception as e:
        print(f"❌ Error deactivating GPS tracking: {e}")
        raise

def get_gps_tracking_status():
    """Get the current GPS tracking status for all vehicles"""
    try:
        engine = get_sqlalchemy_engine()

        with engine.begin() as conn:
            result = conn.execute(text("""
                SELECT plate_number, contractor, gps_tracking_enabled,
                       gps_tracking_activated_at, gps_tracking_deactivated_at
                FROM vehicles
                ORDER BY contractor, plate_number
            """)).fetchall()

            return result

    except Exception as e:
        print(f"❌ Error getting GPS tracking status: {e}")
        raise

if __name__ == "__main__":
    print("Activating GPS tracking for all patrol vehicles...")
    activate_gps_tracking_for_patrol_vehicles()

    print("\nCurrent GPS tracking status:")
    status = get_gps_tracking_status()
    active_count = 0
    for vehicle in status:
        plate, contractor, enabled, activated_at, deactivated_at = vehicle
        if enabled:
            active_count += 1
            print(f"  [ACTIVE] {plate} ({contractor}) - activated at {activated_at}")
        else:
            print(f"  [INACTIVE] {plate} ({contractor})")

    print(f"\nTotal active GPS tracking: {active_count} vehicles")