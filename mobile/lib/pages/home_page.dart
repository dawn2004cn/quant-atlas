import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/market_provider.dart';
import 'stock_detail_page.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<MarketProvider>().fetchQuotes();
    });
  }

  @override
  Widget build(BuildContext context) {
    final market = context.watch<MarketProvider>();

    return Scaffold(
      appBar: AppBar(title: const Text('Market')),
      body: market.loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: () => market.fetchQuotes(),
              child: ListView.builder(
                itemCount: market.quotes.length,
                itemBuilder: (_, i) {
                  final q = market.quotes[i];
                  final isUp = q.change >= 0;
                  return ListTile(
                    leading: CircleAvatar(
                      backgroundColor: isUp ? Colors.green.shade800 : Colors.red.shade800,
                      child: Text(
                        q.symbol.substring(0, 1),
                        style: const TextStyle(color: Colors.white),
                      ),
                    ),
                    title: Text(q.symbol, style: const TextStyle(fontWeight: FontWeight.w600)),
                    subtitle: Text('${q.price.toStringAsFixed(2)}  ${isUp ? '+' : ''}${q.changePct.toStringAsFixed(2)}%'),
                    trailing: Text(
                      isUp ? '+${q.change.toStringAsFixed(2)}' : q.change.toStringAsFixed(2),
                      style: TextStyle(
                        color: isUp ? Colors.green : Colors.red,
                        fontWeight: FontWeight.bold,
                        fontSize: 16,
                      ),
                    ),
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => StockDetailPage(symbol: q.symbol),
                      ),
                    ),
                  );
                },
              ),
            ),
    );
  }
}