import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:provider/provider.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../providers/auth_provider.dart';
import '../config.dart';

class PatrolLogsScreen extends StatefulWidget {
  final Map<String, dynamic> vehicle;

  const PatrolLogsScreen({super.key, required this.vehicle});

  @override
  _PatrolLogsScreenState createState() => _PatrolLogsScreenState();
}

class _PatrolLogsScreenState extends State<PatrolLogsScreen> {
  List<dynamic> _logs = [];
  bool _isLoading = true;
  bool _isTracking = false;

  @override
  void initState() {
    super.initState();
    _fetchPatrolLogs();
  }

  Future<void> _fetchPatrolLogs() async {
    final auth = Provider.of<AuthProvider>(context, listen: false);
    final response = await http.get(
      Uri.parse('$apiBaseUrl/patrol_logs/${widget.vehicle['id']}'),
      headers: {'Authorization': 'Bearer ${auth.token}'},
    );

    if (response.statusCode == 200) {
      setState(() {
        _logs = json.decode(response.body);
        _isLoading = false;
      });
    } else {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _toggleTracking() async {
    final auth = Provider.of<AuthProvider>(context, listen: false);
    final gpsService = GpsService();

    if (_isTracking) {
      // Stop tracking
      await gpsService.stopTracking();
      setState(() => _isTracking = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('GPS tracking stopped')),
      );
    } else {
      // Start tracking
      try {
        await gpsService.startTracking(
          auth.token!,
          widget.vehicle['id'],
          auth.contractor,
        );
        setState(() => _isTracking = true);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('GPS tracking started - monitoring location, speed, and idle time')),
        );
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to start tracking: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: Text('Patrol Vehicle - ${widget.vehicle['plate_number']}'),
          bottom: const TabBar(
            tabs: [
              Tab(text: 'Logs'),
              Tab(text: 'Map'),
            ],
          ),
        ),
        floatingActionButton: FloatingActionButton.extended(
          onPressed: _toggleTracking,
          icon: Icon(_isTracking ? Icons.stop : Icons.play_arrow),
          label: Text(_isTracking ? 'Stop Tracking' : 'Start Tracking'),
          backgroundColor: _isTracking ? Colors.red : Colors.green,
        ),
        body: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : TabBarView(
                children: [
                  // Logs Tab
                  Column(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(16),
                        color: _isTracking ? Colors.green.shade50 : Colors.grey.shade50,
                        child: Row(
                          children: [
                            Icon(
                              _isTracking ? Icons.gps_fixed : Icons.gps_off,
                              color: _isTracking ? Colors.green : Colors.grey,
                            ),
                            const SizedBox(width: 8),
                            Text(
                              _isTracking
                                  ? 'GPS Tracking Active - Recording location, speed, and idle time'
                                  : 'GPS Tracking Inactive',
                              style: TextStyle(
                                color: _isTracking ? Colors.green.shade800 : Colors.grey.shade800,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                      ),
                      Expanded(
                        child: _logs.isEmpty
                            ? const Center(child: Text('No patrol logs yet. Start tracking to see data.'))
                            : ListView.builder(
                                itemCount: _logs.length,
                                itemBuilder: (context, index) {
                                  final log = _logs[index];
                                  return ListTile(
                                    title: Text(log['activity'] ?? 'No activity'),
                                    subtitle: Text(log['timestamp'] ?? ''),
                                    trailing: log['speed'] != null
                                        ? Text('${log['speed']} km/h')
                                        : null,
                                  );
                                },
                              ),
                      ),
                    ],
                  ),
                  // Map Tab
                  FlutterMap(
                    options: MapOptions(
                      center: _logs.isNotEmpty && _logs[0]['latitude'] != null
                          ? LatLng(_logs[0]['latitude'], _logs[0]['longitude'])
                          : LatLng(-1.2921, 36.8219), // Nairobi
                      zoom: 12.0,
                    ),
                    children: [
                      TileLayer(
                        urlTemplate: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
                        subdomains: ['a', 'b', 'c'],
                      ),
                      MarkerLayer(
                        markers: _logs
                            .where((log) => log['latitude'] != null && log['longitude'] != null)
                            .map((log) => Marker(
                                  point: LatLng(log['latitude'], log['longitude']),
                                  builder: (ctx) => const Icon(
                                    Icons.location_on,
                                    color: Colors.red,
                                    size: 30,
                                  ),
                                ))
                            .toList(),
                      ),
                    ],
                  ),
                ],
              ),
      ),
    );
  }
}