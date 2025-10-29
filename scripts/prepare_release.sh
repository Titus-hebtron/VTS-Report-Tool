#!/usr/bin/env bash
set -e
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
MOBILE_DIR="$ROOT_DIR/mobile_app"

echo "Preparing release in $MOBILE_DIR"
# copy sample config if runtime config missing
if [ ! -f "$MOBILE_DIR/config.json" ]; then
  echo "No runtime config found; copying sample config."
  cp "$MOBILE_DIR/config.sample.json" "$MOBILE_DIR/config.json"
fi

# Optionally: inject production API URL via env var
if [ -n "$API_BASE_URL" ]; then
  echo "Setting API_BASE_URL=$API_BASE_URL in config.json"
  python - <<PY
import json,sys
p="$MOBILE_DIR/config.json"
c=json.load(open(p))
c["apiBaseUrl"] = "${API_BASE_URL}"
open(p,"w").write(json.dumps(c,indent=2))
print("Wrote $p")
PY
fi

# Build Android APK (requires Flutter installed)
echo "Building Android APK (release)..."
( cd "$MOBILE_DIR" && flutter pub get && flutter build apk --release )

echo "Release build complete. Find APK under $MOBILE_DIR/build/app/outputs/flutter-apk/"
