# VTS Report Tool Mobile App

A cross-platform mobile application for the VTS Report Tool, built with Flutter.

## Features

- User authentication with JWT
- Vehicle selection
- Patrol logs viewing
- Interactive map with patrol locations
- Incident reports viewing

## Setup

1. Ensure Flutter is installed: https://flutter.dev/docs/get-started/install
2. Install dependencies: `flutter pub get`
3. **Configure API URL**: Edit `lib/config.dart` and set your server URL
4. Run the app: `flutter run`

## 🔗 Server Connection Procedure

### 1. Deploy API Server
```bash
# On your server (replace with your actual server details)
python api.py
# Or for production deployment:
uvicorn api:app --host 0.0.0.0 --port 8000
```

### 2. Configure Mobile App
Edit `lib/config.dart`:
```dart
// For local development:
const String apiBaseUrl = 'http://10.0.2.2:8000'; // Android emulator
const String apiBaseUrl = 'http://localhost:8000'; // iOS simulator

// For production server:
const String apiBaseUrl = 'http://your-server-ip:8000';
const String apiBaseUrl = 'https://your-domain.com/api';
```

### 3. Build and Install
```bash
flutter build apk --release  # Android
flutter build ios --release  # iOS
```

## Cross-Platform

This app is built with Flutter and can run on Android and iOS, connecting directly to your FastAPI server.

## Dependencies

- http: For API calls
- provider: State management
- shared_preferences: Local storage
- flutter_map: Map widget
- latlong2: Coordinates