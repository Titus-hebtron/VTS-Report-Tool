#!/usr/bin/env python3
"""
Add sample vehicles to the database
"""
from db_utils import get_sqlalchemy_engine
from sqlalchemy import text

def add_sample_vehicles():
    engine = get_sqlalchemy_engine()

    # Note: The patrol cars being monitored through GPRS are the five vehicles from the two contractors:
    # Wizpro (3 vehicles + recovery car) and Paschal (2 vehicles + recovery car)
    # The recovery cars serve as additional slots for backup vehicles
    vehicles = [
        # Wizpro vehicles
        ('KDG 320Z', 'Wizpro'),
        ('KDS 374F', 'Wizpro'),
        ('KDK 825Y', 'Wizpro'),
        ('Replacement Car', 'Wizpro'),

        # Paschal vehicles
        ('KDC 873G', 'Paschal'),
        ('KDD 500X', 'Paschal'),
        ('Replacement Car', 'Paschal'),

        # Avators vehicles
        ('KAV 444A', 'Avators'),
        ('KAV 555A', 'Avators'),
        ('KAV 666A', 'Avators'),
        ('Replacement Car', 'Avators'),
    ]

    with engine.begin() as conn:
        for plate_number, contractor in vehicles:
            conn.execute(text("""
                INSERT OR IGNORE INTO vehicles (plate_number, contractor)
                VALUES (:plate_number, :contractor)
            """), {
                "plate_number": plate_number,
                "contractor": contractor
            })

    print("Sample vehicles added successfully!")

if __name__ == "__main__":
    add_sample_vehicles()