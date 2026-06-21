import 'package:flutter/material.dart';
import '../services/api_service.dart';

class AuthProvider extends ChangeNotifier {
  final ApiService _api = ApiService();
  bool _authenticated = false;
  String _username = '';
  int _userId = 0;

  bool get isAuthenticated => _authenticated;
  String get username => _username;
  int get userId => _userId;

  Future<String?> login(String username, String password) async {
    try {
      final resp = await _api.login(username, password);
      if (resp['ok'] == true) {
        _authenticated = true;
        _username = username;
        _userId = resp['data']?['user_id'] ?? 0;
        notifyListeners();
        return null;
      }
      return resp['error'] ?? 'Login failed';
    } catch (e) {
      return 'Network error: $e';
    }
  }

  void logout() {
    _authenticated = false;
    _username = '';
    _userId = 0;
    notifyListeners();
  }
}