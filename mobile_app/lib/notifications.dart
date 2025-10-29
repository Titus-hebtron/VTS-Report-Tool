import 'package:firebase_messaging/firebase_messaging.dart';

class Notifications {
  final FirebaseMessaging _fm = FirebaseMessaging.instance;

  Future<void> init() async {
    // request permissions
    NotificationSettings settings = await _fm.requestPermission();
    // get token to register with backend
    String? token = await _fm.getToken();
    // send token to backend for push targeting
    // POST /devices/register { token, device_info }
  }

  /// foreground message handler registration
  void onMessage(void Function(RemoteMessage) handler) {
    FirebaseMessaging.onMessage.listen(handler);
  }
}
