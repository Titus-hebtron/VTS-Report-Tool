#!/usr/bin/env python3
"""
Add sample vehicles to the database
"""
from db_utils import get_sqlalchemy_engine
from sqlalchemy import text

def add_sample_vehicles():
    engine = get_sqlalchemy_engine()

    from db_utils import USE_SQLITE
    
    # Note: The patrol cars being monitored through GPRS are the five vehicles from the two contractors:
    # Wizpro (3 vehicles + recovery car) and Paschal (2 vehicles + recovery car)
    # The recovery cars serve as additional slots for backup vehicles
    vehicles = [
        # Wizpro vehicles
        ('KDG 320Z', 'Wizpro'),
        ('KDS 374F', 'Wizpro'),
        ('KDK 825Y', 'Wizpro'),
        ('Replacement Car', 'Wizpro'),
        ('Backup Vehicle', 'Wizpro'),

        # Paschal vehicles
        ('KDC 873G', 'Paschal'),
        ('KDD 500X', 'Paschal'),
        ('Replacement Car', 'Paschal'),
        ('Backup Vehicle', 'Paschal'),

        # Avators vehicles
        ('KAV 444A', 'Avators'),
        ('KAV 555A', 'Avators'),
        ('KAV 666A', 'Avators'),
        ('Replacement Car', 'Avators'),

        # Patrol vehicles for GPS tracking (mapping to actual vehicle plates)
        # Patrol_1 = KP1 = KDK 825Y
        # Patrol_2 = KP2 = KDS 374F
        # Patrol_3 = KP3 = KDG 320Z
        ('Patrol_1 (KP1 - KDK 825Y)', 'Wizpro'),
        ('Patrol_2 (KP2 - KDS 374F)', 'Wizpro'),
        ('Patrol_3 (KP3 - KDG 320Z)', 'Wizpro'),
    ]

    with engine.begin() as conn:
        for plate_number, contractor in vehicles:
            if USE_SQLITE:
                conn.execute(text("""
                    INSERT OR IGNORE INTO vehicles (plate_number, contractor)
                    VALUES (:plate_number, :contractor)
                """), {
                    "plate_number": plate_number,
                    "contractor": contractor
                })
            else:
                conn.execute(text("""
                    INSERT INTO vehicles (plate_number, contractor)
                    VALUES (:plate_number, :contractor)
                    ON CONFLICT DO NOTHING
                """), {
                    "plate_number": plate_number,
                    "contractor": contractor
                })

    print("Sample vehicles added successfully!")

if __name__ == "__main__":
    add_sample_vehicles()