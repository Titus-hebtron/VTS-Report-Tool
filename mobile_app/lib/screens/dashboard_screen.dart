import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../providers/gps_provider.dart';
import 'vehicle_selection_screen.dart';
import 'reports_screen.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = Provider.of<AuthProvider>(context);
    final gps = Provider.of<GpsProvider>(context);
    final isPatrol = auth.user?['role'] == 'patrol';

    return Scaffold(
      appBar: AppBar(
        title: const Text('Dashboard'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () => auth.logout(),
          ),
        ],
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text('Welcome, ${auth.user?['username']}'),
            Text('Contractor: ${auth.user?['contractor']}'),
            Text('Role: ${auth.user?['role']}'),
            const SizedBox(height: 20),

            // GPS Status for patrol users
            if (isPatrol) ...[
              Container(
                padding: const EdgeInsets.all(16),
                margin: const EdgeInsets.symmetric(horizontal: 20),
                decoration: BoxDecoration(
                  color: gps.isTracking ? Colors.green.shade100 : Colors.grey.shade100,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: gps.isTracking ? Colors.green : Colors.grey,
                  ),
                ),
                child: Column(
                  children: [
                    Icon(
                      gps.isTracking ? Icons.gps_fixed : Icons.gps_off,
                      size: 48,
                      color: gps.isTracking ? Colors.green : Colors.grey,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      gps.isTracking
                          ? (gps.isIdle ? 'GPS Active - Vehicle Idle' : 'GPS Active - Vehicle Moving')
                          : 'GPS Inactive',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: gps.isTracking ? Colors.green : Colors.grey,
                      ),
                    ),
                    const SizedBox(height: 8),
                    ElevatedButton(
                      onPressed: () async {
                        if (gps.isTracking) {
                          await gps.stopTracking();
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('GPS tracking stopped')),
                          );
                        } else {
                          // Request permissions and start tracking
                          final hasPermission = await gps.requestPermissions();
                          if (hasPermission) {
                            // Note: Vehicle selection would be needed here
                            // For now, using placeholder values
                            try {
                              await gps.startTracking(
                                auth.token!,
                                1, // placeholder vehicle ID
                                auth.user?['contractor'] ?? '',
                              );
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(content: Text('GPS tracking started')),
                              );
                            } catch (e) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(content: Text('Failed to start GPS: $e')),
                              );
                            }
                          } else {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(content: Text('Location permissions required')),
                            );
                          }
                        }
                      },
                      child: Text(gps.isTracking ? 'Stop GPS Tracking' : 'Start GPS Tracking'),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
            ],

            ElevatedButton(
              onPressed: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => const VehicleSelectionScreen()),
                );
              },
              child: const Text('Select Vehicle'),
            ),
            const SizedBox(height: 10),
            ElevatedButton(
              onPressed: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => const ReportsScreen()),
                );
              },
              child: const Text('View Reports'),
            ),
          ],
        ),
      ),
    );
  }
}