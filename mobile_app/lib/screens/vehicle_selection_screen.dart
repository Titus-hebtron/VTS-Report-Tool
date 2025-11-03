import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../config.dart';
import 'patrol_logs_screen.dart';

class VehicleSelectionScreen extends StatefulWidget {
  const VehicleSelectionScreen({super.key});

  @override
  _VehicleSelectionScreenState createState() => _VehicleSelectionScreenState();
}

class _VehicleSelectionScreenState extends State<VehicleSelectionScreen> {
  List<dynamic> _vehicles = [];
  bool _isLoading = true;
  String? _userRole;

  @override
  void initState() {
    super.initState();
    _userRole = Provider.of<AuthProvider>(context, listen: false).role;
    _fetchVehicles();
  }

  Future<void> _fetchVehicles() async {
    final auth = Provider.of<AuthProvider>(context, listen: false);
    final response = await http.get(
      Uri.parse('$apiBaseUrl/vehicles'),
      headers: {'Authorization': 'Bearer ${auth.token}'},
    );

    if (response.statusCode == 200) {
      setState(() {
        _vehicles = json.decode(response.body);
        // Filter vehicles based on role - patrol officers only see patrol vehicles
        if (_userRole == 'patrol') {
          _vehicles = _vehicles.where((vehicle) =>
            vehicle['plate_number'].toString().startsWith('Patrol_')).toList();
        }
        _isLoading = false;
      });
    } else {
      // Handle error
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Select Patrol Vehicle')),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _vehicles.isEmpty
              ? const Center(child: Text('No patrol vehicles available'))
              : ListView.builder(
                  itemCount: _vehicles.length,
                  itemBuilder: (context, index) {
                    final vehicle = _vehicles[index];
                    return ListTile(
                      title: Text(vehicle['plate_number']),
                      subtitle: Text('Tap to activate GPS tracking'),
                      leading: const Icon(Icons.directions_car, color: Colors.blue),
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => PatrolLogsScreen(vehicle: vehicle),
                          ),
                        );
                      },
                    );
                  },
                ),
    );
  }
}