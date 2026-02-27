import 'package:flutter/material.dart';
import '../theme.dart';
import '../widgets/app_card.dart';
import '../widgets/app_button.dart';

class ProfitCalculatorScreen extends StatefulWidget {
  const ProfitCalculatorScreen({super.key});

  @override
  State<ProfitCalculatorScreen> createState() => _ProfitCalculatorScreenState();
}

class _ProfitCalculatorScreenState extends State<ProfitCalculatorScreen> {
  final _expectedYield = TextEditingController(text: '10');
  final _sellingPrice = TextEditingController(text: '2120');
  final _seedCost = TextEditingController(text: '3000');
  final _fertilizerCost = TextEditingController(text: '5000');
  final _labourCost = TextEditingController(text: '8000');
  final _irrigationCost = TextEditingController(text: '2000');
  final _transportCost = TextEditingController(text: '1500');
  final _otherCost = TextEditingController(text: '0');

  bool _calculated = false;

  double get _totalRevenue {
    final yield_ = double.tryParse(_expectedYield.text) ?? 0;
    final price = double.tryParse(_sellingPrice.text) ?? 0;
    return yield_ * price;
  }

  double get _totalCost {
    return (double.tryParse(_seedCost.text) ?? 0) +
        (double.tryParse(_fertilizerCost.text) ?? 0) +
        (double.tryParse(_labourCost.text) ?? 0) +
        (double.tryParse(_irrigationCost.text) ?? 0) +
        (double.tryParse(_transportCost.text) ?? 0) +
        (double.tryParse(_otherCost.text) ?? 0);
  }

  double get _profit => _totalRevenue - _totalCost;

  void _calculate() {
    setState(() => _calculated = true);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Profit Calculator")),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text("Calculate Your Profit", style: AppTheme.headingMedium.copyWith(fontSize: 18)),
            const SizedBox(height: 4),
            Text("Know exactly what you'll earn", style: AppTheme.bodyMedium.copyWith(fontSize: 12)),
            const SizedBox(height: 16),

            _sectionHeader("Expected Revenue", Icons.monetization_on, AppTheme.primaryGreen),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    controller: _expectedYield,
                    keyboardType: TextInputType.number,
                    decoration: AppTheme.inputDecoration("Yield (Quintals)", Icons.eco),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: TextFormField(
                    controller: _sellingPrice,
                    keyboardType: TextInputType.number,
                    decoration: AppTheme.inputDecoration("Price ₹/Quintal", Icons.sell),
                  ),
                ),
              ],
            ),

            const SizedBox(height: 20),

            _sectionHeader("Your Costs", Icons.receipt_long, AppTheme.error),
            const SizedBox(height: 8),

            Row(
              children: [
                Expanded(child: _costField(_seedCost, "Seed ₹", Icons.eco)),
                const SizedBox(width: 8),
                Expanded(child: _costField(_fertilizerCost, "Fertilizer ₹", Icons.science)),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(child: _costField(_labourCost, "Labour ₹", Icons.people)),
                const SizedBox(width: 8),
                Expanded(child: _costField(_irrigationCost, "Irrigation ₹", Icons.water_drop)),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(child: _costField(_transportCost, "Transport ₹", Icons.local_shipping)),
                const SizedBox(width: 8),
                Expanded(child: _costField(_otherCost, "Other ₹", Icons.more_horiz)),
              ],
            ),

            const SizedBox(height: 24),
            AppButton(
              label: "Calculate Profit",
              onPressed: _calculate,
              icon: Icons.calculate,
            ),

            if (_calculated) ...[
              const SizedBox(height: 24),
              _buildResult(),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildResult() {
    final revenue = _totalRevenue;
    final cost = _totalCost;
    final profit = _profit;
    final isProfitable = profit > 0;

    return Column(
      children: [
        AppCard(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              _resultRow("Expected Revenue", "₹${_fmt(revenue)}", AppTheme.primaryGreen),
              const SizedBox(height: 6),
              _resultRow("Total Costs", "- ₹${_fmt(cost)}", AppTheme.error),
              const Divider(height: 20),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    isProfitable ? "Your Profit" : "Your Loss",
                    style: AppTheme.headingMedium.copyWith(fontSize: 16),
                  ),
                  Text(
                    "${isProfitable ? '' : '-'}₹${_fmt(profit.abs())}",
                    style: AppTheme.headingLarge.copyWith(
                      color: isProfitable ? AppTheme.primaryGreen : AppTheme.error,
                      fontSize: 26,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),

        const SizedBox(height: 12),

        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(AppTheme.cardRadius),
            border: Border.all(color: (isProfitable ? AppTheme.primaryGreen : AppTheme.error).withOpacity(0.3)),
          ),
          child: Row(
            children: [
              Text(isProfitable ? '✅' : '⚠️', style: const TextStyle(fontSize: 22)),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  isProfitable
                      ? "Good! You're making a ${((profit / revenue) * 100).toStringAsFixed(0)}% profit margin."
                      : "You're making a loss. Consider waiting for better price or reducing costs.",
                  style: AppTheme.bodyMedium.copyWith(
                    fontSize: 12,
                    color: isProfitable ? AppTheme.textDark : AppTheme.error,
                  ),
                ),
              ),
            ],
          ),
        ),

        const SizedBox(height: 12),

        AppCard(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text("Cost Breakdown", style: AppTheme.headingMedium.copyWith(fontSize: 13)),
              const SizedBox(height: 10),
              _breakdownBar("Seed", double.tryParse(_seedCost.text) ?? 0, cost),
              _breakdownBar("Fertilizer", double.tryParse(_fertilizerCost.text) ?? 0, cost),
              _breakdownBar("Labour", double.tryParse(_labourCost.text) ?? 0, cost),
              _breakdownBar("Irrigation", double.tryParse(_irrigationCost.text) ?? 0, cost),
              _breakdownBar("Transport", double.tryParse(_transportCost.text) ?? 0, cost),
              if ((double.tryParse(_otherCost.text) ?? 0) > 0)
                _breakdownBar("Other", double.tryParse(_otherCost.text) ?? 0, cost),
            ],
          ),
        ),
      ],
    );
  }

  Widget _breakdownBar(String label, double value, double total) {
    final pct = total > 0 ? value / total : 0.0;
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(label, style: AppTheme.bodyMedium.copyWith(fontSize: 11)),
              Text("₹${value.toStringAsFixed(0)} (${(pct * 100).toStringAsFixed(0)}%)", style: AppTheme.bodyMedium.copyWith(fontSize: 11)),
            ],
          ),
          const SizedBox(height: 3),
          ClipRRect(
            borderRadius: BorderRadius.circular(1),
            child: LinearProgressIndicator(
              value: pct,
              backgroundColor: AppTheme.cardBorder,
              color: AppTheme.accentOrange,
              minHeight: 5,
            ),
          ),
        ],
      ),
    );
  }

  Widget _resultRow(String label, String value, Color color) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: AppTheme.bodyMedium.copyWith(fontSize: 13)),
        Text(value, style: AppTheme.headingMedium.copyWith(color: color, fontSize: 16)),
      ],
    );
  }

  Widget _sectionHeader(String title, IconData icon, Color color) {
    return Row(
      children: [
        Icon(icon, color: color, size: 18),
        const SizedBox(width: 6),
        Text(title, style: AppTheme.headingMedium.copyWith(fontSize: 14)),
      ],
    );
  }

  Widget _costField(TextEditingController controller, String label, IconData icon) {
    return TextFormField(
      controller: controller,
      keyboardType: TextInputType.number,
      decoration: AppTheme.inputDecoration(label, icon),
      style: const TextStyle(fontSize: 13),
    );
  }

  String _fmt(double n) {
    if (n >= 100000) return "${(n / 100000).toStringAsFixed(1)} Lakh";
    if (n >= 1000) return "${(n / 1000).toStringAsFixed(1)}K";
    return n.toStringAsFixed(0);
  }
}
