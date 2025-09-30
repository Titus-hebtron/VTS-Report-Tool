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

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: Text('Patrol Logs - ${widget.vehicle['plate_number']}'),
          bottom: const TabBar(
            tabs: [
              Tab(text: 'Logs'),
              Tab(text: 'Map'),
            ],
          ),
        ),
        body: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : TabBarView(
                children: [
                  // Logs Tab
                  ListView.builder(
                    itemCount: _logs.length,
                    itemBuilder: (context, index) {
                      final log = _logs[index];
                      return ListTile(
                        title: Text(log['activity'] ?? 'No activity'),
                        subtitle: Text(log['timestamp']),
                      );
                    },
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