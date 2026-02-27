import 'dart:convert';
import 'package:flutter/material.dart';
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

  // Crop switcher
  String _activeCrop = 'Rice';

  @override
  void initState() {
    super.initState();
    final profile = Provider.of<FarmerProfile>(context, listen: false);
    _activeCrop = profile.primaryCrop ?? 'Rice';
    _loadDashboard();
  }

  Future<void> _loadDashboard() async {
    setState(() => _isLoading = true);

    try {
      final profile = Provider.of<FarmerProfile>(context, listen: false);
      final api = Provider.of<ApiService>(context, listen: false);
      final crop = _activeCrop;
      final district = profile.district ?? 'Pune';
      final mandi = profile.nearestMandi ?? '$district Mandi';
      final landSize = profile.landSize ?? 2.0;
      final state = profile.state ?? 'Maharashtra';

      _strategy = RegionCropStrategy.fromLocal(
        state: state, crop: crop, storageAvailable: profile.storageAvailable,
      );
      _alerts = _strategy.alerts;
      _mspContext = _strategy.mspContext;

      bool usedIntelligent = false;
      try {
        final resp = await api.postIntelligentDashboard({
          'state': state, 'crop': crop, 'district': district,
          'land_size': landSize, 'storage_available': profile.storageAvailable,
          'mandi': mandi,
        });
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
          _recommendation = await api.getRecommendation({
            'crop': crop, 'district': district, 'land_size': landSize, 'mandi': mandi,
          });
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
    final crop = _activeCrop;
    final district = profile.district ?? 'Pune';
    final mandi = profile.nearestMandi ?? '$district Mandi';
    final landSize = profile.landSize ?? 2.0;
    final expectedYield = profile.expectedYield;

    return Scaffold(
      appBar: AppBar(
        title: Row(children: [
          const Icon(Icons.eco, size: 22),
          const SizedBox(width: 8),
          Text("KrishiMitra", style: AppTheme.headingMedium.copyWith(color: Colors.white, fontSize: 18)),
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
                    if (profile.crops.length > 1) ...[
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
                    Text("Quick Actions", style: AppTheme.headingMedium.copyWith(fontSize: 16)),
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
          Text(cropIcons[_activeCrop] ?? '🌱', style: const TextStyle(fontSize: 20)),
          const SizedBox(width: 10),
          Expanded(
            child: DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                value: _activeCrop,
                isExpanded: true,
                icon: const Icon(Icons.keyboard_arrow_down, color: AppTheme.primaryGreen),
                style: AppTheme.headingMedium.copyWith(fontSize: 15, color: AppTheme.textDark),
                items: profile.crops.map((c) => DropdownMenuItem(
                  value: c,
                  child: Row(children: [
                    Text(cropIcons[c] ?? '🌱', style: const TextStyle(fontSize: 16)),
                    const SizedBox(width: 8),
                    Text(c),
                  ]),
                )).toList(),
                onChanged: (v) {
                  if (v != null) {
                    setState(() => _activeCrop = v);
                    _loadDashboard();
                  }
                },
              ),
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(color: AppTheme.lightGreen, borderRadius: BorderRadius.circular(4)),
            child: Text("${profile.crops.length} crops", style: AppTheme.bodyMedium.copyWith(
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
            style: const TextStyle(color: Colors.white, fontSize: 28, fontWeight: FontWeight.w800, letterSpacing: 0.5),
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
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              Icon(Icons.verified, color: Colors.white.withOpacity(0.7), size: 14),
              const SizedBox(width: 6),
              Text("Based on 3-year seasonal data & current market trends",
                  style: TextStyle(color: Colors.white.withOpacity(0.7), fontSize: 10)),
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
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(4), border: Border.all(color: Colors.grey.shade200)),
      child: Column(children: [
        Text(label, style: AppTheme.bodyMedium.copyWith(fontSize: 9)),
        Text(value, style: TextStyle(color: color, fontSize: 13, fontWeight: FontWeight.bold)),
      ]),
    );
  }

  // ═══════════════════════════════════════════════════
  // GREETING + WEATHER
  // ═══════════════════════════════════════════════════
  Widget _buildGreetingWeatherCard(FarmerProfile profile) {
    final temp = (_weatherData?['temp'] ?? 30).toDouble();
    final humidity = (_weatherData?['humidity'] ?? 60).toDouble();
    final rainfall = (_weatherData?['rainfall'] ?? 0).toDouble();
    final condition = _weatherData?['condition'] ?? 'Clear';
    IconData weatherIcon = Icons.wb_sunny;
    if (condition.toLowerCase().contains('rain')) weatherIcon = Icons.water_drop;
    else if (condition.toLowerCase().contains('cloud')) weatherIcon = Icons.cloud;
    else if (condition.toLowerCase().contains('haze') || condition.toLowerCase().contains('mist')) weatherIcon = Icons.foggy;

    return Container(
      decoration: BoxDecoration(color: AppTheme.primaryGreen, borderRadius: BorderRadius.circular(AppTheme.cardRadius)),
      child: Column(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 12),
          child: Row(children: [
            Container(
              width: 44, height: 44,
              decoration: BoxDecoration(color: Colors.white.withOpacity(0.2), borderRadius: BorderRadius.circular(AppTheme.cardRadius)),
              child: const Icon(Icons.person, color: Colors.white, size: 24),
            ),
            const SizedBox(width: 12),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text("Namaste, ${profile.displayName} 🙏", style: AppTheme.headingMedium.copyWith(color: Colors.white, fontSize: 18)),
              Text("${profile.displayCrops} · ${profile.district ?? 'Location'}", style: AppTheme.bodyMedium.copyWith(color: Colors.white70, fontSize: 12)),
            ])),
          ]),
        ),
        Container(
          margin: const EdgeInsets.fromLTRB(8, 0, 8, 8),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(color: Colors.white.withOpacity(0.15), borderRadius: BorderRadius.circular(AppTheme.cardRadius)),
          child: Row(children: [
            Icon(weatherIcon, color: Colors.white, size: 32),
            const SizedBox(width: 10),
            Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text("${temp.toStringAsFixed(0)}°C", style: AppTheme.headingLarge.copyWith(color: Colors.white, fontSize: 22)),
              Text(condition, style: AppTheme.bodyMedium.copyWith(color: Colors.white70, fontSize: 11)),
            ]),
            const Spacer(),
            Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
              Row(mainAxisSize: MainAxisSize.min, children: [
                Icon(Icons.water_drop_outlined, color: Colors.white.withOpacity(0.7), size: 14),
                const SizedBox(width: 4),
                Text("${humidity.toStringAsFixed(0)}%", style: AppTheme.bodyMedium.copyWith(color: Colors.white.withOpacity(0.8), fontSize: 11)),
              ]),
              const SizedBox(height: 4),
              Row(mainAxisSize: MainAxisSize.min, children: [
                Icon(Icons.umbrella_outlined, color: Colors.white.withOpacity(0.7), size: 14),
                const SizedBox(width: 4),
                Text("${rainfall.toStringAsFixed(1)}mm", style: AppTheme.bodyMedium.copyWith(color: Colors.white.withOpacity(0.8), fontSize: 11)),
              ]),
            ]),
            if (_strategy.showExtendedWeather && rainfall > 30) ...[
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.all(4),
                decoration: BoxDecoration(color: Colors.red.withOpacity(0.3), borderRadius: BorderRadius.circular(4)),
                child: const Icon(Icons.warning_amber, color: Colors.white, size: 16),
              ),
            ],
          ]),
        ),
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
          Text("₹${todayPrice.toStringAsFixed(0)}", style: AppTheme.headingLarge.copyWith(fontSize: 28)),
          const SizedBox(width: 4),
          Padding(padding: const EdgeInsets.only(bottom: 4), child: Text("/Quintal", style: AppTheme.bodyMedium.copyWith(fontSize: 10))),
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

  Widget _buildActionCard(String title, String subtitle, IconData icon, Color color, VoidCallback onTap) {
    return Container(
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(AppTheme.cardRadius), border: Border.all(color: Colors.grey.shade200)),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap, borderRadius: BorderRadius.circular(AppTheme.cardRadius),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
              Container(padding: const EdgeInsets.all(6), decoration: BoxDecoration(color: color.withOpacity(0.1), borderRadius: BorderRadius.circular(2)),
                child: Icon(icon, color: color, size: 20)),
              const Spacer(),
              Text(title, style: AppTheme.headingMedium.copyWith(fontSize: 13)),
              const SizedBox(height: 1),
              Text(subtitle, style: AppTheme.bodyMedium.copyWith(fontSize: 10)),
            ]),
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
