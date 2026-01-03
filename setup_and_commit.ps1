Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Vehicle Management Fix - Setup and Git Commit" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Step 1: Updating database schema..." -ForegroundColor Yellow
python update_vehicles_schema.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Schema update failed" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host ""

Write-Host "Step 2: Setting up patrol vehicles..." -ForegroundColor Yellow
python setup_patrol_vehicles.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Vehicle setup failed" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host ""

Write-Host "Step 3: Verifying setup..." -ForegroundColor Yellow
python setup_patrol_vehicles.py --show
Write-Host ""

Write-Host "Step 4: Adding files to git..." -ForegroundColor Yellow
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
git add setup_and_commit.ps1
git add README_VEHICLE_FIX.txt
Write-Host ""

Write-Host "Step 5: Committing changes..." -ForegroundColor Yellow
git commit -m "Fix: Update patrol vehicles to 3 Wizpro, 2 Paschal, 3 Avators, 2 Recovery - prevent duplicates with UNIQUE constraint"
Write-Host ""

Write-Host "Step 6: Showing git status..." -ForegroundColor Yellow
git status
Write-Host ""

Write-Host "============================================================" -ForegroundColor Green
Write-Host "Setup and commit completed!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "To push to remote repository, run:" -ForegroundColor Yellow
Write-Host "  git push origin main" -ForegroundColor White
Write-Host ""
Read-Host "Press Enter to exit"