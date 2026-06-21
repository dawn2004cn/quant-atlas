import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../services/websocket_service.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../providers/portfolio_provider.dart';

class StockDetailPage extends StatefulWidget {
  final String symbol;
  const StockDetailPage({super.key, required this.symbol});

  @override
  State<StockDetailPage> createState() => _StockDetailPageState();
}

class _StockDetailPageState extends State<StockDetailPage> {
  final ApiService _api = ApiService();
  Map<String, dynamic>? _detail;
  Map<String, dynamic>? _tradePlan;
  Map<String, dynamic>? _aiAnalysis;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final results = await Future.wait([
        _api.getStockDetail(widget.symbol),
        _api.getTradePlan(widget.symbol),
        _api.getAiAnalysis(widget.symbol),
      ]);
      setState(() {
        _detail = results[0];
        _tradePlan = results[1];
        _aiAnalysis = results[2];
        _loading = false;
      });
    } catch (e) {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.symbol)),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  _PriceCard(detail: _detail),
                  const SizedBox(height: 16),
                  if (_tradePlan != null) _TradePlanCard(plan: _tradePlan!),
                  const SizedBox(height: 16),
                  if (_aiAnalysis != null) _AiAnalysisCard(analysis: _aiAnalysis!),
                ],
              ),
            ),
    );
  }
}

class _PriceCard extends StatelessWidget {
  final Map<String, dynamic>? detail;
  const _PriceCard({this.detail});

  @override
  Widget build(BuildContext context) {
    final price = (detail?['price'] ?? 0).toDouble();
    final change = (detail?['change'] ?? 0).toDouble();
    final isUp = change >= 0;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            Text(
              price.toStringAsFixed(2),
              style: Theme.of(context).textTheme.headlineLarge?.copyWith(
                    color: isUp ? Colors.green : Colors.red,
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 4),
            Text(
              '${isUp ? '+' : ''}${change.toStringAsFixed(2)} (${isUp ? '+' : ''}${(detail?['change_pct'] ?? 0).toStringAsFixed(2)}%)',
              style: TextStyle(color: isUp ? Colors.green : Colors.red, fontSize: 16),
            ),
          ],
        ),
      ),
    );
  }
}

class _TradePlanCard extends StatelessWidget {
  final Map<String, dynamic> plan;
  const _TradePlanCard({required this.plan});

  @override
  Widget build(BuildContext context) {
    final direction = (plan['direction'] ?? 'HOLD') as String;
    final isBuy = direction == 'BUY';
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(isBuy ? Icons.arrow_upward : Icons.arrow_downward,
                    color: isBuy ? Colors.green : Colors.red),
                const SizedBox(width: 8),
                Text('Trade Plan', style: Theme.of(context).textTheme.titleMedium),
              ],
            ),
            const SizedBox(height: 8),
            Text('Direction: $direction'),
            if (plan['price'] != null) Text('Target: \$${plan['price']}'),
            if (plan['stop_loss'] != null) Text('Stop Loss: \$${plan['stop_loss']}'),
            if (plan['take_profit'] != null) Text('Take Profit: \$${plan['take_profit']}'),
            if (plan['reasoning'] != null) ...[
              const SizedBox(height: 8),
              Text(plan['reasoning'].toString()),
            ],
          ],
        ),
      ),
    );
  }
}

class _AiAnalysisCard extends StatelessWidget {
  final Map<String, dynamic> analysis;
  const _AiAnalysisCard({required this.analysis});

  @override
  Widget build(BuildContext context) {
    final sentiment = (analysis['sentiment'] ?? 'neutral') as String;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.psychology, color: Colors.cyan),
                const SizedBox(width: 8),
                Text('AI Analysis', style: Theme.of(context).textTheme.titleMedium),
              ],
            ),
            const SizedBox(height: 8),
            Text('Sentiment: $sentiment'),
            if (analysis['summary'] != null) Text(analysis['summary'].toString()),
            if (analysis['confidence'] != null)
              LinearProgressIndicator(
                value: (analysis['confidence'] as num).toDouble() / 100,
                backgroundColor: Colors.grey.shade800,
              ),
          ],
        ),
      ),
    );
  }
}