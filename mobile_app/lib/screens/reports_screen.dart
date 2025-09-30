import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../config.dart';

class ReportsScreen extends StatefulWidget {
  const ReportsScreen({super.key});

  @override
  _ReportsScreenState createState() => _ReportsScreenState();
}

class _ReportsScreenState extends State<ReportsScreen> {
  List<dynamic> _incidents = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _fetchIncidents();
  }

  Future<void> _fetchIncidents() async {
    final auth = Provider.of<AuthProvider>(context, listen: false);
    final response = await http.get(
      Uri.parse('$apiBaseUrl/incidents'),
      headers: {'Authorization': 'Bearer ${auth.token}'},
    );

    if (response.statusCode == 200) {
      setState(() {
        _incidents = json.decode(response.body);
        _isLoading = false;
      });
    } else {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Incident Reports')),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : ListView.builder(
              itemCount: _incidents.length,
              itemBuilder: (context, index) {
                final incident = _incidents[index];
                return ListTile(
                  title: Text(incident['description'] ?? 'No description'),
                  subtitle: Text('${incident['patrol_car']} - ${incident['incident_date']}'),
                );
              },
            ),
    );
  }
}