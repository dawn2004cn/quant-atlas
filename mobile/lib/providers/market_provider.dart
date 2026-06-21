import 'dart:async';
import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../services/websocket_service.dart';

class Quote {
  final String symbol;
  final double price;
  final double change;
  final double changePct;

  Quote({
    required this.symbol,
    required this.price,
    required this.change,
    required this.changePct,
  });

  factory Quote.fromJson(Map<String, dynamic> json) {
    return Quote(
      symbol: json['symbol'] ?? '',
      price: (json['price'] ?? 0).toDouble(),
      change: (json['change'] ?? 0).toDouble(),
      changePct: (json['change_pct'] ?? 0).toDouble(),
    );
  }
}

class MarketProvider extends ChangeNotifier {
  final ApiService _api = ApiService();
  final WebSocketService _ws = WebSocketService();
  List<Quote> _quotes = [];
  bool _loading = false;

  List<Quote> get quotes => _quotes;
  bool get loading => _loading;

  MarketProvider() {
    _ws.onQuote(_handleQuote);
    _ws.connect();
  }

  void _handleQuote(Map<String, dynamic> data) {
    final quote = Quote.fromJson(data);
    final idx = _quotes.indexWhere((q) => q.symbol == quote.symbol);
    if (idx >= 0) {
      _quotes[idx] = quote;
    } else {
      _quotes.add(quote);
    }
    notifyListeners();
  }

  Future<void> fetchQuotes() async {
    _loading = true;
    notifyListeners();
    try {
      final data = await _api.getMarketQuotes();
      _quotes = data.map((e) => Quote.fromJson(e as Map<String, dynamic>)).toList();
    } catch (e) {
      print('fetchQuotes error: $e');
    }
    _loading = false;
    notifyListeners();
  }

  Quote? bySymbol(String symbol) {
    try {
      return _quotes.firstWhere((q) => q.symbol == symbol);
    } catch (_) {
      return null;
    }
  }

  @override
  void dispose() {
    _ws.disconnect();
    super.dispose();
  }
}