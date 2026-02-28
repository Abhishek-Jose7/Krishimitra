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
  String? _crop;
  String? _district;
  final _landController = TextEditingController();

  Map<String, dynamic>? _result;
  String? _advisory;
  bool _isLoading = false;

  List<String> _crops = [];
  List<String> _districts = [];

  @override
  void initState() {
    super.initState();
    _loadOptions();
  }

  Future<void> _loadOptions() async {
    try {
      final api = Provider.of<ApiService>(context, listen: false);
      final opts = await api.getYieldOptions();
      final crops = (opts['crop'] as List<dynamic>? ?? []).cast<String>();
      final districts = (opts['district'] as List<dynamic>? ?? []).cast<String>();
      setState(() {
        _crops = crops;
        _districts = districts;
        _crop ??= _crops.isNotEmpty ? _crops.first : null;
        _district ??= _districts.isNotEmpty ? _districts.first : null;
      });
    } catch (e) {
      // Fallback to hardcoded defaults if options fetch fails
      setState(() {
        _crops = ['Rice', 'Wheat', 'Maize', 'Soybean'];
        _districts = ['Mysuru', 'Pune'];
        _crop ??= _crops.first;
        _district ??= _districts.first;
      });
    }
  }

  void _showIndicativeFallback(double landSize) {
    final cropName = _crop ?? 'Crop';
    final districtName = _district ?? 'your district';
    final yieldPerAcre = _heuristicYieldPerAcre(cropName);
    final totalYield = yieldPerAcre * landSize;
    final advisory = 'For $cropName in $districtName, we are providing an indicative estimate '
        'based on typical conditions: about ${yieldPerAcre.toStringAsFixed(1)} tons per acre, '
        'or ${totalYield.toStringAsFixed(1)} tons total for your area. '
        'For precise planning, consult local agronomy or try again later.';
    setState(() {
      _result = {
        'predicted_yield_per_hectare': yieldPerAcre,
        'total_expected_production': totalYield,
        'confidence': 0.5,
        'risk': 'Moderate',
        'explanation_text': advisory,
      };
      _advisory = advisory;
    });
  }

  double _heuristicYieldPerAcre(String crop) {
    final c = crop.toLowerCase();
    if (c.contains('rice')) return 4.5;
    if (c.contains('wheat')) return 3.5;
    if (c.contains('maize')) return 3.0;
    if (c.contains('soybean')) return 1.2;
    if (c.contains('cotton')) return 1.8;
    if (c.contains('sugarcane')) return 28.0;
    if (c.contains('groundnut')) return 1.5;
    if (c.contains('onion')) return 12.0;
    if (c.contains('tomato')) return 18.0;
    if (c.contains('potato')) return 15.0;
    if (c.contains('coconut')) return 8.0;
    return 3.0;
  }

  Future<void> _predict() async {
    if (_formKey.currentState!.validate()) {
      setState(() => _isLoading = true);
      try {
        final api = Provider.of<ApiService>(context, listen: false);
        final landSize = double.tryParse(_landController.text) ?? 1.0;

        final advisoryResp = await api.simulateYield({
          'district': _district,
          'crop': _crop,
          'season': 'Kharif',
          'soil_type': 'Black',
          'irrigation': 'Canal',
          'area': landSize,
        });

        final summary = (advisoryResp['summary'] as Map<String, dynamic>?);
        final predictedYieldPerHa = (summary?['predicted_yield'] ?? 0).toDouble();
        final totalYield = (summary?['estimated_total_yield'] ?? 0).toDouble();
        final confidencePct = (summary?['confidence'] ?? 0).toDouble();
        final riskLevel = summary?['risk_level'] as String? ?? 'Moderate';
        final advisoryText = advisoryResp['advisory'] as String? ?? '';

        if (predictedYieldPerHa <= 0 && totalYield <= 0) {
          _showIndicativeFallback(landSize);
        } else {
          final explanation = advisoryText.isNotEmpty
              ? advisoryText
              : 'Estimate based on model output for $_crop in $_district.';
          setState(() {
            _result = {
              'predicted_yield_per_hectare': predictedYieldPerHa,
              'total_expected_production': totalYield,
              'confidence': (confidencePct / 100.0).clamp(0.0, 1.0),
              'risk': riskLevel,
              'explanation_text': explanation,
            };
            _advisory = advisoryText.isNotEmpty ? advisoryText : explanation;
          });
        }
      } catch (e) {
        final landSize = double.tryParse(_landController.text) ?? 1.0;
        _showIndicativeFallback(landSize);
      } finally {
        if (mounted) setState(() => _isLoading = false);
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
              if (_advisory != null && _advisory!.isNotEmpty) ...[
                const SizedBox(height: 16),
                _buildAdvisoryCard(),
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

  Widget _buildAdvisoryCard() {
    return AppCard(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.article_outlined, color: AppTheme.accentBlue, size: 20),
              const SizedBox(width: 8),
              Text(
                "AI Advisory (Mysuru Model)",
                style: AppTheme.headingMedium.copyWith(fontSize: 14),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            _advisory ?? '',
            style: AppTheme.bodyMedium.copyWith(fontSize: 11, height: 1.4),
          ),
        ],
      ),
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
