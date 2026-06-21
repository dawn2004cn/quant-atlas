import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../providers/portfolio_provider.dart';

class PortfolioPage extends StatefulWidget {
  const PortfolioPage({super.key});

  @override
  State<PortfolioPage> createState() => _PortfolioPageState();
}

class _PortfolioPageState extends State<PortfolioPage> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final userId = context.read<AuthProvider>().userId;
      context.read<PortfolioProvider>().fetchPortfolio(userId);
    });
  }

  @override
  Widget build(BuildContext context) {
    final portfolio = context.watch<PortfolioProvider>();

    return Scaffold(
      appBar: AppBar(title: const Text('Portfolio')),
      body: portfolio.loading
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                Card(
                  margin: const EdgeInsets.all(16),
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('Total Value', style: TextStyle(fontSize: 16)),
                        Text(
                          '\$${portfolio.totalValue.toStringAsFixed(2)}',
                          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                                fontWeight: FontWeight.bold,
                              ),
                        ),
                      ],
                    ),
                  ),
                ),
                Expanded(
                  child: ListView.builder(
                    itemCount: portfolio.positions.length,
                    itemBuilder: (_, i) {
                      final p = portfolio.positions[i];
                      return ListTile(
                        title: Text(p.symbol),
                        subtitle: Text('${p.quantity.toStringAsFixed(0)} @ \$${p.avgPrice.toStringAsFixed(2)}'),
                        trailing: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            Text('\$${p.marketValue.toStringAsFixed(2)}'),
                            Text(
                              p.pnl >= 0 ? '+\$${p.pnl.toStringAsFixed(2)}' : '-\$${p.pnl.abs().toStringAsFixed(2)}',
                              style: TextStyle(
                                color: p.pnl >= 0 ? Colors.green : Colors.red,
                                fontSize: 12,
                              ),
                            ),
                          ],
                        ),
                      );
                    },
                  ),
                ),
              ],
            ),
    );
  }
}