import 'package:flutter/material.dart';
import '../services/gps_service.dart';

class GpsProvider with ChangeNotifier {
  final GpsService _gpsService = GpsService();

  bool get isTracking => _gpsService.isTracking;
  bool get isIdle => _gpsService.isIdle;

  Future<void> startTracking(String token, int vehicleId, String contractorId) async {
    try {
      await _gpsService.startTracking(token, vehicleId, contractorId);
      notifyListeners();
    } catch (e) {
      rethrow;
    }
  }

  Future<void> stopTracking() async {
    await _gpsService.stopTracking();
    notifyListeners();
  }

  Future<bool> requestPermissions() async {
    return await _gpsService.requestPermissions();
  }
}