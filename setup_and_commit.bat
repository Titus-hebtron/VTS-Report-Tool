@echo off
echo ============================================================
echo Vehicle Management Fix - Setup and Git Commit
echo ============================================================
echo.

echo Step 1: Updating database schema...
python update_vehicles_schema.py
if %errorlevel% neq 0 (
    echo ERROR: Schema update failed
    pause
    exit /b 1
)
echo.

echo Step 2: Setting up patrol vehicles...
python setup_patrol_vehicles.py
if %errorlevel% neq 0 (
    echo ERROR: Vehicle setup failed
    pause
    exit /b 1
)
echo.

echo Step 3: Verifying setup...
python setup_patrol_vehicles.py --show
echo.

echo Step 4: Adding files to git...
git add add_vehicles.py
git add schema.sql
git add update_vehicles_schema.py
git add setup_patrol_vehicles.py
git add test_vehicle_setup.py
git add VEHICLE_SETUP_GUIDE.md
git add QUICK_START_VEHICLES.md
git add IMPLEMENTATION_NOTES.md
git add VEHICLE_FIX_SUMMARY.md
git add setup_and_commit.bat
echo.

echo Step 5: Committing changes...
git commit -m "Fix: Update patrol vehicles to 3 Wizpro, 2 Paschal, 3 Avators, 2 Recovery - prevent duplicates with UNIQUE constraint"
echo.

echo Step 6: Showing git status...
git status
echo.

echo ============================================================
echo Setup and commit completed!
echo ============================================================
echo.
echo To push to remote repository, run:
echo   git push origin main
echo.
pause