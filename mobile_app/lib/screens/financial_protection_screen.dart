import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../providers/farmer_profile_provider.dart';
import '../services/api_service.dart';
import '../theme.dart';
import '../widgets/app_card.dart';
import '../widgets/crop_selector_widget.dart';

class FinancialProtectionScreen extends StatefulWidget {
  const FinancialProtectionScreen({super.key});

  @override
  State<FinancialProtectionScreen> createState() => _FinancialProtectionScreenState();
}

class _FinancialProtectionScreenState extends State<FinancialProtectionScreen> {
  bool _loading = true;
  String? _error;
  Map<String, dynamic>? _data;
  String? _lastUpdated;
  List<String> _crops = ['Chickpea', 'Sugarcane', 'Onion'];
  String _selectedCrop = 'Onion';

  /// Persistent per-crop cache so score stays stable on navigation/rebuild.
  /// Key: crop name, Value: last API response for that crop.
  static final Map<String, Map<String, dynamic>> _cropDataCache = {};

  @override
  void initState() {
    super.initState();
    final profile = Provider.of<FarmerProfile>(context, listen: false);
    if (profile.crops.isNotEmpty) {
      _crops = profile.crops;
    }
    _selectedCrop = _crops.contains('Onion')
        ? 'Onion'
        : (profile.primaryCrop ?? profile.activeCrop?.cropName ?? _crops.first);
    final cached = _cropDataCache[_selectedCrop];
    if (cached != null) {
      _data = Map<String, dynamic>.from(cached);
      _lastUpdated = _formatNow();
      _loading = false;
      _error = null;
    } else {
      _load();
    }
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final profile = Provider.of<FarmerProfile>(context, listen: false);
      final api = Provider.of<ApiService>(context, listen: false);
      final district = profile.district ?? 'Pune';
      final mandi = profile.activeMandiName;

      final resp = await api.getFinancialProtection(
        crop: _selectedCrop,
        district: district,
        mandi: mandi,
      );
      _cropDataCache[_selectedCrop] = Map<String, dynamic>.from(resp);
      _data = resp;
      _lastUpdated = _formatNow();
    } catch (e) {
      _error = e.toString();
    }

    if (mounted) {
      setState(() => _loading = false);
    }
  }

  String _formatNow() {
    final now = DateTime.now();
    return "${now.day}/${now.month}/${now.year} ${now.hour}:${now.minute.toString().padLeft(2, '0')}";
  }

  @override
  Widget build(BuildContext context) {
    final profile = Provider.of<FarmerProfile>(context);
    final district = profile.district ?? 'Pune';

    return Scaffold(
      appBar: AppBar(
        title: Row(children: [
          const Icon(Icons.shield_outlined, size: 20),
          const SizedBox(width: 8),
          Text(
            "Financial Protection",
            style: GoogleFonts.playfairDisplay(
              fontStyle: FontStyle.italic,
              fontWeight: FontWeight.w700,
              color: Colors.white,
            ),
          ),
        ]),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _load,
            tooltip: "Refresh",
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: AppTheme.primaryGreen))
          : RefreshIndicator(
              onRefresh: _load,
              color: AppTheme.primaryGreen,
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    CropSelectorWidget(
                      crops: _crops,
                      selectedCrop: _selectedCrop,
                      onCropSelected: (crop) {
                        setState(() {
                          _selectedCrop = crop;
                          final cached = _cropDataCache[crop];
                          if (cached != null) {
                            _data = Map<String, dynamic>.from(cached);
                            _lastUpdated = _formatNow();
                            _loading = false;
                            _error = null;
                          } else {
                            _loading = true;
                            _error = null;
                          }
                        });
                        if (_cropDataCache[crop] == null) _load();
                      },
                    ),
                    const SizedBox(height: 12),
                    _buildHeroHeader(crop: _selectedCrop, district: district),
                    const SizedBox(height: 12),
                    if (_error != null) _buildErrorCard(_error!),
                    if (_data != null) ...[
                      _buildHealthGauge(_data!),
                      const SizedBox(height: 12),
                      _buildRiskBreakdown(_data!),
                      const SizedBox(height: 12),
                      _buildProtectionGap(_data!),
                      const SizedBox(height: 12),
                      _buildRecommendations(_data!),
                      const SizedBox(height: 18),
                      if (_lastUpdated != null)
                        Center(
                          child: Text(
                            "Last updated: $_lastUpdated",
                            style: AppTheme.bodyMedium.copyWith(fontSize: 11, color: Colors.grey),
                          ),
                        ),
                    ],
                  ],
                ),
              ),
            ),
    );
  }

  Widget _buildHeroHeader({required String crop, required String district}) {
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
          )
        ],
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.15),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(
            "🛡 Financial Risk & Protection Intelligence",
            style: GoogleFonts.dmSans(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w700),
          ),
        ),
        const SizedBox(height: 10),
        Text(
          "$crop • $district",
          style: GoogleFonts.playfairDisplay(
            color: Colors.white,
            fontSize: 22,
            fontWeight: FontWeight.w800,
            fontStyle: FontStyle.italic,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          "Know your risk exposure and the best protection actions right now.",
          style: GoogleFonts.dmSans(color: Colors.white70, fontSize: 12, height: 1.4),
        ),
      ]),
    );
  }

  Widget _buildErrorCard(String msg) {
    return AppCard(
      color: const Color(0xFFFFEBEE),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Icon(Icons.error_outline, color: AppTheme.error),
        const SizedBox(width: 10),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text("Couldn’t load protection analysis", style: AppTheme.headingMedium.copyWith(fontSize: 13)),
            const SizedBox(height: 4),
            Text(msg, style: AppTheme.bodyMedium.copyWith(fontSize: 11, color: AppTheme.textDark)),
          ]),
        ),
      ]),
    );
  }

  Widget _buildHealthGauge(Map<String, dynamic> data) {
    final score = (data['financial_health_score'] ?? 0).toDouble();
    final level = (data['risk_level'] ?? 'LOW').toString();

    Color c;
    String label;
    if (level == 'HIGH') {
      c = AppTheme.error;
      label = "High Risk";
    } else if (level == 'MODERATE') {
      c = AppTheme.accentOrange;
      label = "Moderate Risk";
    } else {
      c = AppTheme.success;
      label = "Low Risk";
    }

    final progress = (score.clamp(0, 100)) / 100.0;

    return AppCard(
      child: Row(
        children: [
          Expanded(
            child: Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  SizedBox(
                    width: 100, // Reduced from 120
                    height: 100, // Reduced from 120
                    child: Stack(
                      alignment: Alignment.center,
                      children: [
                        CircularProgressIndicator(
                          value: 1,
                          strokeWidth: 10,
                          valueColor: AlwaysStoppedAnimation<Color>(
                              Colors.grey.shade200),
                        ),
                        CircularProgressIndicator(
                          value: progress,
                          strokeWidth: 10,
                          valueColor: AlwaysStoppedAnimation<Color>(c),
                          backgroundColor: Colors.transparent,
                        ),
                        Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(
                              "${score.toStringAsFixed(0)}",
                              style: GoogleFonts.roboto(
                                fontSize: 32, // Reduced from 36
                                fontWeight: FontWeight.w900,
                                color: AppTheme.textDark,
                              ),
                            ),
                            Text(
                              "Health",
                              style: AppTheme.bodyMedium.copyWith(fontSize: 11), // Reduced from 12
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text("Financial Health Score",
                      style: AppTheme.headingMedium.copyWith(fontSize: 15)), // Reduced from 16
                  const SizedBox(height: 6),
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: c.withOpacity(0.08),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: c.withOpacity(0.25)),
                    ),
                    child: Row(mainAxisSize: MainAxisSize.min, children: [
                      Icon(
                          level == 'HIGH'
                              ? Icons.warning_amber
                              : level == 'MODERATE'
                                  ? Icons.info_outline
                                  : Icons.verified,
                          size: 14,
                          color: c),
                      const SizedBox(width: 6),
                      Text(label,
                          style: AppTheme.bodyMedium.copyWith(
                              fontSize: 11,
                              color: c,
                              fontWeight: FontWeight.w700)),
                    ]),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRiskBreakdown(Map<String, dynamic> data) {
    final rb = (data['risk_breakdown'] as Map?)?.cast<String, dynamic>() ?? {};
    final w = (rb['weather_risk_score'] ?? 0).toDouble();
    final m = (rb['market_risk_score'] ?? 0).toDouble();
    final y = (rb['yield_risk_score'] ?? 0).toDouble();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionHeader("Risk Exposure Breakdown"),
        const SizedBox(height: 10),
        Row(
          children: [
            Expanded(child: _riskMiniCard(title: "Weather", score: w, icon: Icons.cloud, color: AppTheme.accentBlue)),
            const SizedBox(width: 8),
            Expanded(child: _riskMiniCard(title: "Market", score: m, icon: Icons.show_chart, color: AppTheme.accentPurple)),
            const SizedBox(width: 8),
            Expanded(child: _riskMiniCard(title: "Yield", score: y, icon: Icons.grass, color: AppTheme.primaryGreen)),
          ],
        ),
      ],
    );
  }

  Widget _riskMiniCard({
    required String title,
    required double score,
    required IconData icon,
    required Color color,
  }) {
    final s = score.clamp(0, 100);
    final severity = s >= 70 ? "HIGH" : (s >= 40 ? "MODERATE" : "LOW");
    final chipColor = severity == "HIGH"
        ? AppTheme.error
        : (severity == "MODERATE" ? AppTheme.accentOrange : AppTheme.success);

    String imageUrl;
    if (title.toLowerCase().contains('weather')) {
      imageUrl =
          'https://images.unsplash.com/photo-1592210454359-9043f067919b?w=400&q=80';
    } else if (title.toLowerCase().contains('market')) {
      imageUrl =
          'https://images.unsplash.com/photo-1542838132-92c53300491e?w=400&q=80';
    } else {
      imageUrl =
          'https://images.unsplash.com/photo-1574943320219-553eb213f72d?w=400&q=80';
    }

    return Container(
      height: 180,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(0, 4),
          )
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: Stack(
        fit: StackFit.expand,
        children: [
          // Background Image
          Image.network(
            imageUrl,
            fit: BoxFit.cover,
            errorBuilder: (_, __, ___) => Container(color: color),
          ),
          // Gradient Overlay
          Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  Colors.black.withOpacity(0.2),
                  Colors.black.withOpacity(0.7),
                ],
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
              ),
            ),
          ),
          // Content
          Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(6),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.2),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Icon(icon, size: 16, color: Colors.white),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: chipColor.withOpacity(0.9),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        severity,
                        style: AppTheme.bodyMedium.copyWith(
                            fontSize: 9,
                            color: Colors.white,
                            fontWeight: FontWeight.w800),
                      ),
                    ),
                  ],
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title,
                        style: AppTheme.bodyMedium.copyWith(
                            fontSize: 12,
                            color: Colors.white,
                            fontWeight: FontWeight.w700)),
                    const SizedBox(height: 4),
                    Text(
                      s.toStringAsFixed(0),
                      style: GoogleFonts.roboto(
                          fontSize: 24,
                          fontWeight: FontWeight.w900,
                          color: Colors.white),
                    ),
                    const SizedBox(height: 4),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(10),
                      child: LinearProgressIndicator(
                        value: s / 100.0,
                        backgroundColor: Colors.white.withOpacity(0.2),
                        valueColor: AlwaysStoppedAnimation<Color>(chipColor),
                        minHeight: 4,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildProtectionGap(Map<String, dynamic> data) {
    final gap = (data['protection_gap'] ?? '').toString();
    final level = (data['risk_level'] ?? 'LOW').toString();

    final c = level == 'HIGH'
        ? AppTheme.error
        : (level == 'MODERATE' ? AppTheme.accentOrange : AppTheme.success);

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: c.withOpacity(0.07),
        borderRadius: BorderRadius.circular(AppTheme.cardRadius),
        border: Border.all(color: c.withOpacity(0.25)),
      ),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Icon(Icons.warning_amber_rounded, color: c, size: 20),
        const SizedBox(width: 10),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text("Protection Gap", style: AppTheme.headingMedium.copyWith(fontSize: 13, color: c)),
            const SizedBox(height: 4),
            Text(gap, style: AppTheme.bodyMedium.copyWith(fontSize: 11, color: AppTheme.textDark)),
          ]),
        ),
      ]),
    );
  }

  Widget _buildRecommendations(Map<String, dynamic> data) {
    final actions = (data['recommended_protection_actions'] as List?) ?? const [];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionHeader("Recommended Protection Actions"),
        const SizedBox(height: 10),
        if (actions.isEmpty)
          AppCard(
            child: Text(
              "No protection actions recommended right now.",
              style: AppTheme.bodyMedium.copyWith(fontSize: 12, color: AppTheme.textDark),
            ),
          )
        else
          ...actions.map((a) => _actionCard((a as Map).cast<String, dynamic>())).toList(),
      ],
    );
  }

  Widget _actionCard(Map<String, dynamic> action) {
    final type = (action['type'] ?? 'Protection').toString();
    final name = (action['scheme_name'] ?? '').toString();
    final urgency = (action['urgency'] ?? 'MEDIUM').toString();
    final reason = (action['reason'] ?? '').toString();
    final link = (action['apply_link'] ?? '').toString();

    final c = urgency == 'HIGH'
        ? AppTheme.error
        : (urgency == 'MEDIUM' ? AppTheme.accentOrange : AppTheme.primaryGreen);

    IconData icon;
    switch (type.toLowerCase()) {
      case 'insurance':
        icon = Icons.shield;
        break;
      case 'income support':
        icon = Icons.payments_outlined;
        break;
      case 'msp procurement':
        icon = Icons.account_balance;
        break;
      default:
        icon = Icons.lightbulb_outline;
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: AppCard(
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: c.withOpacity(0.10),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(icon, color: c, size: 18),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(type, style: AppTheme.bodyMedium.copyWith(fontSize: 10, color: AppTheme.textMuted)),
                  Text(name, style: AppTheme.headingMedium.copyWith(fontSize: 14)),
                ]),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: c.withOpacity(0.10),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: c.withOpacity(0.25)),
                ),
                child: Text(
                  urgency,
                  style: AppTheme.bodyMedium.copyWith(fontSize: 10, color: c, fontWeight: FontWeight.w800),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(reason, style: AppTheme.bodyMedium.copyWith(fontSize: 11, color: AppTheme.textDark)),
          if (link.isNotEmpty) ...[
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () => _openLink(link),
                    icon: const Icon(Icons.open_in_new, size: 16),
                    label: const Text("Apply Now"),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.primaryGreen,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(AppTheme.buttonRadius),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ]),
      ),
    );
  }

  Widget _sectionHeader(String title) {
    return Row(
      children: [
        Text(
          title,
          style: GoogleFonts.playfairDisplay(
            fontSize: 18,
            fontWeight: FontWeight.w700,
            fontStyle: FontStyle.italic,
            color: AppTheme.textDark,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Container(
            height: 1,
            color: AppTheme.accentGold.withOpacity(0.4),
          ),
        ),
      ],
    );
  }

  Future<void> _openLink(String url) async {
    final uri = Uri.tryParse(url);
    if (uri == null) return;
    final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
    if (!ok && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Could not open link"), backgroundColor: AppTheme.error),
      );
    }
  }
}

