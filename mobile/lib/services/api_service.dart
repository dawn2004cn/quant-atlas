class ApiConfig {
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:5000',
  );
  static const String wsUrl = String.fromEnvironment(
    'WS_URL',
    defaultValue: 'http://10.0.2.2:5001',
  );
}

class ApiService {
  final String baseUrl;

  ApiService({this.baseUrl = ApiConfig.baseUrl});

  String get _api => '$baseUrl/api/v1';

  Future<Map<String, dynamic>> login(String username, String password) async {
    final uri = Uri.parse('$_api/auth/login');
    final response = await _post(uri, {
      'username': username,
      'password': password,
    });
    return response;
  }

  Future<List<dynamic>> getMarketQuotes() async {
    final uri = Uri.parse('$_api/market/quotes');
    return _getList(uri);
  }

  Future<Map<String, dynamic>> getStockDetail(String symbol) async {
    final uri = Uri.parse('$_api/market/stock/$symbol');
    return _getJson(uri);
  }

  Future<Map<String, dynamic>> getTradePlan(String symbol) async {
    final uri = Uri.parse('$_api/trade-plan/$symbol');
    return _getJson(uri);
  }

  Future<List<dynamic>> getPortfolio(int userId) async {
    final uri = Uri.parse('$_api/portfolio/$userId');
    return _getList(uri);
  }

  Future<List<dynamic>> getOrders(int userId) async {
    final uri = Uri.parse('$_api/orders/$userId');
    return _getList(uri);
  }

  Future<Map<String, dynamic>> submitOrder(
    String symbol,
    String side,
    double price,
    int quantity,
  ) async {
    final uri = Uri.parse('$_api/orders');
    return _post(uri, {
      'symbol': symbol,
      'side': side,
      'price': price,
      'quantity': quantity,
    });
  }

  Future<Map<String, dynamic>> getAiAnalysis(String symbol) async {
    final uri = Uri.parse('$_api/ai/analysis/$symbol');
    return _getJson(uri);
  }

  // ── HTTP helpers ──

  Future<Map<String, dynamic>> _getJson(Uri uri) async {
    final http = _createClient();
    final resp = await http.get(uri, headers: _headers);
    return _decode(resp.body);
  }

  Future<List<dynamic>> _getList(Uri uri) async {
    final http = _createClient();
    final resp = await http.get(uri, headers: _headers);
    final json = _decode(resp.body);
    return json['data'] as List<dynamic>? ?? [];
  }

  Future<Map<String, dynamic>> _post(Uri uri, Map<String, dynamic> body) async {
    final http = _createClient();
    final resp = await http.post(uri, headers: _headers, body: _encode(body));
    return _decode(resp.body);
  }

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      };

  dynamic _createClient() {
    // In production: add auth token interceptor
    return _HttpClient();
  }

  Map<String, dynamic> _decode(String body) {
    // Very simple JSON decode — use dart:convert
    import 'dart:convert';
    return jsonDecode(body) as Map<String, dynamic>;
  }

  String _encode(Map<String, dynamic> body) {
    import 'dart:convert';
    return jsonEncode(body);
  }
}

// Minimal HTTP client wrapper
class _HttpClient {
  Future<http.Response> get(Uri uri, {Map<String, String>? headers}) =>
      http.get(uri, headers: headers);

  Future<http.Response> post(Uri uri,
      {Map<String, String>? headers, String? body}) =>
      http.post(uri, headers: headers, body: body);
}

import 'dart:convert';
import 'package:http/http.dart' as http;