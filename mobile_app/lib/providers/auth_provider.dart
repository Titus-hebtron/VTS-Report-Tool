import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../config.dart';

class AuthProvider with ChangeNotifier {
  String? _token;
  Map<String, dynamic>? _user;

  bool get isAuthenticated => _token != null;

  String? get token => _token;
  Map<String, dynamic>? get user => _user;

  Future<void> login(String contractor, String username, String password) async {
    final response = await http.post(
      Uri.parse('$apiBaseUrl/login'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({
        'contractor': contractor,
        'username': username,
        'password': password,
      }),
    );

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      _token = data['access_token'];
      // Decode token to get user info (simplified)
      final payload = json.decode(utf8.decode(base64.decode(base64.normalize(_token!.split('.')[1]))));
      _user = {
        'username': payload['sub'],
        'contractor': payload['contractor'],
        'role': payload['role'],
      };
      await _saveToken();
      notifyListeners();
    } else {
      throw Exception('Login failed');
    }
  }

  Future<void> logout() async {
    _token = null;
    _user = null;
    await _clearToken();
    notifyListeners();
  }

  Future<void> _saveToken() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('token', _token!);
  }

  Future<void> _clearToken() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('token');
  }

  Future<void> tryAutoLogin() async {
    final prefs = await SharedPreferences.getInstance();
    final savedToken = prefs.getString('token');
    if (savedToken != null) {
      _token = savedToken;
      // Decode token
      try {
        final payload = json.decode(utf8.decode(base64.decode(base64.normalize(_token!.split('.')[1]))));
        _user = {
          'username': payload['sub'],
          'contractor': payload['contractor'],
          'role': payload['role'],
        };
        notifyListeners();
      } catch (e) {
        await _clearToken();
      }
    }
  }
}