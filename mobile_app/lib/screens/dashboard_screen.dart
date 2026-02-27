import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../providers/farmer_profile_provider.dart';
import '../services/api_service.dart';
import '../services/region_crop_strategy.dart';
import '../theme.dart';
import '../widgets/app_card.dart';
import 'mandi_screen.dart';
import 'price_screen.dart';
import 'recommendation_screen.dart';
import 'yield_screen.dart';
import 'profit_calculator_screen.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  Map<String, dynamic>? _weatherData;
  Map<String, dynamic>? _riskData;
  Map<String, dynamic>? _recommendation;
  List<dynamic>? _mandiPrices;
  bool _isLoading = true;
  String? _lastUpdated;

  // Intelligence strategy
  RegionCropStrategy _strategy = RegionCropStrategy.fromLocal(
    state: null, crop: null, storageAvailable: false,
  );
  List<IntelligenceAlert> _alerts = [];
  MspContext? _mspContext;

  @override
  void initState() {
    super.initState();
    _loadDashboard();
  }

  Future<void> _loadDashboard() async {
    setState(() => _isLoading = true);

    try {
      final profile = Provider.of<FarmerProfile>(context, listen: false);
      final api = Provider.of<ApiService>(context, listen: false);
      final activeCrop = profile.activeCrop;
      final crop = activeCrop?.cropName ?? profile.primaryCrop ?? 'Rice';
      final district = profile.district ?? 'Pune';
      final mandi = activeCrop?.preferredMandi ?? profile.nearestMandi ?? '$district Mandi';
      final landSize = activeCrop?.areaHectares ?? profile.landSize ?? 2.0;
      final state = profile.state ?? 'Maharashtra';
      final farmCropId = activeCrop?.id;

      _strategy = RegionCropStrategy.fromLocal(
        state: state, crop: crop, storageAvailable: profile.storageAvailable,
      );
      _alerts = _strategy.alerts;
      _mspContext = _strategy.mspContext;

      bool usedIntelligent = false;
      try {
        final payload = <String, dynamic>{
          'state': state, 'crop': crop, 'district': district,
          'land_size': landSize, 'storage_available': profile.storageAvailable,
          'mandi': mandi,
        };
        // Pass farm_crop_id if available (enables DB-driven crop context)
        if (farmCropId != null && !farmCropId.startsWith('local_')) {
          payload['farm_crop_id'] = farmCropId;
        }
        final resp = await api.postIntelligentDashboard(payload);
        _weatherData = resp['weather'];
        _mandiPrices = resp['mandi_prices'] as List<dynamic>?;
        _riskData = resp['market_risk'];
        _recommendation = resp['recommendation'];
        if (resp['strategy'] != null) {
          _strategy = RegionCropStrategy.fromJson(resp);
          _alerts = _strategy.alerts;
          _mspContext = _strategy.mspContext;
        }
        usedIntelligent = true;
      } catch (_) {}

      if (!usedIntelligent) {
        try { _weatherData = await api.getWeather(district); } catch (_) {
          _weatherData = {'temp': 30, 'humidity': 60, 'rainfall': 0, 'condition': 'Clear'};
        }
        try {
          _mandiPrices = await api.getMandiPrices(crop, district: district);
          if (_mandiPrices != null) profile.cacheData(mandiPrices: json.encode(_mandiPrices));
        } catch (_) { _mandiPrices = profile.cachedMandiPrices; }
        try { _riskData = await api.getMarketRisk(); } catch (_) {}
        try {
          final recPayload = <String, dynamic>{
            'crop': crop, 'district': district, 'land_size': landSize, 'mandi': mandi,
          };
          if (farmCropId != null && !farmCropId.startsWith('local_')) {
            recPayload['farm_crop_id'] = farmCropId;
          }
          _recommendation = await api.getRecommendation(recPayload);
          if (_recommendation != null) profile.cacheData(forecast: json.encode(_recommendation));
        } catch (_) { _recommendation = profile.cachedForecast; }
      }
    } catch (e) {
      debugPrint('Dashboard load error: $e');
    }

    if (mounted) {
      setState(() { _lastUpdated = _formatNow(); _isLoading = false; });
    }
  }

  String _formatNow() {
    final now = DateTime.now();
    return "${now.day}/${now.month}/${now.year} ${now.hour}:${now.minute.toString().padLeft(2, '0')}";
  }

  @override
  Widget build(BuildContext context) {
    final profile = Provider.of<FarmerProfile>(context);
    final activeCrop = profile.activeCrop;
    final crop = activeCrop?.cropName ?? profile.primaryCrop ?? 'Rice';
    final district = profile.district ?? 'Pune';
    final mandi = activeCrop?.preferredMandi ?? profile.nearestMandi ?? '$district Mandi';
    final landSize = activeCrop?.areaHectares ?? profile.landSize ?? 2.0;
    final expectedYield = profile.expectedYield;

    return Scaffold(
      appBar: AppBar(
        title: Row(children: [
          const Icon(Icons.eco, size: 22),
          const SizedBox(width: 8),
          Text.rich(TextSpan(children: [
            TextSpan(text: 'Krishi', style: GoogleFonts.dmSans(color: Colors.white, fontSize: 19, fontWeight: FontWeight.w400)),
            TextSpan(text: 'Mitra', style: GoogleFonts.playfairDisplay(color: AppTheme.accentGold, fontSize: 19, fontWeight: FontWeight.w700, fontStyle: FontStyle.italic)),
          ])),
        ]),
        actions: [
          IconButton(icon: const Icon(Icons.notifications_outlined), onPressed: () {}),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: AppTheme.primaryGreen))
          : RefreshIndicator(
              onRefresh: _loadDashboard,
              color: AppTheme.primaryGreen,
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // ═══ CROP SWITCHER (if multi-crop) ═══
                    if (profile.allFarmCrops.length > 1) ...[
                      _buildCropSwitcher(profile),
                      const SizedBox(height: 12),
                    ],

                    // ═══ 1. HERO: RECOMMENDATION (THE answer) ═══
                    _buildRecommendationHero(crop, landSize, expectedYield),
                    const SizedBox(height: 12),

                    // ═══ 2. GREETING + WEATHER ═══
                    _buildGreetingWeatherCard(profile),
                    const SizedBox(height: 12),

                    // ═══ 3. INTELLIGENCE ALERTS ═══
                    if (_alerts.isNotEmpty) ...[
                      ..._alerts.map(_buildAlertCard),
                      const SizedBox(height: 12),
                    ],

                    // ═══ 4. TODAY'S PRICE + MSP JUDGMENT ═══
                    if (_mandiPrices != null && _mandiPrices!.isNotEmpty)
                      _buildPriceInsightCard(_mandiPrices![0], crop, mandi),
                    const SizedBox(height: 10),

                    // ═══ 5. MSP CARD ═══
                    if (_strategy.showMspCard && _mspContext != null)
                      _buildMspCard(_mspContext!, _mandiPrices),
                    if (_strategy.showMspCard) const SizedBox(height: 12),

                    // ═══ 6. MARKET SITUATION ═══
                    if (_riskData != null)
                      _buildRiskBanner(_riskData!),
                    const SizedBox(height: 16),

                    // ═══ 7. PRICE ALERT BUTTON ═══
                    _buildPriceAlertButton(crop),
                    const SizedBox(height: 16),

                    // ═══ 8. QUICK ACTIONS ═══
                    _buildSectionHeader("Quick Actions"),
                    const SizedBox(height: 10),
                    GridView.count(
                      crossAxisCount: 2, shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      mainAxisSpacing: 8, crossAxisSpacing: 8, childAspectRatio: 1.4,
                      children: _buildStrategyActions(),
                    ),
                    const SizedBox(height: 16),

                    // ═══ 9. PROFIT CALCULATOR ═══
                    AppCard(
                      onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const ProfitCalculatorScreen())),
                      padding: const EdgeInsets.all(14),
                      child: Row(children: [
                        const Icon(Icons.calculate, color: AppTheme.primaryGreen, size: 22),
                        const SizedBox(width: 12),
                        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text("Profit Calculator", style: AppTheme.headingMedium.copyWith(fontSize: 13)),
                          Text("Know your exact earnings after costs", style: AppTheme.bodyMedium.copyWith(fontSize: 11)),
                        ])),
                        const Icon(Icons.chevron_right, color: Colors.grey),
                      ]),
                    ),
                    const SizedBox(height: 20),
                    if (_lastUpdated != null)
                      Center(child: Text("Last updated: $_lastUpdated",
                          style: AppTheme.bodyMedium.copyWith(fontSize: 11, color: Colors.grey))),
                    const SizedBox(height: 8),
                  ],
                ),
              ),
            ),
    );
  }

  // ═══════════════════════════════════════════════════
  // CROP SWITCHER — top dropdown for multi-crop
  // ═══════════════════════════════════════════════════
  Widget _buildCropSwitcher(FarmerProfile profile) {
    final cropIcons = {
      'Rice': '🌾', 'Wheat': '🌿', 'Maize': '🌽', 'Soybean': '🫘',
      'Cotton': '☁️', 'Sugarcane': '🎋', 'Groundnut': '🥜', 'Onion': '🧅',
      'Tomato': '🍅', 'Potato': '🥔',
    };
    final allCrops = profile.allFarmCrops;
    if (allCrops.isEmpty) return const SizedBox.shrink();

    // Guard: ensure activeCropId actually exists in the list
    final allIds = allCrops.map((c) => c.id).toSet();
    String activeCropId = profile.activeCrop?.id ?? '';
    if (!allIds.contains(activeCropId)) {
      // Stale local ID — reset to first crop
      activeCropId = allCrops.first.id;
      Future.microtask(() => profile.setActiveCropById(activeCropId));
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(AppTheme.cardRadius),
        border: Border.all(color: AppTheme.primaryGreen.withOpacity(0.3)),
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.04), blurRadius: 8, offset: const Offset(0, 2))],
      ),
      child: Row(
        children: [
          Text(cropIcons[profile.activeCrop?.cropName] ?? '🌱', style: const TextStyle(fontSize: 20)),
          const SizedBox(width: 10),
          Expanded(
            child: DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                value: activeCropId,
                isExpanded: true,
                icon: const Icon(Icons.keyboard_arrow_down, color: AppTheme.primaryGreen),
                style: AppTheme.headingMedium.copyWith(fontSize: 15, color: AppTheme.textDark),
                items: allCrops.map((fc) => DropdownMenuItem(
                  value: fc.id,
                  child: Row(children: [
                    Text(cropIcons[fc.cropName] ?? '🌱', style: const TextStyle(fontSize: 16)),
                    const SizedBox(width: 8),
                    Expanded(child: Text(fc.cropName)),
                    Text('${fc.areaHectares.toStringAsFixed(1)} ha',
                        style: AppTheme.bodyMedium.copyWith(fontSize: 10, color: AppTheme.textLight)),
                  ]),
                )).toList(),
                onChanged: (cropId) {
                  if (cropId != null) {
                    profile.setActiveCropById(cropId);
                    _loadDashboard();
                  }
                },
              ),
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(color: AppTheme.lightGreen, borderRadius: BorderRadius.circular(4)),
            child: Text("${allCrops.length} crops", style: AppTheme.bodyMedium.copyWith(
                fontSize: 10, color: AppTheme.primaryGreen, fontWeight: FontWeight.w600)),
          ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════
  // RECOMMENDATION HERO — THE answer a farmer wants
  // ═══════════════════════════════════════════════════
  Widget _buildRecommendationHero(String crop, double landSize, double expectedYield) {
    final rec = _recommendation;
    final isSell = rec?['recommendation'] == 'SELL NOW';
    final waitDays = rec?['wait_days'] ?? 10;
    final extraProfit = (rec?['extra_profit'] ?? 0).toDouble();
    final riskLevel = rec?['risk_level'] ?? 'LOW';
    final explanation = rec?['explanation'] ?? '';

    final todayPrice = (_mandiPrices != null && _mandiPrices!.isNotEmpty)
        ? (_mandiPrices![0]['today_price']?.toDouble() ?? 2120.0) : 2120.0;
    final revenueToday = expectedYield * todayPrice;

    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: isSell
              ? [const Color(0xFF2E7D32), const Color(0xFF43A047)]
              : [const Color(0xFFE65100), const Color(0xFFF57C00)],
          begin: Alignment.topLeft, end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(AppTheme.cardRadius),
        boxShadow: [BoxShadow(
          color: (isSell ? AppTheme.primaryGreen : AppTheme.accentOrange).withOpacity(0.25),
          blurRadius: 16, offset: const Offset(0, 4),
        )],
      ),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          // Top label
          Row(children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(color: Colors.white.withOpacity(0.2), borderRadius: BorderRadius.circular(4)),
              child: Text("💡 Recommendation", style: TextStyle(color: Colors.white.withOpacity(0.9), fontSize: 11, fontWeight: FontWeight.w600)),
            ),
            const Spacer(),
            // Risk indicator with confidence
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(color: Colors.white.withOpacity(0.2), borderRadius: BorderRadius.circular(4)),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Text(riskLevel == 'LOW' ? '🟢' : riskLevel == 'MEDIUM' ? '🟡' : '🔴', style: const TextStyle(fontSize: 12)),
                const SizedBox(width: 4),
                Text("Risk: $riskLevel", style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w600)),
              ]),
            ),
          ]),
          const SizedBox(height: 14),

          // THE ANSWER
          Text(
            isSell ? "SELL TODAY" : "WAIT ~$waitDays days",
            style: GoogleFonts.roboto(color: Colors.white, fontSize: 30, fontWeight: FontWeight.w900, letterSpacing: 0.5),
          ),
          const SizedBox(height: 4),

          if (!isSell && extraProfit > 0)
            Text(
              "Expected Extra Profit: ₹${_formatNumber(extraProfit)}",
              style: TextStyle(color: Colors.white.withOpacity(0.95), fontSize: 16, fontWeight: FontWeight.w600),
            ),

          if (isSell)
            Text(
              "Good time to sell. Revenue: ₹${_formatNumber(revenueToday)}",
              style: TextStyle(color: Colors.white.withOpacity(0.95), fontSize: 14, fontWeight: FontWeight.w600),
            ),

          const SizedBox(height: 10),

          // Simple explanation
          if (explanation.isNotEmpty)
            Text(explanation, style: TextStyle(color: Colors.white.withOpacity(0.8), fontSize: 12, height: 1.4)),

          const SizedBox(height: 8),

          // Confidence line
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(color: Colors.white.withOpacity(0.12), borderRadius: BorderRadius.circular(4)),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Icon(Icons.verified, color: Colors.white.withOpacity(0.7), size: 14),
              const SizedBox(width: 6),
              Expanded(
                child: Text("Based on 3-year seasonal data & current market trends",
                    style: TextStyle(color: Colors.white.withOpacity(0.7), fontSize: 10)),
              ),
            ]),
          ),
        ]),
      ),
    );
  }

  // ═══════════════════════════════════════════════════
  // PRICE ALERT BUTTON
  // ═══════════════════════════════════════════════════
  Widget _buildPriceAlertButton(String crop) {
    final currentPrice = (_mandiPrices != null && _mandiPrices!.isNotEmpty)
        ? (_mandiPrices![0]['today_price']?.toDouble() ?? 2100) : 2100.0;
    final suggestedTarget = (currentPrice * 1.05).round(); // 5% above current

    return GestureDetector(
      onTap: () {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text("🔔 We'll alert you when $crop price crosses ₹$suggestedTarget/Q"),
            backgroundColor: AppTheme.primaryGreen,
            behavior: SnackBarBehavior.floating,
            duration: const Duration(seconds: 3),
          ),
        );
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(AppTheme.cardRadius),
          border: Border.all(color: AppTheme.accentBlue.withOpacity(0.3)),
        ),
        child: Row(children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(color: AppTheme.accentBlue.withOpacity(0.1), borderRadius: BorderRadius.circular(8)),
            child: const Icon(Icons.notifications_active, color: AppTheme.accentBlue, size: 20),
          ),
          const SizedBox(width: 12),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text("Set Price Alert", style: AppTheme.headingMedium.copyWith(fontSize: 13)),
            Text("Alert me if $crop > ₹$suggestedTarget/Q", style: AppTheme.bodyMedium.copyWith(fontSize: 11, color: AppTheme.textLight)),
          ])),
          const Icon(Icons.chevron_right, color: AppTheme.accentBlue, size: 20),
        ]),
      ),
    );
  }

  // ═══════════════════════════════════════════════════
  // ALERT CARD
  // ═══════════════════════════════════════════════════
  Widget _buildAlertCard(IntelligenceAlert alert) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: alert.bgColor,
          borderRadius: BorderRadius.circular(AppTheme.cardRadius),
          border: Border.all(color: alert.severityColor.withOpacity(0.3)),
        ),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(alert.icon, style: const TextStyle(fontSize: 20)),
          const SizedBox(width: 10),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(alert.title, style: AppTheme.headingMedium.copyWith(fontSize: 12, color: alert.severityColor)),
            const SizedBox(height: 2),
            Text(alert.message, style: AppTheme.bodyMedium.copyWith(fontSize: 11)),
            if (alert.action != null) ...[
              const SizedBox(height: 4),
              Text("→ ${alert.action!}", style: AppTheme.bodyMedium.copyWith(fontSize: 10, fontWeight: FontWeight.w600, color: alert.severityColor)),
            ],
          ])),
        ]),
      ),
    );
  }

  // ═══════════════════════════════════════════════════
  // MSP CARD
  // ═══════════════════════════════════════════════════
  Widget _buildMspCard(MspContext msp, List<dynamic>? mandiPrices) {
    final currentPrice = (mandiPrices != null && mandiPrices.isNotEmpty)
        ? (mandiPrices[0]['today_price']?.toDouble() ?? 0) : 0.0;
    final aboveMsp = currentPrice - msp.effectiveMsp;
    final isAbove = aboveMsp >= 0;

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: isAbove ? const Color(0xFFE8F5E9) : const Color(0xFFFFEBEE),
        borderRadius: BorderRadius.circular(AppTheme.cardRadius),
        border: Border.all(color: isAbove ? AppTheme.primaryGreen.withOpacity(0.3) : AppTheme.error.withOpacity(0.3)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.account_balance, size: 16, color: AppTheme.accentPurple),
          const SizedBox(width: 6),
          Text("MSP Comparison — ${msp.crop}", style: AppTheme.headingMedium.copyWith(fontSize: 12)),
          const Spacer(),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(
              color: isAbove ? AppTheme.primaryGreen : AppTheme.error,
              borderRadius: BorderRadius.circular(2),
            ),
            child: Text(isAbove ? "ABOVE MSP" : "BELOW MSP",
                style: const TextStyle(color: Colors.white, fontSize: 9, fontWeight: FontWeight.bold)),
          ),
        ]),
        const SizedBox(height: 10),
        Row(children: [
          _mspPill("MSP", "₹${msp.baseMsp.toStringAsFixed(0)}", AppTheme.textDark),
          if (msp.stateBonus > 0) ...[
            const SizedBox(width: 8),
            _mspPill("State Bonus", "+₹${msp.stateBonus.toStringAsFixed(0)}", AppTheme.accentPurple),
          ],
          const SizedBox(width: 8),
          _mspPill("Effective", "₹${msp.effectiveMsp.toStringAsFixed(0)}", AppTheme.primaryGreen),
        ]),
        if (currentPrice > 0) ...[
          const SizedBox(height: 8),
          Text(
            "Market price ₹${currentPrice.toStringAsFixed(0)} is ${isAbove ? '+' : ''}₹${aboveMsp.toStringAsFixed(0)} ${isAbove ? 'above' : 'below'} MSP",
            style: AppTheme.bodyMedium.copyWith(fontSize: 11, color: isAbove ? AppTheme.primaryGreen : AppTheme.error, fontWeight: FontWeight.w600),
          ),
        ],
      ]),
    );
  }

  Widget _mspPill(String label, String value, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(AppTheme.chipRadius), border: Border.all(color: AppTheme.cardBorder)),
      child: Column(children: [
        Text(label, style: AppTheme.bodyMedium.copyWith(fontSize: 9)),
        Text(value, style: TextStyle(color: color, fontSize: 13, fontWeight: FontWeight.bold)),
      ]),
    );
  }

  // ═══════════════════════════════════════════════════
  // GREETING + WEATHER
  // ═══════════════════════════════════════════════════
  // ═══════════════════════════════════════════════════
  // SECTION HEADER — Playfair Display italic + gold divider
  // ═══════════════════════════════════════════════════
  Widget _buildSectionHeader(String title) {
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

  Widget _buildGreetingWeatherCard(FarmerProfile profile) {
    final rec = _recommendation;
    final weatherRisk = rec?['weather_risk'] as Map<String, dynamic>?;
    final rainRisk = weatherRisk?['rain_risk'] ?? 'LOW';
    final heatRisk = weatherRisk?['heat_risk'] ?? 'LOW';
    final humidityRisk = weatherRisk?['humidity_risk'] ?? 'LOW';

    final temp = (_weatherData?['temp'] ?? 30).toDouble();
    final humidity = (_weatherData?['humidity'] ?? 60).toDouble();
    final rainfall = (_weatherData?['rainfall'] ?? 0).toDouble();
    final condition = _weatherData?['condition'] ?? 'Clear';
    IconData weatherIcon = Icons.wb_sunny;
    if (condition.toLowerCase().contains('rain')) weatherIcon = Icons.water_drop;
    else if (condition.toLowerCase().contains('cloud')) weatherIcon = Icons.cloud;
    else if (condition.toLowerCase().contains('haze') || condition.toLowerCase().contains('mist')) weatherIcon = Icons.foggy;

    // Pick a weather-appropriate photo URL
    String weatherPhotoUrl;
    if (condition.toLowerCase().contains('rain')) {
      weatherPhotoUrl = 'https://images.unsplash.com/photo-1534274988757-a28bf1a57c17?w=800&q=80';
    } else if (condition.toLowerCase().contains('cloud')) {
      weatherPhotoUrl = 'https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=800&q=80';
    } else {
      weatherPhotoUrl = 'https://images.unsplash.com/photo-1625246333195-78d9c38ad449?w=800&q=80';
    }

    return SizedBox(
      height: 220,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(AppTheme.cardRadius),
        child: Stack(
          fit: StackFit.expand,
          children: [
            // Photo background with fallback
            Image.network(
              weatherPhotoUrl,
              fit: BoxFit.cover,
              errorBuilder: (_, __, ___) => Container(
                decoration: const BoxDecoration(
                  gradient: LinearGradient(
                    colors: [Color(0xFF1A4731), Color(0xFF2D6A4F)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                ),
              ),
            ),
            // Dark gradient overlay
            Container(
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  colors: [Color(0x10000000), Color(0xCC000000)],
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                ),
              ),
            ),
            // Content
            Padding(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Top row: greeting + location pill
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.2),
                          borderRadius: BorderRadius.circular(AppTheme.chipRadius),
                        ),
                        child: Row(mainAxisSize: MainAxisSize.min, children: [
                          const Icon(Icons.location_on, color: Colors.white, size: 13),
                          const SizedBox(width: 4),
                          Text(profile.district ?? 'Location', style: GoogleFonts.dmSans(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w600)),
                        ]),
                      ),
                      const Spacer(),
                      Text("Namaste, ${profile.displayName} 🙏", style: GoogleFonts.dmSans(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w500)),
                    ],
                  ),
                  const Spacer(),
                  // Big temperature
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text(
                        "${temp.toStringAsFixed(0)}°",
                        style: GoogleFonts.roboto(color: Colors.white, fontSize: 64, fontWeight: FontWeight.w900, height: 1.0),
                      ),
                      const SizedBox(width: 12),
                      Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text(condition, style: GoogleFonts.dmSans(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600)),
                          Text("${profile.displayCrops}", style: GoogleFonts.dmSans(color: Colors.white70, fontSize: 11)),
                        ]),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  // Bottom pills
                  Row(
                    children: [
                      _weatherPill(Icons.water_drop_outlined, "${humidity.toStringAsFixed(0)}%"),
                      const SizedBox(width: 8),
                      _weatherPill(Icons.air, "${rainfall.toStringAsFixed(1)}mm"),
                      if (_strategy.showExtendedWeather && rainfall > 30) ...[
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.all(4),
                          decoration: BoxDecoration(color: Colors.red.withOpacity(0.4), borderRadius: BorderRadius.circular(8)),
                          child: const Icon(Icons.warning_amber, color: Colors.white, size: 14),
                        ),
                      ],
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _weatherPill(IconData icon, String text) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.2),
        borderRadius: BorderRadius.circular(AppTheme.chipRadius),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, color: Colors.white, size: 13),
        const SizedBox(width: 4),
        Text(text, style: GoogleFonts.dmSans(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w600)),
      ]),
    );
  }

  // ═══════════════════════════════════════════════════
  // PRICE INSIGHT with MSP judgment phrase
  // ═══════════════════════════════════════════════════
  Widget _buildPriceInsightCard(Map<String, dynamic> nearest, String crop, String mandi) {
    final todayPrice = nearest['today_price']?.toDouble() ?? 0;
    final yesterdayPrice = nearest['yesterday_price']?.toDouble() ?? 0;
    final change = nearest['price_change']?.toDouble() ?? 0;
    final msp = nearest['msp']?.toDouble() ?? 0;
    final isUp = change >= 0;
    final mspDiff = todayPrice - msp;
    final isAboveMsp = mspDiff >= 0;

    // Simple judgment phrase
    String judgmentText;
    Color judgmentColor;
    if (isAboveMsp && mspDiff > 50) {
      judgmentText = "₹${mspDiff.toStringAsFixed(0)} above MSP. Good selling zone.";
      judgmentColor = AppTheme.primaryGreen;
    } else if (isAboveMsp) {
      judgmentText = "₹${mspDiff.toStringAsFixed(0)} above MSP. Marginal — consider waiting.";
      judgmentColor = AppTheme.accentOrange;
    } else {
      judgmentText = "₹${mspDiff.abs().toStringAsFixed(0)} below MSP. Hold if possible.";
      judgmentColor = AppTheme.error;
    }

    return AppCard(
      onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const PriceScreen())),
      padding: const EdgeInsets.all(14),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.storefront, color: AppTheme.primaryGreen, size: 16),
          const SizedBox(width: 6),
          Text("$crop at ${nearest['mandi'] ?? mandi}", style: AppTheme.bodyMedium.copyWith(fontSize: 11)),
          const Spacer(),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(color: isUp ? AppTheme.primaryGreen : AppTheme.error, borderRadius: BorderRadius.circular(2)),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              Icon(isUp ? Icons.arrow_upward : Icons.arrow_downward, color: Colors.white, size: 10),
              const SizedBox(width: 2),
              Text("₹${change.abs().toStringAsFixed(0)}", style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold)),
            ]),
          ),
        ]),
        const SizedBox(height: 8),
        Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
          Text("₹${todayPrice.toStringAsFixed(0)}", style: GoogleFonts.playfairDisplay(fontSize: 30, fontWeight: FontWeight.w700, color: AppTheme.textDark)),
          const SizedBox(width: 4),
          Padding(padding: const EdgeInsets.only(bottom: 6), child: Text("/Quintal", style: GoogleFonts.dmSans(fontSize: 10, color: AppTheme.textMuted))),
          const Spacer(),
          Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
            Text("Yesterday: ₹${yesterdayPrice.toStringAsFixed(0)}", style: AppTheme.bodyMedium.copyWith(fontSize: 10)),
            Text("MSP: ₹${msp.toStringAsFixed(0)} (${isAboveMsp ? '+' : ''}₹${mspDiff.toStringAsFixed(0)})",
                style: AppTheme.bodyMedium.copyWith(fontSize: 10, color: isAboveMsp ? AppTheme.primaryGreen : AppTheme.error)),
          ]),
        ]),
        // Judgment phrase
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: BoxDecoration(
            color: judgmentColor.withOpacity(0.08),
            borderRadius: BorderRadius.circular(4),
          ),
          child: Row(children: [
            Icon(isAboveMsp && mspDiff > 50 ? Icons.thumb_up : Icons.info_outline,
                color: judgmentColor, size: 14),
            const SizedBox(width: 6),
            Expanded(child: Text(judgmentText,
                style: AppTheme.bodyMedium.copyWith(fontSize: 11, color: judgmentColor, fontWeight: FontWeight.w600))),
          ]),
        ),
      ]),
    );
  }

  // ═══════════════════════════════════════════════════
  // MARKET RISK (simplified language)
  // ═══════════════════════════════════════════════════
  Widget _buildRiskBanner(Map<String, dynamic> risk) {
    final level = risk['level'] ?? 'LOW';
    Color borderColor; Color iconColor; IconData icon;
    switch (level) {
      case 'HIGH': borderColor = AppTheme.error; iconColor = AppTheme.error; icon = Icons.warning_amber_rounded; break;
      case 'MEDIUM': borderColor = AppTheme.accentOrange; iconColor = AppTheme.accentOrange; icon = Icons.info_outline; break;
      default: borderColor = AppTheme.primaryGreen; iconColor = AppTheme.primaryGreen; icon = Icons.check_circle_outline;
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(AppTheme.cardRadius), border: Border.all(color: borderColor)),
      child: Row(children: [
        Icon(icon, color: iconColor, size: 20),
        const SizedBox(width: 10),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text("Market Situation Today", style: AppTheme.bodyMedium.copyWith(fontWeight: FontWeight.bold, color: iconColor, fontSize: 12)),
          Text(risk['message'] ?? '', style: AppTheme.bodyMedium.copyWith(fontSize: 11, color: AppTheme.textDark)),
        ])),
      ]),
    );
  }

  // ═══════════════════════════════════════════════════
  // STRATEGY-ORDERED QUICK ACTIONS
  // ═══════════════════════════════════════════════════
  List<Widget> _buildStrategyActions() {
    final actions = <Widget>[];
    final added = <String>{};

    void addAction(String id, String title, String sub, IconData icon, Color c, Widget screen) {
      if (added.contains(id)) return;
      added.add(id);
      actions.add(_buildActionCard(title, sub, icon, c, () => Navigator.push(context, MaterialPageRoute(builder: (_) => screen))));
    }

    for (final card in _strategy.cardPriority) {
      if (card.contains('price') || card == 'daily_price') {
        addAction('price', "Price Forecast", "Short & long term", Icons.show_chart, AppTheme.accentBlue, const PriceScreen());
      } else if (card.contains('mandi') || card == 'mandi_compare') {
        addAction('mandi', "Mandi Prices", "Compare nearby", Icons.storefront, AppTheme.accentPurple, const MandiScreen());
      } else if (card.contains('sell') || card == 'sell_hold' || card == 'sell_window') {
        addAction('rec', "Sell/Hold Advice", "When to sell", Icons.lightbulb_outline, AppTheme.accentOrange, const RecommendationScreen());
      }
    }

    addAction('yield', "Yield Estimate", "Predict harvest", Icons.grass, AppTheme.primaryGreen, const YieldScreen());
    addAction('price', "Price Forecast", "Short & long term", Icons.show_chart, AppTheme.accentBlue, const PriceScreen());
    addAction('rec', "Sell/Hold Advice", "When to sell", Icons.lightbulb_outline, AppTheme.accentOrange, const RecommendationScreen());
    addAction('mandi', "Mandi Prices", "Compare nearby", Icons.storefront, AppTheme.accentPurple, const MandiScreen());

    return actions.take(4).toList();
  }

  // Photo URLs for quick action cards
  static const _actionPhotos = {
    'Price Forecast': 'asset:assets/images/price_forecast.png',
    'Yield Estimate': 'https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?w=400&q=80',
    'Sell/Hold Advice': 'https://images.unsplash.com/photo-1595508064774-5ff825a07340?w=400&q=80',
    'Mandi Prices': 'https://images.unsplash.com/photo-1488459716781-31db52582fe9?w=400&q=80',
  };

  Widget _buildActionCard(String title, String subtitle, IconData icon, Color color, VoidCallback onTap) {
    final photoUrl = _actionPhotos[title];
    return ClipRRect(
      borderRadius: BorderRadius.circular(AppTheme.cardRadius),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(AppTheme.cardRadius),
          child: Stack(
            fit: StackFit.expand,
            children: [
              // Photo background or color fallback
              if (photoUrl != null && photoUrl.startsWith('asset:'))
                Image.asset(
                  photoUrl.substring(6),
                  fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) => Container(color: color.withOpacity(0.15)),
                )
              else if (photoUrl != null)
                Image.network(
                  photoUrl,
                  fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) => Container(color: color.withOpacity(0.15)),
                )
              else
                Container(color: color.withOpacity(0.15)),
              // Gradient overlay
              Container(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [color.withOpacity(0.0), color.withOpacity(0.85)],
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
                  children: [
                    Container(
                      padding: const EdgeInsets.all(6),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.25),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Icon(icon, color: Colors.white, size: 18),
                    ),
                    const Spacer(),
                    Text(title, style: GoogleFonts.dmSans(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w700)),
                    const SizedBox(height: 2),
                    Text(subtitle, style: GoogleFonts.dmSans(color: Colors.white70, fontSize: 10)),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _formatNumber(double n) {
    if (n >= 100000) return "${(n / 100000).toStringAsFixed(1)}L";
    if (n >= 1000) return "${(n / 1000).toStringAsFixed(1)}K";
    return n.toStringAsFixed(0);
  }
}
