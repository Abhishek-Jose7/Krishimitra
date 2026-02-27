import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_service.dart';
import '../theme.dart';
import '../widgets/app_button.dart';
import '../widgets/app_card.dart';

class YieldScreen extends StatefulWidget {
  const YieldScreen({super.key});

  @override
  State<YieldScreen> createState() => _YieldScreenState();
}

class _YieldScreenState extends State<YieldScreen> {
  final _formKey = GlobalKey<FormState>();
  String? _crop = 'Rice';
  String? _district = 'Pune';
  final _landController = TextEditingController();

  Map<String, dynamic>? _result;
  bool _isLoading = false;

  final List<String> _crops = ['Rice', 'Wheat', 'Maize', 'Soybean'];
  final List<String> _districts = ['Pune', 'Nashik', 'Nagpur', 'Aurangabad'];

  Future<void> _predict() async {
    if (_formKey.currentState!.validate()) {
      setState(() => _isLoading = true);
      try {
        final api = Provider.of<ApiService>(context, listen: false);
        final result = await api.predictYield({
          'crop': _crop,
          'district': _district,
          'land_size': double.parse(_landController.text),
          'soil_type': 'Black',
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
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Yield Estimate")),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text("Predict Your Harvest", style: AppTheme.headingMedium.copyWith(fontSize: 18)),
              const SizedBox(height: 4),
              Text("Enter your crop & land details", style: AppTheme.bodyMedium.copyWith(fontSize: 12)),
              const SizedBox(height: 16),

              DropdownButtonFormField(
                value: _crop,
                items: _crops.map((e) => DropdownMenuItem(value: e, child: Text(e))).toList(),
                onChanged: (v) => setState(() => _crop = v),
                decoration: AppTheme.inputDecoration("Your Crop", Icons.grass),
                validator: (v) => v == null ? "Required" : null,
              ),
              const SizedBox(height: 10),

              Row(
                children: [
                  Expanded(
                    child: DropdownButtonFormField(
                      value: _district,
                      items: _districts.map((e) => DropdownMenuItem(value: e, child: Text(e))).toList(),
                      onChanged: (v) => setState(() => _district = v),
                      decoration: AppTheme.inputDecoration("District", Icons.location_on_outlined),
                      validator: (v) => v == null ? "Required" : null,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: TextFormField(
                      controller: _landController,
                      keyboardType: TextInputType.number,
                      decoration: AppTheme.inputDecoration("Land (Acres)", Icons.square_foot),
                      validator: (v) => v!.isEmpty ? "Required" : null,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),

              AppButton(
                label: "Estimate Harvest",
                onPressed: _predict,
                isLoading: _isLoading,
                icon: Icons.grass,
              ),

              if (_result != null) ...[
                const SizedBox(height: 24),
                _buildResultCard(),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildResultCard() {
    final yieldPerUnit = (_result!['predicted_yield_per_hectare'] ?? 0).toDouble();
    final totalProduction = (_result!['total_expected_production'] ?? 0).toDouble();
    final confidence = (_result!['confidence'] ?? 0).toDouble();
    final risk = _result!['risk'] ?? 'Moderate';
    final explanation = _result!['explanation_text'] ?? '';

    const estimatedPricePerTon = 21200.0;
    final estimatedRevenue = totalProduction * estimatedPricePerTon;

    return Column(
      children: [
        AppCard(
          padding: const EdgeInsets.all(20),
          child: Column(
            children: [
              const Icon(Icons.eco, color: AppTheme.primaryGreen, size: 32),
              const SizedBox(height: 6),
              Text("Estimated Harvest", style: AppTheme.headingMedium.copyWith(fontSize: 14)),
              const SizedBox(height: 10),

              Text(
                "${totalProduction.toStringAsFixed(1)} Tons",
                style: AppTheme.headingLarge.copyWith(color: AppTheme.primaryGreen, fontSize: 34),
              ),
              Text(
                "(${yieldPerUnit.toStringAsFixed(1)} tons/acre)",
                style: AppTheme.bodyMedium.copyWith(fontSize: 12),
              ),

              const SizedBox(height: 16),

              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppTheme.lightGreen,
                  borderRadius: BorderRadius.circular(AppTheme.cardRadius),
                ),
                child: Column(
                  children: [
                    Text("At Current Market Price", style: AppTheme.bodyMedium.copyWith(fontSize: 11)),
                    const SizedBox(height: 2),
                    Text(
                      "Estimated Revenue: ₹${_formatNumber(estimatedRevenue)}",
                      style: AppTheme.headingMedium.copyWith(color: AppTheme.primaryGreen, fontSize: 16),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),

        const SizedBox(height: 12),

        Row(
          children: [
            Expanded(
              child: _miniInfo(
                risk == 'Low' ? '🟢' : '🟡',
                "Risk",
                risk,
                risk == 'Low' ? AppTheme.primaryGreen : AppTheme.accentOrange,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _miniInfo(
                '📊',
                "Reliability",
                "${(confidence * 100).toStringAsFixed(0)}%",
                AppTheme.accentBlue,
              ),
            ),
          ],
        ),

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
              const Icon(Icons.wb_sunny_outlined, color: AppTheme.accentOrange, size: 18),
              const SizedBox(width: 8),
              Expanded(child: Text(explanation, style: AppTheme.bodyMedium.copyWith(fontSize: 11, color: AppTheme.textDark))),
            ],
          ),
        ),
      ],
    );
  }

  Widget _miniInfo(String emoji, String label, String value, Color color) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(AppTheme.cardRadius),
        border: Border.all(color: color.withOpacity(0.2)),
      ),
      child: Column(
        children: [
          Text(emoji, style: const TextStyle(fontSize: 20)),
          const SizedBox(height: 2),
          Text(label, style: AppTheme.bodyMedium.copyWith(fontSize: 10)),
          Text(value, style: AppTheme.headingMedium.copyWith(fontSize: 15, color: color)),
        ],
      ),
    );
  }

  String _formatNumber(double n) {
    if (n >= 100000) return "${(n / 100000).toStringAsFixed(1)} Lakh";
    if (n >= 1000) return "${(n / 1000).toStringAsFixed(1)}K";
    return n.toStringAsFixed(0);
  }
}
