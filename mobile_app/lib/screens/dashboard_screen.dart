import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../providers/farmer_profile_provider.dart';
import '../providers/localization_provider.dart';
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
  static const Map<String, String> _cropIcons = {
    'Rice': '🌾',
    'Wheat': '🌿',
    'Maize': '🌽',
    'Soybean': '🫘',
    'Cotton': '☁️',
    'Sugarcane': '🎋',
    'Groundnut': '🥜',
    'Onion': '🧅',
    'Tomato': '🍅',
    'Potato': '🥔',
  };

  Map<String, dynamic>? _weatherData;
  Map<String, dynamic>? _riskData;
  Map<String, dynamic>? _recommendation;
  Map<String, dynamic>? _karnatakaForecast;
  List<dynamic>? _mandiPrices;
  bool _isLoading = true;
  String? _lastUpdated;

  // Intelligence strategy
  RegionCropStrategy _strategy = RegionCropStrategy.fromLocal(
    state: null,
    crop: null,
    storageAvailable: false,
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
      final mandi = activeCrop?.preferredMandi ??
          profile.nearestMandi ??
          '$district Mandi';
      final landSize = activeCrop?.areaHectares ?? profile.landSize ?? 2.0;
      final state = profile.state ?? 'Maharashtra';
      final farmCropId = activeCrop?.id;

      _strategy = RegionCropStrategy.fromLocal(
        state: state,
        crop: crop,
        storageAvailable: profile.storageAvailable,
      );
      _alerts = _strategy.alerts;
      _mspContext = _strategy.mspContext;

      bool usedIntelligent = false;
      try {
        final payload = <String, dynamic>{
          'state': state,
          'crop': crop,
          'district': district,
          'land_size': landSize,
          'storage_available': profile.storageAvailable,
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
        _karnatakaForecast = resp['karnataka_forecast'];

        if (resp['strategy'] != null) {
          _strategy = RegionCropStrategy.fromJson(resp);
          _alerts = _strategy.alerts;
          _mspContext = _strategy.mspContext;
        }

        if (_karnatakaForecast != null) {
          final today = _karnatakaForecast!['today'];
          final bestDay = _karnatakaForecast!['best_day'];
          bool isSell = today['decision'] == 'SELL';
          _recommendation = {
            'recommendation': isSell ? 'SELL NOW' : 'HOLD INVENTORY',
            'explanation':
                'Based on highly-trained local models. Expected optimal sale day: ${bestDay["day"]} at ₹${bestDay["price"]}. ${today["msp_note"]}',
            'risk_level': today['above_msp'] ? 'LOW' : 'HIGH',
            'revenue_today': today['revenue'],
            'severity_color': isSell ? 'green' : 'orange',
          };
          // Clear general alerts so we just show the Karnataka insight directly
          _alerts.clear();
        }

        usedIntelligent = true;
      } catch (_) {}

      if (!usedIntelligent) {
        try {
          _weatherData = await api.getWeather(district);
        } catch (_) {
          _weatherData = {
            'temp': 30,
            'humidity': 60,
            'rainfall': 0,
            'condition': 'Clear'
          };
        }
        try {
          _mandiPrices = await api.getMandiPrices(crop, district: district);
          if (_mandiPrices != null)
            profile.cacheData(mandiPrices: json.encode(_mandiPrices));
        } catch (_) {
          _mandiPrices = profile.cachedMandiPrices;
        }
        try {
          _riskData = await api.getMarketRisk();
        } catch (_) {}
        try {
          final recPayload = <String, dynamic>{
            'crop': crop,
            'district': district,
            'land_size': landSize,
            'mandi': mandi,
          };
          if (farmCropId != null && !farmCropId.startsWith('local_')) {
            recPayload['farm_crop_id'] = farmCropId;
          }
          _recommendation = await api.getRecommendation(recPayload);
          if (_recommendation != null)
            profile.cacheData(forecast: json.encode(_recommendation));
        } catch (_) {
          _recommendation = profile.cachedForecast;
        }
      }
    } catch (e) {
      debugPrint('Dashboard load error: $e');
    }

    if (mounted) {
      setState(() {
        _lastUpdated = _formatNow();
        _isLoading = false;
      });
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
    final mandi =
        activeCrop?.preferredMandi ?? profile.nearestMandi ?? '$district Mandi';
    final landSize = activeCrop?.areaHectares ?? profile.landSize ?? 2.0;
    final expectedYield = profile.expectedYield;

    return Scaffold(
      backgroundColor:
          const Color(0xFFF9F9F9), // Light grayish background matching mockup
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(color: AppTheme.primaryGreen))
          : RefreshIndicator(
              onRefresh: _loadDashboard,
              color: AppTheme.primaryGreen,
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // ═══ 1. GREETING + WEATHER (NEW HEADER) ═══
                    _buildGreetingWeatherHeader(context, profile),
                    // Remove top gap and apply negative margin via Transform to overlap image
                    Transform.translate(
                      offset: const Offset(0, -60),
                      child: _buildRecommendationHero(
                          crop, landSize, expectedYield),
                    ),
                    const SizedBox(height: 8),

                    // ═══ 3. QUICK ACTIONS (2x2 GRID) ═══
                    _buildQuickActionsGrid(),

                    const SizedBox(
                        height:
                            100), // Bottom padding to ensure user can scroll above navigation bar
                  ],
                ),
              ),
            ),
    );
  }

  // ═══════════════════════════════════════════════════
  // RECOMMENDATION HERO — Overlaps the header image
  // ═══════════════════════════════════════════════════
  Widget _buildRecommendationHero(
      String crop, double landSize, double expectedYield) {
    final loc = Provider.of<LocalizationProvider>(context);
    final rec = _recommendation;
    final isSell = rec?['recommendation'] == 'SELL NOW';
    final riskLevel = rec?['risk_level'] ?? 'LOW';
    final explanation = rec?['explanation'] ?? '';
    final severityColor = rec?['severity_color'];
    final karnatakaRev = rec?['revenue_today'];

    final revenueToday = karnatakaRev != null
        ? (karnatakaRev as int).toDouble()
        : (expectedYield * 2120.0);

    final bgColor = severityColor == 'orange'
        ? const Color(0xFFE65100)
        : severityColor == 'red'
            ? const Color(0xFFD32F2F)
            : isSell
                ? const Color(0xFF2E7D32)
                : const Color(0xFFE65100);

    return Container(
      margin: EdgeInsets.zero,
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(28),
        boxShadow: [
          BoxShadow(
            color: bgColor.withOpacity(0.4),
            blurRadius: 24,
            offset: const Offset(0, 8),
          )
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(24, 28, 24, 28),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Simplified Status Line
            Row(
              children: [
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Row(
                    children: [
                      Icon(
                          isSell
                              ? Icons.check_circle
                              : Icons.pause_circle_filled,
                          color: Colors.white,
                          size: 14),
                      const SizedBox(width: 6),
                      Text(
                        isSell ? "Ready to Sell" : "Wait Support",
                        style: GoogleFonts.dmSans(
                          color: Colors.white,
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                ),
                const Spacer(),
                Text(
                  "Risk: ${riskLevel}",
                  style: GoogleFonts.dmSans(
                    color: Colors.white70,
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),

            // Big Visual Instruction - EMOJI DRIVEN
            Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: const BoxDecoration(
                    color: Colors.white24,
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    isSell ? Icons.shopping_cart_checkout : Icons.inventory_2,
                    color: Colors.white,
                    size: 40,
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        isSell ? "SELL $crop" : "STORE $crop",
                        style: GoogleFonts.dmSans(
                          color: Colors.white,
                          fontSize: 36,
                          fontWeight: FontWeight.w900,
                          height: 1.0,
                        ),
                      ),
                      Text(
                        isSell ? "Best Profit Today" : "Prices will go up soon",
                        style: GoogleFonts.dmSans(
                          color: Colors.white.withOpacity(0.8),
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),

            // The 'Farmer's Money' Summary Box
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.1),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.white24),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text("Estimated Income",
                          style: GoogleFonts.dmSans(
                              color: Colors.white70, fontSize: 12)),
                      Text("₹${_formatNumber(revenueToday)}",
                          style: GoogleFonts.dmSans(
                              color: Colors.white,
                              fontSize: 28,
                              fontWeight: FontWeight.w800)),
                    ],
                  ),
                  const Icon(Icons.arrow_forward_ios,
                      color: Colors.white38, size: 16),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Simple Why-To-Do logic
            Text(
              isSell
                  ? "Market price is high right now. Selling now gives you more cash than waiting."
                  : "Prices are rising. If you wait a few more days, you will earn more money.",
              style: GoogleFonts.dmSans(
                color: Colors.white.withOpacity(0.9),
                fontSize: 14,
                height: 1.4,
              ),
            ),

            const SizedBox(height: 20),
            // Footer Trust Badge - Tiny
            Row(
              children: [
                const Icon(Icons.security, color: Colors.white54, size: 12),
                const SizedBox(width: 6),
                Text(
                  "KrishiMitra AI Protected Advice",
                  style:
                      GoogleFonts.dmSans(color: Colors.white54, fontSize: 10),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMiniPill(IconData icon, String text) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.5),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white.withOpacity(0.8)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: AppTheme.textLight),
          const SizedBox(width: 4),
          Text(
            text,
            style: GoogleFonts.dmSans(
              color: AppTheme.textDark,
              fontSize: 10,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════
  // PRICE ALERT BUTTON
  // ═══════════════════════════════════════════════════
  Widget _buildPriceAlertButton(String crop) {
    final currentPrice = (_mandiPrices != null && _mandiPrices!.isNotEmpty)
        ? (_mandiPrices![0]['today_price']?.toDouble() ?? 2100)
        : 2100.0;
    final suggestedTarget = (currentPrice * 1.05).round(); // 5% above current

    return GestureDetector(
      onTap: () {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
                "🔔 We'll alert you when $crop price crosses ₹$suggestedTarget/Q"),
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
            decoration: BoxDecoration(
                color: AppTheme.accentBlue.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8)),
            child: const Icon(Icons.notifications_active,
                color: AppTheme.accentBlue, size: 20),
          ),
          const SizedBox(width: 12),
          Expanded(
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                Text("Set Price Alert",
                    style: AppTheme.headingMedium.copyWith(fontSize: 13)),
                Text("Alert me if $crop > ₹$suggestedTarget/Q",
                    style: AppTheme.bodyMedium
                        .copyWith(fontSize: 11, color: AppTheme.textLight)),
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
          Expanded(
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                Text(alert.title,
                    style: AppTheme.headingMedium
                        .copyWith(fontSize: 12, color: alert.severityColor)),
                const SizedBox(height: 2),
                Text(alert.message,
                    style: AppTheme.bodyMedium.copyWith(fontSize: 11)),
                if (alert.action != null) ...[
                  const SizedBox(height: 4),
                  Text("→ ${alert.action!}",
                      style: AppTheme.bodyMedium.copyWith(
                          fontSize: 10,
                          fontWeight: FontWeight.w600,
                          color: alert.severityColor)),
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
        ? (mandiPrices[0]['today_price']?.toDouble() ?? 0)
        : 0.0;
    final aboveMsp = currentPrice - msp.effectiveMsp;
    final isAbove = aboveMsp >= 0;

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: isAbove ? const Color(0xFFE8F5E9) : const Color(0xFFFFEBEE),
        borderRadius: BorderRadius.circular(AppTheme.cardRadius),
        border: Border.all(
            color: isAbove
                ? AppTheme.primaryGreen.withOpacity(0.3)
                : AppTheme.error.withOpacity(0.3)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.account_balance,
              size: 16, color: AppTheme.accentPurple),
          const SizedBox(width: 6),
          Expanded(
              child: Text("MSP Comparison — ${msp.crop}",
                  style: AppTheme.headingMedium.copyWith(fontSize: 12),
                  overflow: TextOverflow.ellipsis)),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(
              color: isAbove ? AppTheme.primaryGreen : AppTheme.error,
              borderRadius: BorderRadius.circular(2),
            ),
            child: Text(isAbove ? "ABOVE MSP" : "BELOW MSP",
                style: const TextStyle(
                    color: Colors.white,
                    fontSize: 9,
                    fontWeight: FontWeight.bold)),
          ),
        ]),
        const SizedBox(height: 10),
        Wrap(spacing: 8, runSpacing: 8, children: [
          _mspPill(
              "MSP", "₹${msp.baseMsp.toStringAsFixed(0)}", AppTheme.textDark),
          if (msp.stateBonus > 0)
            _mspPill("State Bonus", "+₹${msp.stateBonus.toStringAsFixed(0)}",
                AppTheme.accentPurple),
          _mspPill("Effective", "₹${msp.effectiveMsp.toStringAsFixed(0)}",
              AppTheme.primaryGreen),
        ]),
        if (currentPrice > 0) ...[
          const SizedBox(height: 8),
          Text(
            "Market price ₹${currentPrice.toStringAsFixed(0)} is ${isAbove ? '+' : ''}₹${aboveMsp.toStringAsFixed(0)} ${isAbove ? 'above' : 'below'} MSP",
            style: AppTheme.bodyMedium.copyWith(
                fontSize: 11,
                color: isAbove ? AppTheme.primaryGreen : AppTheme.error,
                fontWeight: FontWeight.w600),
          ),
        ],
      ]),
    );
  }

  Widget _mspPill(String label, String value, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(AppTheme.chipRadius),
          border: Border.all(color: AppTheme.cardBorder)),
      child: Column(children: [
        Text(label, style: AppTheme.bodyMedium.copyWith(fontSize: 9)),
        Text(value,
            style: TextStyle(
                color: color, fontSize: 13, fontWeight: FontWeight.bold)),
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

  Widget _buildGreetingWeatherHeader(
      BuildContext context, FarmerProfile profile) {
    final rec = _recommendation;
    final temp = (_weatherData?['temp'] ?? 30).toDouble();
    final humidity = (_weatherData?['humidity'] ?? 60).toDouble();
    final rainfall = (_weatherData?['rainfall'] ?? 0).toDouble();
    final condition = _weatherData?['condition'] ?? 'Clear';

    // Pick a weather-appropriate photo URL
    String weatherPhotoUrl;
    if (condition.toLowerCase().contains('rain')) {
      weatherPhotoUrl =
          'https://images.unsplash.com/photo-1534274988757-a28bf1a57c17?w=800&q=80';
    } else if (condition.toLowerCase().contains('cloud')) {
      weatherPhotoUrl =
          'https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=800&q=80';
    } else {
      weatherPhotoUrl =
          'https://images.unsplash.com/photo-1625246333195-78d9c38ad449?w=800&q=80';
    }

    final screenHeight = MediaQuery.of(context).size.height;

    return Container(
      width: double.infinity,
      height:
          screenHeight * 0.52, // Larger image spanning roughly half the screen
      decoration: const BoxDecoration(
        borderRadius: BorderRadius.zero,
      ),
      clipBehavior: Clip.antiAlias,
      child: Stack(
        children: [
          // 1. Photo Background
          Positioned.fill(
            child: Image.network(
              weatherPhotoUrl,
              fit: BoxFit.cover,
              errorBuilder: (_, __, ___) => Container(
                decoration: const BoxDecoration(
                  gradient: LinearGradient(
                    colors: [Color(0xFF1B4332), Color(0xFF2D6A4F)],
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                  ),
                ),
              ),
            ),
          ),

          // 2. Gradient Overlay
          Positioned.fill(
            child: Container(
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  colors: [Colors.black54, Colors.black12, Colors.black87],
                  stops: [0.0, 0.4, 1.0],
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                ),
              ),
            ),
          ),

          // 3. Content
          SafeArea(
            bottom: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20,
                  120), // Increased pad bottom to avoid Quick Actions blocking pills
              child: Column(
                mainAxisAlignment:
                    MainAxisAlignment.spaceBetween, // Anchor top & bottom
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Top Row: Location Config & Profile Pic
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 14, vertical: 10),
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.25),
                          borderRadius: BorderRadius.circular(24),
                        ),
                        child: Row(
                          children: [
                            const Icon(Icons.location_on,
                                color: Colors.white, size: 16),
                            const SizedBox(width: 8),
                            Text(
                              "${profile.district ?? 'Location'}, ${profile.state ?? 'India'}",
                              style: GoogleFonts.dmSans(
                                  color: Colors.white,
                                  fontSize: 13,
                                  fontWeight: FontWeight.w500),
                            ),
                          ],
                        ),
                      ),
                      Row(
                        children: [
                          // Language Switcher
                          Consumer<LocalizationProvider>(
                              builder: (context, loc, _) {
                            return PopupMenuButton<String>(
                              offset: const Offset(0, 48),
                              onSelected: (langCode) {
                                loc.setLanguage(langCode);
                              },
                              itemBuilder: (context) => [
                                const PopupMenuItem(
                                    value: 'en', child: Text("English")),
                                const PopupMenuItem(
                                    value: 'hi', child: Text("हिंदी")),
                                const PopupMenuItem(
                                    value: 'mr', child: Text("मराठी")),
                                const PopupMenuItem(
                                    value: 'kn', child: Text("ಕನ್ನಡ")),
                              ],
                              child: Container(
                                margin: const EdgeInsets.only(right: 8),
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 12, vertical: 6),
                                decoration: BoxDecoration(
                                  color: Colors.white.withOpacity(0.25),
                                  borderRadius: BorderRadius.circular(16),
                                ),
                                child: Row(
                                  children: [
                                    const Icon(Icons.language,
                                        color: Colors.white, size: 16),
                                    const SizedBox(width: 4),
                                    Text(
                                      loc.currentLanguage.toUpperCase(),
                                      style: GoogleFonts.dmSans(
                                          color: Colors.white,
                                          fontWeight: FontWeight.bold,
                                          fontSize: 12),
                                    )
                                  ],
                                ),
                              ),
                            );
                          }),
                          // Crop Switcher Dropdown (Replaces old Profile Pic)
                          if (profile.allFarmCrops.length > 1)
                            Theme(
                              data: Theme.of(context).copyWith(
                                popupMenuTheme: PopupMenuThemeData(
                                  shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(16)),
                                ),
                              ),
                              child: PopupMenuButton<String>(
                                offset: const Offset(0, 48),
                                onSelected: (cropId) {
                                  profile.setActiveCropById(cropId);
                                  _loadDashboard();
                                },
                                itemBuilder: (context) =>
                                    profile.allFarmCrops.map((fc) {
                                  return PopupMenuItem(
                                    value: fc.id,
                                    child: Row(
                                      children: [
                                        Text(_cropIcons[fc.cropName] ?? '🌱',
                                            style:
                                                const TextStyle(fontSize: 18)),
                                        const SizedBox(width: 12),
                                        Text(fc.cropName,
                                            style: GoogleFonts.dmSans(
                                                fontWeight: FontWeight.w600,
                                                color: AppTheme.textDark)),
                                        const Spacer(),
                                        if (profile.activeCrop?.id == fc.id)
                                          const Icon(Icons.check,
                                              color: AppTheme.primaryGreen,
                                              size: 18),
                                      ],
                                    ),
                                  );
                                }).toList(),
                                child: CircleAvatar(
                                  radius: 20,
                                  backgroundColor: const Color(
                                      0xFF1B4332), // Dark green background like reference
                                  child: Text(
                                    _cropIcons[profile.activeCrop?.cropName] ??
                                        '🌱',
                                    style: const TextStyle(fontSize: 20),
                                  ),
                                ),
                              ),
                            )
                          else
                            CircleAvatar(
                              radius: 20,
                              backgroundColor: const Color(
                                  0xFF1B4332), // Dark green background like reference
                              child: Text(
                                _cropIcons[profile.activeCrop?.cropName] ??
                                    '🌱',
                                style: const TextStyle(fontSize: 20),
                              ),
                            ),
                        ],
                      ),
                    ],
                  ),

                  // Bottom Content Row
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Greeting
                      Text(
                        "Hi, Good Morning ${profile.displayName.split(' ').first}...",
                        style: GoogleFonts.dmSans(
                            color: Colors.white,
                            fontSize: 16,
                            fontWeight: FontWeight.w400,
                            shadows: [
                              Shadow(
                                  color: Colors.black45,
                                  blurRadius: 4,
                                  offset: const Offset(0, 1))
                            ]),
                      ),
                      const SizedBox(height: 6),

                      // Big Temperature & Condition
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            "${temp.toStringAsFixed(0)}°C",
                            style: GoogleFonts.roboto(
                              color: Colors.white,
                              fontSize: 76,
                              fontWeight: FontWeight.w400,
                              height: 1.0,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.end,
                              children: [
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.end,
                                  children: [
                                    const Icon(Icons.wb_cloudy_outlined,
                                        color: Colors.white, size: 18),
                                    const SizedBox(width: 6),
                                    Flexible(
                                      child: Text(
                                        condition,
                                        style: GoogleFonts.dmSans(
                                            color: Colors.white,
                                            fontSize: 14, // Slightly smaller
                                            fontWeight: FontWeight.w500),
                                        overflow: TextOverflow.ellipsis,
                                        maxLines: 1,
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  "${DateTime.now().hour}:${DateTime.now().minute.toString().padLeft(2, '0')} AM | ${_getMonthMap(DateTime.now().month)} ${DateTime.now().day}",
                                  style: GoogleFonts.dmSans(
                                      color: Colors.white,
                                      fontSize: 12,
                                      fontWeight: FontWeight.w400),
                                ),
                                const SizedBox(height: 12),
                              ],
                            ),
                          ),
                        ],
                      ),

                      const SizedBox(height: 12),

                      // Bottom Weather Pills
                      Wrap(
                        spacing: 14,
                        runSpacing: 8,
                        children: [
                          _weatherDetailPill("🌬️",
                              "${(rainfall * 2).toStringAsFixed(1)} km/h"),
                          _weatherDetailPill(
                              "💧", "${humidity.toStringAsFixed(1)}%"),
                        ],
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _getMonthMap(int month) {
    const map = {
      1: 'Jan',
      2: 'Feb',
      3: 'Mar',
      4: 'Apr',
      5: 'May',
      6: 'Jun',
      7: 'Jul',
      8: 'Aug',
      9: 'Sep',
      10: 'Oct',
      11: 'Nov',
      12: 'Dec'
    };
    return map[month] ?? '';
  }

  Widget _weatherDetailPill(String iconEmoji, String text) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.black26,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white12),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Text(iconEmoji, style: const TextStyle(fontSize: 14)),
        const SizedBox(width: 6),
        Text(text,
            style: GoogleFonts.dmSans(
                color: Colors.white,
                fontSize: 13,
                fontWeight: FontWeight.w500)),
      ]),
    );
  }

  // ═══════════════════════════════════════════════════
  // PRICE INSIGHT with MSP judgment phrase
  // ═══════════════════════════════════════════════════
  Widget _buildPriceInsightCard(
      Map<String, dynamic> nearest, String crop, String mandi) {
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
      judgmentText =
          "₹${mspDiff.toStringAsFixed(0)} above MSP. Good selling zone.";
      judgmentColor = AppTheme.primaryGreen;
    } else if (isAboveMsp) {
      judgmentText =
          "₹${mspDiff.toStringAsFixed(0)} above MSP. Marginal — consider waiting.";
      judgmentColor = AppTheme.accentOrange;
    } else {
      judgmentText =
          "₹${mspDiff.abs().toStringAsFixed(0)} below MSP. Hold if possible.";
      judgmentColor = AppTheme.error;
    }

    return AppCard(
      onTap: () => Navigator.push(
          context, MaterialPageRoute(builder: (_) => const PriceScreen())),
      padding: const EdgeInsets.all(14),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.storefront, color: AppTheme.primaryGreen, size: 16),
          const SizedBox(width: 6),
          Expanded(
              child: Text("$crop at ${nearest['mandi'] ?? mandi}",
                  style: AppTheme.bodyMedium.copyWith(fontSize: 11),
                  overflow: TextOverflow.ellipsis)),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(
                color: isUp ? AppTheme.primaryGreen : AppTheme.error,
                borderRadius: BorderRadius.circular(2)),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              Icon(isUp ? Icons.arrow_upward : Icons.arrow_downward,
                  color: Colors.white, size: 10),
              const SizedBox(width: 2),
              Text("₹${change.abs().toStringAsFixed(0)}",
                  style: const TextStyle(
                      color: Colors.white,
                      fontSize: 10,
                      fontWeight: FontWeight.bold)),
            ]),
          ),
        ]),
        const SizedBox(height: 8),
        Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
          Text("₹${todayPrice.toStringAsFixed(0)}",
              style: GoogleFonts.playfairDisplay(
                  fontSize: 30,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.textDark)),
          const SizedBox(width: 4),
          Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Text("/Quintal",
                  style: GoogleFonts.dmSans(
                      fontSize: 10, color: AppTheme.textMuted))),
          const Spacer(),
          Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
            Text("Yesterday: ₹${yesterdayPrice.toStringAsFixed(0)}",
                style: AppTheme.bodyMedium.copyWith(fontSize: 10)),
            Text(
                "MSP: ₹${msp.toStringAsFixed(0)} (${isAboveMsp ? '+' : ''}₹${mspDiff.toStringAsFixed(0)})",
                style: AppTheme.bodyMedium.copyWith(
                    fontSize: 10,
                    color:
                        isAboveMsp ? AppTheme.primaryGreen : AppTheme.error)),
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
            Icon(
                isAboveMsp && mspDiff > 50
                    ? Icons.thumb_up
                    : Icons.info_outline,
                color: judgmentColor,
                size: 14),
            const SizedBox(width: 6),
            Expanded(
                child: Text(judgmentText,
                    style: AppTheme.bodyMedium.copyWith(
                        fontSize: 11,
                        color: judgmentColor,
                        fontWeight: FontWeight.w600))),
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
    Color borderColor;
    Color iconColor;
    IconData icon;
    switch (level) {
      case 'HIGH':
        borderColor = AppTheme.error;
        iconColor = AppTheme.error;
        icon = Icons.warning_amber_rounded;
        break;
      case 'MEDIUM':
        borderColor = AppTheme.accentOrange;
        iconColor = AppTheme.accentOrange;
        icon = Icons.info_outline;
        break;
      default:
        borderColor = AppTheme.primaryGreen;
        iconColor = AppTheme.primaryGreen;
        icon = Icons.check_circle_outline;
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(AppTheme.cardRadius),
          border: Border.all(color: borderColor)),
      child: Row(children: [
        Icon(icon, color: iconColor, size: 20),
        const SizedBox(width: 10),
        Expanded(
            child:
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text("Market Situation Today",
              style: AppTheme.bodyMedium.copyWith(
                  fontWeight: FontWeight.bold, color: iconColor, fontSize: 12)),
          Text(risk['message'] ?? '',
              style: AppTheme.bodyMedium
                  .copyWith(fontSize: 11, color: AppTheme.textDark)),
        ])),
      ]),
    );
  }

  // ═══════════════════════════════════════════════════
  // QUICK ACTIONS GRID (2x2)
  // ═══════════════════════════════════════════════════
  Widget _buildQuickActionsGrid() {
    final items = <_ActionItem>[];
    final added = <String>{};

    void addItem(String id, String title, String sub, IconData icon, Color c,
        Widget screen, String imageUrl) {
      if (added.contains(id)) return;
      added.add(id);
      items.add(_ActionItem(
        id: id,
        title: title,
        subtitle: sub,
        icon: icon,
        color: c,
        screen: screen,
        isPrimary: items.isEmpty,
        imageUrl: imageUrl,
      ));
    }

    for (final card in _strategy.cardPriority) {
      if (card.contains('price') || card == 'daily_price') {
        addItem('price', "Price Forecast", "Short & long term",
            Icons.show_chart, AppTheme.accentBlue, const PriceScreen(),
            'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=400&q=80');
      } else if (card.contains('mandi') || card == 'mandi_compare') {
        addItem('mandi', "Mandi Prices", "Compare nearby", Icons.storefront,
            AppTheme.accentPurple, const MandiScreen(),
            'https://images.unsplash.com/photo-1542838132-92c53300491e?w=400&q=80');
      } else if (card.contains('sell') ||
          card == 'sell_hold' ||
          card == 'sell_window') {
        addItem(
            'rec',
            "Sell/Hold Advice",
            "When to sell",
            Icons.lightbulb_outline,
            AppTheme.accentOrange,
            const RecommendationScreen(),
            'https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=400&q=80');
      }
    }

    addItem('yield', "Yield Estimate", "Predict harvest", Icons.grass,
        AppTheme.primaryGreen, const YieldScreen(),
        'https://images.unsplash.com/photo-1574943320219-553eb213f72d?w=400&q=80');
    addItem('price', "Price Forecast", "Short & long term", Icons.show_chart,
        AppTheme.accentBlue, const PriceScreen(),
        'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=400&q=80');
    addItem(
        'rec',
        "Sell/Hold Advice",
        "When to sell",
        Icons.lightbulb_outline,
        AppTheme.accentOrange,
        const RecommendationScreen(),
        'https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=400&q=80');
    addItem('mandi', "Mandi Prices", "Compare nearby", Icons.storefront,
        AppTheme.accentPurple, const MandiScreen(),
        'https://images.unsplash.com/photo-1542838132-92c53300491e?w=400&q=80');

    final finalItems = items.take(4).toList();

    return Padding(
      padding: EdgeInsets.zero,
      child: Column(
        children: [
          // First Row
          Row(
            children: [
              Expanded(child: _buildActionCard(finalItems[0])),
              const SizedBox(width: 12),
              Expanded(child: finalItems.length > 1
                  ? _buildActionCard(finalItems[1])
                  : const SizedBox()),
            ],
          ),
          const SizedBox(height: 12),
          // Second Row
          Row(
            children: [
              Expanded(child: finalItems.length > 2
                  ? _buildActionCard(finalItems[2])
                  : const SizedBox()),
              const SizedBox(width: 12),
              Expanded(child: finalItems.length > 3
                  ? _buildActionCard(finalItems[3])
                  : const SizedBox()),
            ],
          ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════
  // QUICK ACTION CARD (GRID ITEM)
  // ═══════════════════════════════════════════════════
  Widget _buildActionCard(_ActionItem item) {
    return Container(
      height: 160,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.08),
            blurRadius: 16,
            offset: const Offset(0, 4),
          )
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () => Navigator.push(
              context, MaterialPageRoute(builder: (_) => item.screen)),
          borderRadius: BorderRadius.circular(24),
          child: Stack(
            fit: StackFit.expand,
            children: [
              // Background image
              Image.network(
                item.imageUrl,
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) => Container(
                  color: item.isPrimary
                      ? const Color(0xFFCAE87E)
                      : Colors.grey[200],
                ),
              ),
              // Gradient overlay for text readability
              Container(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      Colors.black.withOpacity(0.1),
                      Colors.black.withOpacity(0.65),
                    ],
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                  ),
                ),
              ),
              // Content
              Padding(
                padding: const EdgeInsets.all(14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Status pill
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: item.isPrimary
                            ? const Color(0xFFCAE87E)
                            : Colors.white.withOpacity(0.85),
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(item.icon,
                              color: item.isPrimary
                                  ? const Color(0xFF1B4332)
                                  : Colors.grey[600],
                              size: 12),
                          const SizedBox(width: 4),
                          Text(item.isPrimary ? "Now" : "Later",
                              style: GoogleFonts.dmSans(
                                  color: item.isPrimary
                                      ? const Color(0xFF1B4332)
                                      : Colors.grey[700],
                                  fontSize: 11,
                                  fontWeight: FontWeight.w600)),
                        ],
                      ),
                    ),
                    const Spacer(),
                    // Title
                    Text(item.title,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: GoogleFonts.dmSans(
                            color: Colors.white,
                            fontSize: 17,
                            fontWeight: FontWeight.w700,
                            height: 1.15,
                            shadows: [
                              Shadow(
                                color: Colors.black.withOpacity(0.5),
                                blurRadius: 4,
                              )
                            ])),
                    const SizedBox(height: 6),
                    // Subtitle chip
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 12, vertical: 6),
                      decoration: BoxDecoration(
                        color: item.isPrimary
                            ? const Color(0xFF1B4332)
                            : Colors.white.withOpacity(0.9),
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Text(
                          item.isPrimary ? item.subtitle : "Explore",
                          style: GoogleFonts.dmSans(
                              color: item.isPrimary
                                  ? Colors.white
                                  : AppTheme.textDark,
                              fontSize: 10,
                              fontWeight: FontWeight.w700)),
                    ),
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

class _ActionItem {
  final String id;
  final String title;
  final String subtitle;
  final IconData icon;
  final Color color;
  final Widget screen;
  final bool isPrimary;
  final String imageUrl;

  const _ActionItem({
    required this.id,
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.color,
    required this.screen,
    required this.isPrimary,
    required this.imageUrl,
  });
}
