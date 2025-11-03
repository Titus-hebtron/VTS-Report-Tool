import 'dart:async';
import 'dart:convert';
import 'package:geolocator/geolocator.dart';
import 'package:background_location/background_location.dart';
import 'package:http/http.dart' as http;
import '../config.dart';

class GpsService {
  static const double IDLE_SPEED_THRESHOLD = 2.0; // km/h
  static const Duration IDLE_CHECK_INTERVAL = Duration(seconds: 30);
  static const Duration LOCATION_UPDATE_INTERVAL = Duration(seconds: 10);

  bool _isTracking = false;
  bool _isIdle = false;
  DateTime? _idleStartTime;
  Position? _lastPosition;
  Timer? _idleCheckTimer;
  StreamSubscription<Position>? _positionStream;
  String? _authToken;
  int? _vehicleId;
  String? _contractorId;

  bool get isTracking => _isTracking;
  bool get isIdle => _isIdle;

  Future<bool> requestPermissions() async {
    LocationPermission permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied) {
        return false;
      }
    }

    if (permission == LocationPermission.deniedForever) {
      return false;
    }

    return true;
  }

  Future<void> startTracking(String token, int vehicleId, String contractorId) async {
    if (_isTracking) return;

    _authToken = token;
    _vehicleId = vehicleId;
    // Convert contractor name to ID - for now using a simple mapping
    _contractorId = _getContractorIdFromName(contractorId);

    // Request permissions
    if (!await requestPermissions()) {
      throw Exception('Location permissions not granted');
    }

    // Start background location tracking
    await BackgroundLocation.setAndroidNotification(
      title: 'Patrol GPS Tracking Active',
      message: 'Recording speed, location, time, and idle data for patrol logs',
      icon: '@mipmap/ic_launcher',
    );

    BackgroundLocation.startLocationService(distanceFilter: 10); // Update every 10 meters

    BackgroundLocation.getLocationUpdates((location) {
      _handleLocationUpdate(location);
    });

    _isTracking = true;

    // Start idle detection
    _startIdleDetection();
  }

  Future<void> stopTracking() async {
    if (!_isTracking) return;

    BackgroundLocation.stopLocationService();
    _positionStream?.cancel();
    _idleCheckTimer?.cancel();

    _isTracking = false;
    _isIdle = false;
    _idleStartTime = null;
    _lastPosition = null;
  }

  void _handleLocationUpdate(BackgroundLocation location) async {
    final position = Position(
      latitude: location.latitude!,
      longitude: location.longitude!,
      timestamp: DateTime.now(),
      accuracy: location.accuracy!,
      altitude: location.altitude!,
      heading: location.bearing!,
      speed: location.speed!,
      speedAccuracy: 0.0,
    );

    await _sendLocationToServer(position);

    // Check for idle status
    _checkIdleStatus(position);
  }

  Future<void> _sendLocationToServer(Position position) async {
    if (_authToken == null || _vehicleId == null) return;

    try {
      final response = await http.post(
        Uri.parse('$apiBaseUrl/patrol_logs'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $_authToken',
        },
        body: json.encode({
          'vehicle_id': _vehicleId,
          'latitude': position.latitude,
          'longitude': position.longitude,
          'timestamp': position.timestamp.toIso8601String(),
          'activity': _isIdle ? 'idle' : 'moving',
          'speed': position.speed * 3.6, // Convert m/s to km/h
          'status': 'online', // Indicate active GPS tracking
        }),
      );

      if (response.statusCode != 201) {
        print('Failed to send location: ${response.statusCode}');
      }
    } catch (e) {
      print('Error sending location: $e');
    }
  }

  void _checkIdleStatus(Position currentPosition) {
    if (_lastPosition == null) {
      _lastPosition = currentPosition;
      return;
    }

    // Calculate speed (simple distance/time approximation)
    final distance = Geolocator.distanceBetween(
      _lastPosition!.latitude,
      _lastPosition!.longitude,
      currentPosition.latitude,
      currentPosition.longitude,
    );

    final timeDiff = currentPosition.timestamp.difference(_lastPosition!.timestamp);
    final speedKmh = (distance / 1000) / (timeDiff.inSeconds / 3600);

    _lastPosition = currentPosition;

    if (speedKmh < IDLE_SPEED_THRESHOLD) {
      if (!_isIdle) {
        _isIdle = true;
        _idleStartTime = currentPosition.timestamp;
        _recordIdleStart();
      }
    } else {
      if (_isIdle) {
        _recordIdleEnd();
        _isIdle = false;
        _idleStartTime = null;
      }
    }
  }

  void _startIdleDetection() {
    _idleCheckTimer = Timer.periodic(IDLE_CHECK_INTERVAL, (timer) async {
      if (_isIdle && _idleStartTime != null) {
        final idleDuration = DateTime.now().difference(_idleStartTime!);
        if (idleDuration.inMinutes >= 1) { // Record idle every minute
          await _sendIdleReport(idleDuration);
        }
      }
    });
  }

  Future<void> _recordIdleStart() async {
    if (_authToken == null || _vehicleId == null || _lastPosition == null) return;

    try {
      final response = await http.post(
        Uri.parse('$apiBaseUrl/idle_reports'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $_authToken',
        },
        body: json.encode({
          'vehicle': 'Vehicle $_vehicleId', // Should get actual plate number
          'idle_start': _idleStartTime!.toIso8601String(),
          'location_address': 'Lat: ${_lastPosition!.latitude}, Lng: ${_lastPosition!.longitude}',
          'latitude': _lastPosition!.latitude,
          'longitude': _lastPosition!.longitude,
          'description': 'Vehicle idle detected',
          'contractor_id': _contractorId,
        }),
      );

      print('Idle start recorded: ${response.statusCode}');
    } catch (e) {
      print('Error recording idle start: $e');
    }
  }

  Future<void> _recordIdleEnd() async {
    if (_authToken == null || _vehicleId == null || _idleStartTime == null) return;

    try {
      final idleDuration = DateTime.now().difference(_idleStartTime!);
      final response = await http.put(
        Uri.parse('$apiBaseUrl/idle_reports/end'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $_authToken',
        },
        body: json.encode({
          'vehicle': 'Vehicle $_vehicleId',
          'idle_end': DateTime.now().toIso8601String(),
          'idle_duration_min': idleDuration.inMinutes.toDouble(),
        }),
      );

      print('Idle end recorded: ${response.statusCode}');
    } catch (e) {
      print('Error recording idle end: $e');
    }
  }

  Future<void> _sendIdleReport(Duration idleDuration) async {
    // Send periodic idle updates
    if (_authToken == null || _vehicleId == null || _lastPosition == null) return;

    try {
      await http.post(
        Uri.parse('$apiBaseUrl/patrol_logs'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $_authToken',
        },
        body: json.encode({
          'vehicle_id': _vehicleId,
          'latitude': _lastPosition!.latitude,
          'longitude': _lastPosition!.longitude,
          'timestamp': DateTime.now().toIso8601String(),
          'activity': 'idle_continued',
          'speed': 0.0,
        }),
      );
    } catch (e) {
      print('Error sending idle report: $e');
    }
  }

  String _getContractorIdFromName(String contractorName) {
    // Simple mapping for contractor names to IDs
    switch (contractorName.toLowerCase()) {
      case 'wizpro':
        return '1';
      case 'paschal':
        return '2';
      case 're office':
        return '3';
      case 'avators':
        return '4';
      default:
        return '1'; // Default to Wizpro
    }
  }
}