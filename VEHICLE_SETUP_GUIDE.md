# Patrol Vehicles Setup Guide

## Overview
This guide explains how to properly configure and manage patrol vehicles in the GPS Report Tool system to prevent duplicate vehicle entries.

## Vehicle Configuration

The system is configured with the following patrol vehicles:

### Official Vehicle List (Total: 10 patrol cars)

1. **Wizpro** - 3 patrol cars
   - Wizpro Patrol 1
   - Wizpro Patrol 2
   - Wizpro Patrol 3

2. **Paschal** - 2 patrol cars
   - Paschal Patrol 1
   - Paschal Patrol 2

3. **Avators** - 3 patrol cars
   - Avators Patrol 1
   - Avators Patrol 2
   - Avators Patrol 3

4. **Recovery/Backup** - 2 vehicles
   - Recovery Vehicle 1 (RE Office)
   - Recovery Vehicle 2 (RE Office)

## Setup Instructions

### Initial Setup

1. **Update Database Schema** (adds UNIQUE constraint to prevent duplicates):
   ```bash
   python update_vehicles_schema.py
   ```

2. **Setup Patrol Vehicles**:
   ```bash
   python setup_patrol_vehicles.py
   ```

### Maintenance Commands

- **View current vehicles**:
  ```bash
  python setup_patrol_vehicles.py --show
  ```

- **Clean duplicates only**:
  ```bash
  python setup_patrol_vehicles.py --clean
  ```

- **Full setup** (clean + add vehicles + show):
  ```bash
  python setup_patrol_vehicles.py
  ```

## How It Prevents Duplicates

### Database Level
- The `vehicles` table has a **UNIQUE constraint** on the `plate_number` column
- This prevents the same vehicle from being added multiple times

### Application Level
- When incidents, breaks, or pickups are recorded, users select from existing vehicles in a dropdown
- The system references existing vehicle records instead of creating new ones
- All vehicle selections use the official vehicle list from the database

## Using Vehicles in the Application

### For Incident Reports
When creating an incident report, select the patrol car from the dropdown menu. The dropdown shows only the official vehicles configured in the system.

### For Breaks & Pickups
The breaks and pickups page automatically loads vehicles for the logged-in contractor. Users select from this pre-defined list.

### For System Managers (RE Admin)
System managers can:
- View all patrol cars in the "Patrol Car Management" tab
- Add new patrol cars if needed (will be prevented if duplicate)
- Enable/disable GPS tracking for vehicles
- Delete vehicles (if no associated data exists)

## Troubleshooting

### Problem: Duplicate vehicles appearing
**Solution**: Run the cleanup script:
```bash
python setup_patrol_vehicles.py --clean
```

### Problem: Vehicle not appearing in dropdown
**Solution**: 
1. Check if vehicle exists: `python setup_patrol_vehicles.py --show`
2. If missing, run full setup: `python setup_patrol_vehicles.py`

### Problem: Cannot add vehicle (already exists error)
**Solution**: This is expected behavior. The UNIQUE constraint prevents duplicates. If you need to modify a vehicle, delete the old one first (only if no data is associated with it).

## Database Schema

The vehicles table structure:
```sql
CREATE TABLE vehicles (
    id SERIAL PRIMARY KEY,
    plate_number TEXT NOT NULL UNIQUE,  -- UNIQUE constraint prevents duplicates
    contractor TEXT NOT NULL,
    gps_tracking_enabled BOOLEAN DEFAULT FALSE,
    gps_tracking_activated_at TIMESTAMP,
    gps_tracking_deactivated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Notes

- The UNIQUE constraint on `plate_number` is the key to preventing duplicates
- All vehicle references in incidents, breaks, and pickups use the `plate_number` field
- When a vehicle is deleted, associated records remain but are no longer linked to an active vehicle
- Recovery vehicles are managed by "RE Office" contractor for shared access