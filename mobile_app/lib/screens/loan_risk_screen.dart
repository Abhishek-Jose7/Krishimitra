import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';

import '../providers/farmer_profile_provider.dart';
import '../services/api_service.dart';
import '../theme.dart';
import '../widgets/app_card.dart';

class LoanRiskScreen extends StatefulWidget {
  const LoanRiskScreen({super.key});

  @override
  State<LoanRiskScreen> createState() => _LoanRiskScreenState();
}

class _LoanRiskScreenState extends State<LoanRiskScreen> {
  final _formKey = GlobalKey<FormState>();
  final _loanAmountController = TextEditingController(text: '100000');
  final _interestRateController = TextEditingController(text: '12');
  final _tenureController = TextEditingController(text: '12');

  bool _loading = false;
  String? _error;
  Map<String, dynamic>? _result;

  @override
  void dispose() {
    _loanAmountController.dispose();
    _interestRateController.dispose();
    _tenureController.dispose();
    super.dispose();
  }

  Future<void> _analyze() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _loading = true;
      _error = null;
      _result = null;
    });

    try {
      final profile = Provider.of<FarmerProfile>(context, listen: false);
      final api = Provider.of<ApiService>(context, listen: false);
      final crop = profile.activeCrop?.cropName ?? profile.primaryCrop ?? 'Rice';
      final district = profile.district ?? 'Pune';
      final loanAmount = double.tryParse(_loanAmountController.text) ?? 100000;
      final interestRate = double.tryParse(_interestRateController.text) ?? 12;
      final tenure = int.tryParse(_tenureController.text) ?? 12;

      final resp = await api.getLoanRisk(
        crop: crop,
        district: district,
        loanAmount: loanAmount,
        interestRate: interestRate,
        tenureMonths: tenure,
      );
      _result = resp;
    } catch (e) {
      _error = e.toString();
    }

    if (mounted) {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final profile = Provider.of<FarmerProfile>(context);
    final crop = profile.activeCrop?.cropName ?? profile.primaryCrop ?? 'Rice';
    final district = profile.district ?? 'Pune';

    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            const Icon(Icons.account_balance_wallet_outlined, size: 20),
            const SizedBox(width: 8),
            Text(
              'Loan Risk Assistant',
              style: GoogleFonts.playfairDisplay(
                fontStyle: FontStyle.italic,
                fontWeight: FontWeight.w700,
                color: Colors.white,
              ),
            ),
          ],
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _buildHeader(crop: crop, district: district),
            const SizedBox(height: 16),
            _buildForm(),
            const SizedBox(height: 16),
            if (_error != null) _buildError(),
            if (_result != null) ...[
              _buildRiskGauge(_result!),
              const SizedBox(height: 12),
              _buildStressRatios(_result!),
              const SizedBox(height: 12),
              _buildRecommendations(_result!),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildHeader({required String crop, required String district}) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            AppTheme.primaryGreen,
            AppTheme.secondaryGreen.withOpacity(0.95),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(AppTheme.cardRadius),
        boxShadow: [
          BoxShadow(
            color: AppTheme.primaryGreen.withOpacity(0.18),
            blurRadius: 16,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.15),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              'Financial Stress Simulator',
              style: GoogleFonts.dmSans(
                color: Colors.white,
                fontSize: 11,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          const SizedBox(height: 10),
          Text(
            '$crop • $district',
            style: GoogleFonts.playfairDisplay(
              color: Colors.white,
              fontSize: 22,
              fontWeight: FontWeight.w800,
              fontStyle: FontStyle.italic,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            'See how loan repayment fits your expected farm income.',
            style: GoogleFonts.dmSans(
              color: Colors.white70,
              fontSize: 12,
              height: 1.4,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildForm() {
    return AppCard(
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Loan details',
              style: AppTheme.headingMedium.copyWith(fontSize: 14),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _loanAmountController,
              keyboardType: TextInputType.number,
              decoration: AppTheme.inputDecoration('Loan amount (₹)', Icons.currency_rupee),
              validator: (v) {
                if (v == null || v.isEmpty) return 'Required';
                if (double.tryParse(v) == null) return 'Enter a number';
                return null;
              },
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _interestRateController,
              keyboardType: TextInputType.number,
              decoration: AppTheme.inputDecoration('Interest rate (% p.a.)', Icons.percent),
              validator: (v) {
                if (v == null || v.isEmpty) return 'Required';
                if (double.tryParse(v) == null) return 'Enter a number';
                return null;
              },
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _tenureController,
              keyboardType: TextInputType.number,
              decoration: AppTheme.inputDecoration('Tenure (months)', Icons.calendar_today),
              validator: (v) {
                if (v == null || v.isEmpty) return 'Required';
                if (int.tryParse(v) == null) return 'Enter whole number';
                return null;
              },
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _loading ? null : _analyze,
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primaryGreen,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(AppTheme.buttonRadius),
                  ),
                ),
                child: _loading
                    ? const SizedBox(
                        height: 22,
                        width: 22,
                        child: CircularProgressIndicator(
                          color: Colors.white,
                          strokeWidth: 2,
                        ),
                      )
                    : const Text('Analyze loan risk'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildError() {
    return AppCard(
      color: const Color(0xFFFFEBEE),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.error_outline, color: AppTheme.error),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              _error!,
              style: AppTheme.bodyMedium.copyWith(
                fontSize: 11,
                color: AppTheme.textDark,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRiskGauge(Map<String, dynamic> data) {
    final score = (data['loan_risk_score'] ?? 0).toDouble();
    final level = (data['loan_risk_level'] ?? 'LOW').toString();

    Color c;
    String label;
    if (level == 'HIGH') {
      c = AppTheme.error;
      label = 'High Risk';
    } else if (level == 'MODERATE') {
      c = AppTheme.accentOrange;
      label = 'Moderate Risk';
    } else {
      c = AppTheme.success;
      label = 'Low Risk';
    }

    final progress = (score.clamp(0.0, 100.0)) / 100.0;

    return AppCard(
      child: Row(
        children: [
          SizedBox(
            width: 92,
            height: 92,
            child: Stack(
              alignment: Alignment.center,
              children: [
                CircularProgressIndicator(
                  value: 1,
                  strokeWidth: 10,
                  valueColor: AlwaysStoppedAnimation<Color>(Colors.grey.shade200),
                ),
                CircularProgressIndicator(
                  value: progress,
                  strokeWidth: 10,
                  valueColor: AlwaysStoppedAnimation<Color>(c),
                  backgroundColor: Colors.transparent,
                ),
                Align(
                  alignment: Alignment.center,
                  child: Text(
                    score.toStringAsFixed(0),
                    style: GoogleFonts.roboto(
                      fontSize: 26,
                      fontWeight: FontWeight.w900,
                      color: AppTheme.textDark,
                    ),
                  ),
                ),
                Align(
                  alignment: Alignment.bottomCenter,
                  child: Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: Text(
                      'Risk',
                      style: AppTheme.bodyMedium.copyWith(fontSize: 10),
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Loan Risk Score',
                  style: AppTheme.headingMedium.copyWith(fontSize: 14),
                ),
                const SizedBox(height: 4),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: c.withOpacity(0.08),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: c.withOpacity(0.25)),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        level == 'HIGH'
                            ? Icons.warning_amber
                            : level == 'MODERATE'
                                ? Icons.info_outline
                                : Icons.verified,
                        size: 16,
                        color: c,
                      ),
                      const SizedBox(width: 6),
                      Text(
                        label,
                        style: AppTheme.bodyMedium.copyWith(
                          fontSize: 11,
                          color: c,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStressRatios(Map<String, dynamic> data) {
    final repaymentRatio = (data['repayment_ratio'] ?? 0).toDouble();
    final worstCaseRatio = (data['worst_case_ratio'] ?? 0).toDouble();
    final expectedIncome = (data['expected_income'] ?? 0).toDouble();
    final monthlyEmi = (data['monthly_emi'] ?? 0).toDouble();

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Stress & scenario',
            style: AppTheme.headingMedium.copyWith(fontSize: 14),
          ),
          const SizedBox(height: 10),
          _ratioRow('Repayment ratio', repaymentRatio),
          const SizedBox(height: 8),
          _ratioRow('Worst-case ratio', worstCaseRatio),
          const SizedBox(height: 12),
          const Divider(height: 1),
          const SizedBox(height: 10),
          _moneyRow('Expected income (season)', expectedIncome),
          const SizedBox(height: 6),
          _moneyRow('Monthly EMI', monthlyEmi),
        ],
      ),
    );
  }

  Widget _ratioRow(String label, double value) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: AppTheme.bodyMedium.copyWith(fontSize: 12)),
        Text(
          value.toStringAsFixed(2),
          style: AppTheme.headingMedium.copyWith(fontSize: 14),
        ),
      ],
    );
  }

  Widget _moneyRow(String label, double value) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: AppTheme.bodyMedium.copyWith(fontSize: 12)),
        Text(
          '₹${value.toStringAsFixed(0)}',
          style: AppTheme.headingMedium.copyWith(fontSize: 14),
        ),
      ],
    );
  }

  Widget _buildRecommendations(Map<String, dynamic> data) {
    final list = (data['recommendations'] as List?)?.cast<String>() ?? [];
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Recommendations',
            style: AppTheme.headingMedium.copyWith(fontSize: 14),
          ),
          const SizedBox(height: 10),
          if (list.isEmpty)
            Text(
              'No specific recommendations.',
              style: AppTheme.bodyMedium.copyWith(fontSize: 12),
            )
          else
            ...list.map(
              (s) => Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.lightbulb_outline,
                        size: 16, color: AppTheme.accentGold),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        s,
                        style: AppTheme.bodyMedium.copyWith(fontSize: 12),
                      ),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}
