import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:http/http.dart' as http;

// Minimal offline queue: stores JSON events in SharedPreferences under 'vts_queue'
class OfflineQueue {
  final String apiBase;
  final String queueKey = 'vts_queue';

  OfflineQueue(this.apiBase);

  Future<void> enqueueEvent(Map<String, dynamic> event) async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(queueKey);
    List<dynamic> items = raw != null ? jsonDecode(raw) : [];
    items.add(event);
    await prefs.setString(queueKey, jsonEncode(items));
  }

  Future<List<dynamic>> _getQueue() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(queueKey);
    return raw != null ? jsonDecode(raw) : [];
  }

  Future<void> _setQueue(List<dynamic> items) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(queueKey, jsonEncode(items));
  }

  Future<void> flushQueue() async {
    final items = await _getQueue();
    if (items.isEmpty) return;
    final remaining = <dynamic>[];
    for (final it in items) {
      try {
        final resp = await http.post(
          Uri.parse('$apiBase/api/events'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode(it),
        );
        if (resp.statusCode != 200 && resp.statusCode != 201) {
          // keep item for retry
          remaining.add(it);
        }
      } catch (e) {
        // network error -> keep item
        remaining.add(it);
      }
    }
    await _setQueue(remaining);
  }
}
