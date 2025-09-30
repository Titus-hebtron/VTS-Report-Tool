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

  @override
  void initState() {
    super.initState();
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
      appBar: AppBar(title: const Text('Select Vehicle')),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : ListView.builder(
              itemCount: _vehicles.length,
              itemBuilder: (context, index) {
                final vehicle = _vehicles[index];
                return ListTile(
                  title: Text(vehicle['plate_number']),
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