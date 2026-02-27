import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_service.dart';
import '../theme.dart';
import '../widgets/app_button.dart';
import '../widgets/app_card.dart';

class RecommendationScreen extends StatefulWidget {
  const RecommendationScreen({super.key});

  @override
  State<RecommendationScreen> createState() => _RecommendationScreenState();
}

class _RecommendationScreenState extends State<RecommendationScreen> {
  String _crop = 'Rice';
  final String _district = 'Pune';
  String _mandi = 'Pune Mandi';
  final _landController = TextEditingController(text: '2');

  final _seedCost = TextEditingController(text: '0');
  final _fertilizerCost = TextEditingController(text: '0');
  final _labourCost = TextEditingController(text: '0');
  final _irrigationCost = TextEditingController(text: '0');

  Map<String, dynamic>? _result;
  bool _isLoading = false;
  bool _showCostInputs = false;

  final List<String> _crops = ['Rice', 'Wheat', 'Maize', 'Soybean'];
  final List<String> _mandis = ['Pune Mandi', 'Nashik Mandi', 'Nagpur Mandi', 'Aurangabad Mandi'];

  Future<void> _getAdvice() async {
    setState(() => _isLoading = true);
    try {
      final api = Provider.of<ApiService>(context, listen: false);
      final result = await api.getRecommendation({
        'crop': _crop,
        'district': _district,
        'land_size': double.tryParse(_landController.text) ?? 2,
        'mandi': _mandi,
        'soil_type': 'Black',
        'seed_cost': double.tryParse(_seedCost.text) ?? 0,
        'fertilizer_cost': double.tryParse(_fertilizerCost.text) ?? 0,
        'labour_cost': double.tryParse(_labourCost.text) ?? 0,
        'irrigation_cost': double.tryParse(_irrigationCost.text) ?? 0,
      });
      setState(() => _result = result);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Error: $e")));
      }
    } finally {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Should I Sell or Wait?")),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text("Your Details", style: AppTheme.headingMedium.copyWith(fontSize: 16)),
            const SizedBox(height: 4),
            Text("Just 3 things needed", style: AppTheme.bodyMedium.copyWith(fontSize: 12)),
            const SizedBox(height: 12),

            DropdownButtonFormField(
              value: _crop,
              items: _crops.map((e) => DropdownMenuItem(value: e, child: Text(e))).toList(),
              onChanged: (v) => setState(() => _crop = v!),
              decoration: AppTheme.inputDecoration("Your Crop", Icons.grass),
            ),
            const SizedBox(height: 10),

            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    controller: _landController,
                    keyboardType: TextInputType.number,
                    decoration: AppTheme.inputDecoration("Land (Acres)", Icons.square_foot),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: DropdownButtonFormField(
                    value: _mandi,
                    items: _mandis.map((e) => DropdownMenuItem(value: e, child: Text(e, style: const TextStyle(fontSize: 12)))).toList(),
                    onChanged: (v) => setState(() => _mandi = v!),
                    decoration: AppTheme.inputDecoration("Mandi", Icons.storefront),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),

            // Optional costs
            GestureDetector(
              onTap: () => setState(() => _showCostInputs = !_showCostInputs),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                decoration: BoxDecoration(
                  color: AppTheme.lightGreen,
                  borderRadius: BorderRadius.circular(AppTheme.cardRadius),
                  border: Border.all(color: AppTheme.primaryGreen.withOpacity(0.2)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.calculate, color: AppTheme.primaryGreen, size: 18),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        "Add costs for profit calculation",
                        style: AppTheme.bodyMedium.copyWith(fontSize: 12, color: AppTheme.primaryGreen),
                      ),
                    ),
                    Icon(_showCostInputs ? Icons.expand_less : Icons.expand_more, color: AppTheme.primaryGreen, size: 18),
                  ],
                ),
              ),
            ),

            if (_showCostInputs) ...[
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(child: TextFormField(controller: _seedCost, keyboardType: TextInputType.number, decoration: AppTheme.inputDecoration("Seed ₹", Icons.eco))),
                  const SizedBox(width: 8),
                  Expanded(child: TextFormField(controller: _fertilizerCost, keyboardType: TextInputType.number, decoration: AppTheme.inputDecoration("Fertilizer ₹", Icons.science))),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(child: TextFormField(controller: _labourCost, keyboardType: TextInputType.number, decoration: AppTheme.inputDecoration("Labour ₹", Icons.people))),
                  const SizedBox(width: 8),
                  Expanded(child: TextFormField(controller: _irrigationCost, keyboardType: TextInputType.number, decoration: AppTheme.inputDecoration("Water ₹", Icons.water_drop))),
                ],
              ),
            ],

            const SizedBox(height: 20),
            AppButton(
              label: "Get Selling Advice",
              onPressed: _isLoading ? null : _getAdvice,
              isLoading: _isLoading,
              icon: Icons.lightbulb_outline,
            ),

            if (_result != null) ...[
              const SizedBox(height: 24),
              _buildResultCard(),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildResultCard() {
    final rec = _result!;
    final isSell = rec['recommendation'] == 'SELL NOW';
    final riskLevel = rec['risk_level'] ?? 'LOW';
    final sellNow = (rec['sell_now_revenue'] ?? 0).toDouble();
    final sellPeak = (rec['sell_peak_revenue'] ?? 0).toDouble();
    final extraProfit = (rec['extra_profit'] ?? 0).toDouble();
    final waitDays = rec['wait_days'] ?? 0;
    final profitNow = (rec['profit_if_sell_now'] ?? 0).toDouble();
    final profitPeak = (rec['profit_if_hold'] ?? 0).toDouble();
    final totalInputCost = (rec['input_cost']?['total'] ?? 0).toDouble();
    final storage = rec['storage_advice'];

    return Column(
      children: [
        // Hero Recommendation
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: isSell ? AppTheme.primaryGreen : AppTheme.accentOrange,
            borderRadius: BorderRadius.circular(AppTheme.cardRadius),
          ),
          child: Column(
            children: [
              Icon(isSell ? Icons.sell : Icons.hourglass_bottom, color: Colors.white, size: 36),
              const SizedBox(height: 6),
              Text(
                isSell ? "SELL NOW" : "HOLD & WAIT",
                style: AppTheme.headingLarge.copyWith(color: Colors.white, fontSize: 24, letterSpacing: 1),
              ),
              const SizedBox(height: 4),
              Text(
                rec['explanation'] ?? '',
                style: AppTheme.bodyMedium.copyWith(color: Colors.white.withOpacity(0.9), fontSize: 12),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 4),
              Text(
                "Risk: ${rec['risk_emoji'] ?? ''} $riskLevel",
                style: AppTheme.bodyMedium.copyWith(color: Colors.white.withOpacity(0.8), fontSize: 11),
              ),
            ],
          ),
        ),

        const SizedBox(height: 12),

        // Revenue Comparison
        AppCard(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              Text("Revenue Comparison", style: AppTheme.headingMedium.copyWith(fontSize: 14)),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(child: _revenueBox("Sell Today", "₹${_fmt(sellNow)}", AppTheme.textDark)),
                  const SizedBox(width: 8),
                  const Text("vs", style: TextStyle(color: Colors.grey, fontSize: 12)),
                  const SizedBox(width: 8),
                  Expanded(child: _revenueBox("Wait ~$waitDays days", "₹${_fmt(sellPeak)}", AppTheme.primaryGreen)),
                ],
              ),
              if (extraProfit > 0) ...[
                const SizedBox(height: 10),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: AppTheme.lightGreen,
                    borderRadius: BorderRadius.circular(AppTheme.cardRadius),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.arrow_upward, color: AppTheme.primaryGreen, size: 16),
                      const SizedBox(width: 6),
                      Text(
                        "Extra Profit: ₹${_fmt(extraProfit)}",
                        style: AppTheme.bodyMedium.copyWith(color: AppTheme.primaryGreen, fontWeight: FontWeight.bold, fontSize: 13),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),

        // Profit after costs
        if (totalInputCost > 0) ...[
          const SizedBox(height: 12),
          AppCard(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                Text("After Your Costs", style: AppTheme.headingMedium.copyWith(fontSize: 14)),
                const SizedBox(height: 10),
                _costRow("Total Input Cost", "₹${_fmt(totalInputCost)}", Colors.grey),
                const SizedBox(height: 4),
                _costRow("Profit if Sell Now", "₹${_fmt(profitNow)}", profitNow > 0 ? AppTheme.primaryGreen : AppTheme.error),
                const SizedBox(height: 4),
                _costRow("Profit if Hold", "₹${_fmt(profitPeak)}", profitPeak > 0 ? AppTheme.primaryGreen : AppTheme.error),
              ],
            ),
          ),
        ],

        // Storage advice
        if (storage != null) ...[
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(AppTheme.cardRadius),
              border: Border.all(color: AppTheme.accentOrange.withOpacity(0.3)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.warehouse, color: AppTheme.accentOrange, size: 20),
                    const SizedBox(width: 8),
                    Text("Storage Tips", style: AppTheme.headingMedium.copyWith(fontSize: 14)),
                  ],
                ),
                const SizedBox(height: 10),
                Text("📦 ${storage['method']}", style: AppTheme.bodyMedium.copyWith(fontSize: 12, color: AppTheme.textDark)),
                const SizedBox(height: 4),
                Text("⏱ Safe for ${storage['safe_days']} days", style: AppTheme.bodyMedium.copyWith(fontSize: 12, color: AppTheme.textDark)),
                const SizedBox(height: 4),
                Text("⚠️ ${storage['quality_risk']}", style: AppTheme.bodyMedium.copyWith(fontSize: 12, color: AppTheme.accentOrange)),
                if (storage['can_safely_hold'] == false) ...[
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: AppTheme.error.withOpacity(0.06),
                      borderRadius: BorderRadius.circular(2),
                    ),
                    child: Text(
                      "⚠ Wait time exceeds safe storage. Consider selling sooner.",
                      style: AppTheme.bodyMedium.copyWith(color: AppTheme.error, fontSize: 11, fontWeight: FontWeight.w500),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],

        const SizedBox(height: 12),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: AppTheme.background,
            borderRadius: BorderRadius.circular(AppTheme.cardRadius),
            border: Border.all(color: Colors.grey.shade300),
          ),
          child: Row(
            children: [
              Text(rec['risk_emoji'] ?? '🟢', style: const TextStyle(fontSize: 20)),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  rec['risk_message'] ?? '',
                  style: AppTheme.bodyMedium.copyWith(fontSize: 12, color: AppTheme.textDark),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _revenueBox(String label, String value, Color valueColor) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 10),
      decoration: BoxDecoration(
        color: AppTheme.background,
        borderRadius: BorderRadius.circular(AppTheme.cardRadius),
      ),
      child: Column(
        children: [
          Text(label, style: AppTheme.bodyMedium.copyWith(fontSize: 11)),
          const SizedBox(height: 2),
          Text(value, style: AppTheme.headingMedium.copyWith(color: valueColor, fontSize: 16)),
        ],
      ),
    );
  }

  Widget _costRow(String label, String value, Color color) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: AppTheme.bodyMedium.copyWith(fontSize: 12)),
        Text(value, style: AppTheme.bodyMedium.copyWith(fontWeight: FontWeight.bold, color: color, fontSize: 13)),
      ],
    );
  }

  String _fmt(double n) {
    if (n >= 100000) return "${(n / 100000).toStringAsFixed(1)}L";
    if (n >= 1000) return "${(n / 1000).toStringAsFixed(1)}K";
    return n.toStringAsFixed(0);
  }
}
