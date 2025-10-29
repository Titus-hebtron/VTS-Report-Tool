# VTS Report Tool Mobile App (Ready-to-run)

This mobile app supports full VTS features and is packaged to be easy to run for non-technical users.

Key features
- User authentication (JWT or device token)
- Select patrol vehicle currently tracking (KP1/KP2 mapping supported)
- Background GPS tracking that:
  - Activates only after user logs in and explicitly starts a patrol
  - Runs continually in background until user stops tracking
  - Uses foreground and platform background services (Android/iOS) with persistent notification on Android
  - Sends periodic location updates (configurable interval/distance)
- Offline queueing: events (check-ins, patrol start/stop, incidents) are stored locally and synced when online
- Direct S3 presigned PUT uploads for images (client uploads binary directly to S3; backend stores key)
- WhatsApp import helpers (Streamlit) integrated with incident ingestion

Ready-to-run (no configuration) quickstart
1. Clone the repo and open the /mobile_app folder.
2. Ensure Flutter is installed (or use the included prebuilt APK if available).
3. Run one of the scripts in `d:\gps-report-tool\scripts`:
   - On macOS/Linux: scripts/prepare_release.sh
   - On Windows: scripts/prepare_release.bat
   These scripts will:
   - Copy `mobile_app/config.sample.json` → `mobile_app/config.json` (runtime config)
   - Optionally set API_BASE_URL from environment
   - Run `flutter build apk --release` to generate an installable APK
4. Provide the generated APK to users; they can install and run without editing config files.

Configuration (optional)
- `mobile_app/config.json` (generated from config.sample) contains:
  - apiBaseUrl: backend URL (default `http://localhost:8000`)
  - deviceToken: demo token (replace for production)
  - enableBackgroundLocationByDefault, backgroundLocationIntervalSeconds, locationDistanceMeters
- If you want to pre-configure for production, edit config.sample.json or set API_BASE_URL env var before running scripts.

Background GPS behavior (important)
- GPS tracking module will only activate when:
  1) A user is authenticated (login required), and
  2) The user selects and starts tracking a patrol vehicle in the UI.
- Stopping the patrol explicitly (Stop Patrol) disables background location.
- Implementation notes:
  - Android: uses foreground service / persistent notification and `flutter_background_geolocation` or `workmanager` depending on implementation.
  - iOS: uses location background modes and requires permissions and justification text in Info.plist.
  - Interval and distance are configurable from config.json.

Offline queueing
- Events are enqueued locally (AsyncStorage / SharedPreferences) when offline.
- Images are uploaded using presigned PUT URLs returned from backend `/api/presign`.
- When connectivity returns, the app:
  1) Uploads images (PUT to presigned URL)
  2) Posts events in a single batch to `/api/events/batch`
- Use `mobile_app/services/offlineQueue.js` (React Native example) as a reference implementation.

Patrol vehicle mapping for WizPro
- The app maps vehicle tags to patrol cars:
  - KP1 → KDK 825Y
  - KP2 → KDS 374F
  - KP3 → KDG 320Z
- If OCR/chat text contains KP1/KP2/KP3, the app will preselect the mapped patrol car.

Distribution suggestions
- Build and distribute via:
  - Android APK (sideload)
  - Google Play internal test track
  - iOS TestFlight (requires Apple account)
- For one-click distribution to non-technical users, produce and host the APK and provide a short install guide.

Security and production notes
- Replace demo device tokens with secure auth (JWT).
- Use HTTPS for backend and presigned URL exchanges.
- Limit S3 presigned URL duration and use bucket policies for security.

If you want I can:
- Add Flutter code snippets (Platform-specific) for background tracking + notification,
- Provide a complete Expo/React-Native example instead of Flutter,
- Create CI workflow to produce release artifacts automatically (GitHub Actions).