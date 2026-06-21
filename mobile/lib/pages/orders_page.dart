import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../services/api_service.dart';

class Order {
  final String id;
  final String symbol;
  final String side;
  final double price;
  final int quantity;
  final String status;

  Order({
    required this.id,
    required this.symbol,
    required this.side,
    required this.price,
    required this.quantity,
    required this.status,
  });

  factory Order.fromJson(Map<String, dynamic> json) {
    return Order(
      id: json['order_id'] ?? json['id'] ?? '',
      symbol: json['symbol'] ?? '',
      side: json['side'] ?? json['direction'] ?? '',
      price: (json['price'] ?? 0).toDouble(),
      quantity: (json['quantity'] ?? 0).toInt(),
      status: json['status'] ?? 'unknown',
    );
  }
}

class OrdersPage extends StatefulWidget {
  const OrdersPage({super.key});

  @override
  State<OrdersPage> createState() => _OrdersPageState();
}

class _OrdersPageState extends State<OrdersPage> {
  final ApiService _api = ApiService();
  List<Order> _orders = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final userId = context.read<AuthProvider>().userId;
    try {
      final data = await _api.getOrders(userId);
      setState(() {
        _orders = data.map((e) => Order.fromJson(e as Map<String, dynamic>)).toList();
        _loading = false;
      });
    } catch (e) {
      setState(() => _loading = false);
    }
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'filled':
        return Colors.green;
      case 'pending':
        return Colors.orange;
      case 'cancelled':
        return Colors.grey;
      case 'rejected':
        return Colors.red;
      default:
        return Colors.white;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Orders')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: _orders.isEmpty
                  ? const Center(child: Text('No orders'))
                  : ListView.builder(
                      itemCount: _orders.length,
                      itemBuilder: (_, i) {
                        final o = _orders[i];
                        return ListTile(
                          leading: Icon(
                            o.side == 'BUY' ? Icons.shopping_cart : Icons.sell,
                            color: o.side == 'BUY' ? Colors.green : Colors.red,
                          ),
                          title: Text('${o.symbol}  ${o.side}'),
                          subtitle: Text('${o.quantity} @ \$${o.price.toStringAsFixed(2)}'),
                          trailing: Chip(
                            label: Text(o.status.toUpperCase(), style: const TextStyle(fontSize: 11)),
                            backgroundColor: _statusColor(o.status).withOpacity(0.2),
                          ),
                        );
                      },
                    ),
            ),
    );
  }
}