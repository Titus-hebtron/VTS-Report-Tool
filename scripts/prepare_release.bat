@echo off
setlocal
set ROOT_DIR=%~dp0\..
set MOBILE_DIR=%ROOT_DIR%\mobile_app

if not exist "%MOBILE_DIR%\config.json" (
  echo Copying sample config...
  copy "%MOBILE_DIR%\config.sample.json" "%MOBILE_DIR%\config.json"
)

if defined API_BASE_URL (
  echo Updating API_BASE_URL in config.json...
  python - <<PY
import json,sys
p=r"%MOBILE_DIR%\config.json"
c=json.load(open(p))
c["apiBaseUrl"] = "%API_BASE_URL%"
open(p,"w").write(json.dumps(c,indent=2))
print("Wrote",p)
PY
)

echo Building Android APK (release)...
pushd "%MOBILE_DIR%"
flutter pub get
flutter build apk --release
popd
echo Done.
endlocal
