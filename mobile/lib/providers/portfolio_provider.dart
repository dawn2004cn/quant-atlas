import 'package:flutter/material.dart';
import '../services/api_service.dart';

class Position {
  final String symbol;
  final double quantity;
  final double avgPrice;
  final double marketValue;
  final double pnl;

  Position({
    required this.symbol,
    required this.quantity,
    required this.avgPrice,
    required this.marketValue,
    required this.pnl,
  });

  factory Position.fromJson(Map<String, dynamic> json) {
    return Position(
      symbol: json['symbol'] ?? '',
      quantity: (json['quantity'] ?? 0).toDouble(),
      avgPrice: (json['avg_price'] ?? 0).toDouble(),
      marketValue: (json['market_value'] ?? 0).toDouble(),
      pnl: (json['pnl'] ?? 0).toDouble(),
    );
  }
}

class PortfolioProvider extends ChangeNotifier {
  final ApiService _api = ApiService();
  List<Position> _positions = [];
  double _totalValue = 0;
  bool _loading = false;

  List<Position> get positions => _positions;
  double get totalValue => _totalValue;
  bool get loading => _loading;

  Future<void> fetchPortfolio(int userId) async {
    _loading = true;
    notifyListeners();
    try {
      final data = await _api.getPortfolio(userId);
      _positions = data
          .map((e) => Position.fromJson(e as Map<String, dynamic>))
          .toList();
      _totalValue =
          _positions.fold(0.0, (sum, p) => sum + p.marketValue);
    } catch (e) {
      print('fetchPortfolio error: $e');
    }
    _loading = false;
    notifyListeners();
  }
}