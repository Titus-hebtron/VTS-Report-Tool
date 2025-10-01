#!/usr/bin/env python3
"""
Remove old vehicle entries from the database
"""
from db_utils import get_sqlalchemy_engine
from sqlalchemy import text

def remove_old_vehicles():
    engine = get_sqlalchemy_engine()

    old_vehicles = ['KCB 111P', 'KCB 222P', 'KCB 333P', 'KBZ 123A', 'KBZ 456B', 'KBZ 789C']

    with engine.begin() as conn:
        for plate_number in old_vehicles:
            conn.execute(text("""
                DELETE FROM vehicles WHERE plate_number = :plate_number
            """), {
                "plate_number": plate_number
            })

    print("Old vehicles removed successfully!")

if __name__ == "__main__":
    remove_old_vehicles()