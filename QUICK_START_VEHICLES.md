# Quick Start: Fix Vehicle Duplicates

## Problem
The system was creating a new vehicle entry every time an incident, break, or pickup was recorded, leading to duplicate vehicles with the same code.

## Solution
Added database constraints and proper vehicle management to ensure all data references existing vehicles instead of creating duplicates.

## Quick Setup (3 Steps)

### Step 1: Update Database Schema
```bash
python update_vehicles_schema.py
```
This adds a UNIQUE constraint to prevent duplicate vehicle plate numbers.

### Step 2: Setup Official Vehicles
```bash
python setup_patrol_vehicles.py
```
This configures the 10 official patrol vehicles:
- 3 Wizpro patrol cars
- 2 Paschal patrol cars
- 3 Avators patrol cars
- 2 Recovery/Backup vehicles

### Step 3: Verify Setup
```bash
python setup_patrol_vehicles.py --show
```
This displays all vehicles in the database.

## Expected Result

After setup, you should see:
```
Wizpro:
  • Wizpro Patrol 1
  • Wizpro Patrol 2
  • Wizpro Patrol 3

Paschal:
  • Paschal Patrol 1
  • Paschal Patrol 2

Avators:
  • Avators Patrol 1
  • Avators Patrol 2
  • Avators Patrol 3

RE Office:
  • Recovery Vehicle 1
  • Recovery Vehicle 2

TOTAL: 10 vehicles
```

## How It Works Now

1. **Incidents**: When creating an incident report, select patrol car from dropdown → references existing vehicle
2. **Breaks**: When recording a break, select vehicle from dropdown → references existing vehicle
3. **Pickups**: When recording a pickup, select vehicle from dropdown → references existing vehicle

**No new vehicles are created** - all data links to the 10 official vehicles.

## Managing Vehicles

Use the **System Manager** (RE Admin only):
- Go to "Patrol Car Management" tab
- View all vehicles
- Add new vehicles if needed
- Enable/disable GPS tracking
- Delete unused vehicles

## Troubleshooting

**Q: I see duplicate vehicles**
```bash
python setup_patrol_vehicles.py --clean
```

**Q: Vehicle missing from dropdown**
```bash
python setup_patrol_vehicles.py
```

**Q: Can't add vehicle (already exists)**
This is correct! The system prevents duplicates. Use existing vehicle or delete old one first.

## Done!
Your vehicle management system is now configured to prevent duplicates.