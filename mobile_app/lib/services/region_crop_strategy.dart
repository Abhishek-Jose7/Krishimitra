/// Region + Crop Intelligence Strategy
///
/// This is the frontend "mirror" of the backend intelligence engine.
/// It determines:
///   - Which cards to show on the dashboard
///   - Their visual emphasis (prominent/normal/subtle)
///   - Card ordering
///   - Alert styling
///   - Sync frequency
///
/// Works OFFLINE — doesn't need backend to determine strategy.
/// The backend /dashboard/intelligent endpoint returns the same strategy
/// plus actual data.

import 'package:flutter/material.dart';
import '../theme.dart';

// ═══════════════════════════════════════════════════
// ENUMS
// ═══════════════════════════════════════════════════
enum RegionFocus { weatherHeavy, volatilityMandi, mspGovt, marketIntelligence, balanced }
enum CropType { perishable, semiPerishable, grain }
enum AdviceStyle { urgent, balanced, patient, strategic }
enum CardEmphasis { hero, prominent, normal, subtle }

// ═══════════════════════════════════════════════════
// DASHBOARD CARD — represents a single insight card
// ═══════════════════════════════════════════════════
class DashboardCardConfig {
  final String id;
  final String title;
  final String subtitle;
  final IconData icon;
  final Color color;
  final CardEmphasis emphasis;

  const DashboardCardConfig({
    required this.id,
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.color,
    this.emphasis = CardEmphasis.normal,
  });
}

// ═══════════════════════════════════════════════════
// ALERT — region or crop specific notification
// ═══════════════════════════════════════════════════
class IntelligenceAlert {
  final String type;
  final String severity;  // critical, high, medium, info
  final String icon;
  final String title;
  final String message;
  final String? action;

  const IntelligenceAlert({
    required this.type,
    required this.severity,
    required this.icon,
    required this.title,
    required this.message,
    this.action,
  });

  Color get severityColor {
    switch (severity) {
      case 'critical': return const Color(0xFFD32F2F);
      case 'high': return const Color(0xFFE65100);
      case 'medium': return const Color(0xFFF9A825);
      case 'info': return AppTheme.accentBlue;
      default: return AppTheme.textLight;
    }
  }

  Color get bgColor {
    switch (severity) {
      case 'critical': return const Color(0xFFFFEBEE);
      case 'high': return const Color(0xFFFFF3E0);
      case 'medium': return const Color(0xFFFFFDE7);
      case 'info': return const Color(0xFFE3F2FD);
      default: return Colors.grey.shade50;
    }
  }

  /// Parse from backend JSON
  factory IntelligenceAlert.fromJson(Map<String, dynamic> json) {
    return IntelligenceAlert(
      type: json['type'] ?? '',
      severity: json['severity'] ?? 'info',
      icon: json['icon'] ?? '📋',
      title: json['title'] ?? '',
      message: json['message'] ?? '',
      action: json['action'],
    );
  }
}

// ═══════════════════════════════════════════════════
// MSP CONTEXT
// ═══════════════════════════════════════════════════
class MspContext {
  final double baseMsp;
  final double stateBonus;
  final double effectiveMsp;
  final bool hasMsp;
  final String crop;

  const MspContext({
    required this.baseMsp,
    required this.stateBonus,
    required this.effectiveMsp,
    required this.hasMsp,
    required this.crop,
  });

  factory MspContext.fromJson(Map<String, dynamic> json) {
    return MspContext(
      baseMsp: (json['base_msp'] ?? 0).toDouble(),
      stateBonus: (json['state_bonus'] ?? 0).toDouble(),
      effectiveMsp: (json['effective_msp'] ?? 0).toDouble(),
      hasMsp: json['has_msp'] ?? false,
      crop: json['crop'] ?? '',
    );
  }
}

// ═══════════════════════════════════════════════════
// MAIN STRATEGY CLASS
// ═══════════════════════════════════════════════════
class RegionCropStrategy {
  final RegionFocus regionFocus;
  final String regionLabel;
  final CropType cropType;
  final AdviceStyle adviceStyle;
  final String forecastHorizon;
  final List<String> cardPriority;
  final double weatherWeight;
  final double marketWeight;
  final double mspWeight;
  final int syncIntervalHours;
  final bool volatilitySensitive;
  final int shelfLifeDays;
  final bool storageCritical;
  final List<IntelligenceAlert> alerts;
  final MspContext? mspContext;

  RegionCropStrategy({
    required this.regionFocus,
    required this.regionLabel,
    required this.cropType,
    required this.adviceStyle,
    required this.forecastHorizon,
    required this.cardPriority,
    required this.weatherWeight,
    required this.marketWeight,
    required this.mspWeight,
    required this.syncIntervalHours,
    required this.volatilitySensitive,
    required this.shelfLifeDays,
    required this.storageCritical,
    required this.alerts,
    this.mspContext,
  });

  // ═══════════════════════════════════════════════════
  // FACTORY: Build from backend response
  // ═══════════════════════════════════════════════════
  factory RegionCropStrategy.fromJson(Map<String, dynamic> json) {
    final strategy = json['strategy'] ?? {};
    final weights = strategy['weights'] ?? {};

    return RegionCropStrategy(
      regionFocus: _parseRegionFocus(strategy['region_focus']),
      regionLabel: strategy['region_label'] ?? 'Smart Dashboard',
      cropType: _parseCropType(strategy['crop_type']),
      adviceStyle: _parseAdviceStyle(strategy['advice_style']),
      forecastHorizon: strategy['forecast_horizon'] ?? 'medium',
      cardPriority: List<String>.from(strategy['card_priority'] ?? []),
      weatherWeight: (weights['weather'] ?? 0.5).toDouble(),
      marketWeight: (weights['market'] ?? 0.5).toDouble(),
      mspWeight: (weights['msp'] ?? 0.5).toDouble(),
      syncIntervalHours: strategy['sync_interval_hours'] ?? 8,
      volatilitySensitive: json['storage']?['storage_critical'] ?? false,
      shelfLifeDays: json['storage']?['shelf_life_days'] ?? 90,
      storageCritical: json['storage']?['storage_critical'] ?? false,
      alerts: (json['alerts'] as List<dynamic>? ?? [])
          .map((a) => IntelligenceAlert.fromJson(a as Map<String, dynamic>))
          .toList(),
      mspContext: json['msp'] != null ? MspContext.fromJson(json['msp']) : null,
    );
  }

  // ═══════════════════════════════════════════════════
  // FACTORY: Build OFFLINE from stored profile
  // ═══════════════════════════════════════════════════
  factory RegionCropStrategy.fromLocal({
    required String? state,
    required String? crop,
    required bool storageAvailable,
  }) {
    final regionFocus = _resolveRegion(state);
    final cropType = _resolveCropType(crop);
    final adviceStyle = cropType == CropType.perishable
        ? AdviceStyle.urgent
        : cropType == CropType.grain
            ? AdviceStyle.patient
            : AdviceStyle.balanced;

    // Build card priority based on region + crop
    final cards = _buildCardPriority(regionFocus, cropType);

    // Build offline alerts
    final alerts = _buildOfflineAlerts(state, crop, cropType, storageAvailable);

    // MSP lookup
    final mspContext = _lookupMsp(crop, state);

    // Weights
    double ww = 0.5, mw = 0.5, msw = 0.5;
    int syncHours = 8;
    String label = 'Smart Dashboard';

    switch (regionFocus) {
      case RegionFocus.weatherHeavy:
        ww = 0.9; mw = 0.4; msw = 0.3; syncHours = 3;
        label = 'Weather Intelligence';
        break;
      case RegionFocus.volatilityMandi:
        ww = 0.4; mw = 0.9; msw = 0.5; syncHours = 6;
        label = 'Market Volatility Watch';
        break;
      case RegionFocus.mspGovt:
        ww = 0.4; mw = 0.6; msw = 0.9; syncHours = 12;
        label = 'MSP & Government Focus';
        break;
      case RegionFocus.marketIntelligence:
        ww = 0.5; mw = 0.95; msw = 0.6; syncHours = 4;
        label = 'Market Intelligence';
        break;
      default:
        break;
    }

    // Crop type overrides sync for perishables
    if (cropType == CropType.perishable) {
      syncHours = syncHours > 4 ? 4 : syncHours;
    }

    return RegionCropStrategy(
      regionFocus: regionFocus,
      regionLabel: label,
      cropType: cropType,
      adviceStyle: adviceStyle,
      forecastHorizon: cropType == CropType.perishable ? 'short'
          : cropType == CropType.grain ? 'long' : 'medium',
      cardPriority: cards,
      weatherWeight: ww,
      marketWeight: mw,
      mspWeight: msw,
      syncIntervalHours: syncHours,
      volatilitySensitive: cropType == CropType.perishable,
      shelfLifeDays: _getShelfLife(crop),
      storageCritical: cropType != CropType.grain || !storageAvailable,
      alerts: alerts,
      mspContext: mspContext,
    );
  }

  // ═══════════════════════════════════════════════════
  // PUBLIC: Should this card be shown prominently?
  // ═══════════════════════════════════════════════════
  CardEmphasis getCardEmphasis(String cardId) {
    final idx = cardPriority.indexOf(cardId);
    if (idx < 0) return CardEmphasis.subtle;
    if (idx == 0) return CardEmphasis.hero;
    if (idx <= 2) return CardEmphasis.prominent;
    return CardEmphasis.normal;
  }

  /// Weather card should be expanded (multi-row)?
  bool get showExtendedWeather => weatherWeight >= 0.7;

  /// Show MSP comparison card?
  bool get showMspCard => mspWeight >= 0.5 && (mspContext?.hasMsp ?? false);

  /// Show mandi comparison card prominently?
  bool get showMandiCompareProminent => marketWeight >= 0.8;

  /// Show volatility alert?
  bool get showVolatilityAlert => volatilitySensitive || marketWeight >= 0.8;

  /// Show storage countdown for perishables?
  bool get showStorageCountdown =>
      cropType == CropType.perishable && storageCritical;

  /// Forecast label for UI
  String get forecastLabel {
    switch (forecastHorizon) {
      case 'short': return '7-day forecast';
      case 'long': return '90-day forecast';
      default: return '30-day forecast';
    }
  }

  /// Advice label
  String get adviceLabel {
    switch (adviceStyle) {
      case AdviceStyle.urgent: return 'Act Now';
      case AdviceStyle.patient: return 'Long-term Plan';
      case AdviceStyle.strategic: return 'Strategic Advice';
      default: return 'Recommendation';
    }
  }

  // ═══════════════════════════════════════════════════
  // PRIVATE RESOLVERS
  // ═══════════════════════════════════════════════════
  static RegionFocus _resolveRegion(String? state) {
    switch (state) {
      case 'Kerala': return RegionFocus.weatherHeavy;
      case 'Karnataka': return RegionFocus.volatilityMandi;
      case 'Tamil Nadu': return RegionFocus.mspGovt;
      case 'Maharashtra': return RegionFocus.marketIntelligence;
      case 'Andhra Pradesh':
      case 'Telangana':
        return RegionFocus.mspGovt;
      case 'Gujarat':
      case 'Rajasthan':
        return RegionFocus.marketIntelligence;
      case 'Punjab':
      case 'Haryana':
        return RegionFocus.mspGovt;
      default: return RegionFocus.balanced;
    }
  }

  static CropType _resolveCropType(String? crop) {
    switch (crop?.toLowerCase()) {
      case 'onion': return CropType.perishable;
      case 'sugarcane': return CropType.perishable;
      case 'cotton': return CropType.semiPerishable;
      case 'groundnut': return CropType.semiPerishable;
      default: return CropType.grain;
    }
  }

  static int _getShelfLife(String? crop) {
    switch (crop?.toLowerCase()) {
      case 'onion': return 14;
      case 'sugarcane': return 3;
      case 'cotton': return 180;
      case 'groundnut': return 60;
      case 'rice': return 365;
      case 'wheat': return 365;
      case 'maize': return 180;
      case 'soybean': return 120;
      default: return 90;
    }
  }

  static List<String> _buildCardPriority(RegionFocus region, CropType crop) {
    final List<String> cards = [];

    // Region-first ordering
    switch (region) {
      case RegionFocus.weatherHeavy:
        cards.addAll(['weather_extended', 'rainfall_alert', 'flood_risk']);
        break;
      case RegionFocus.volatilityMandi:
        cards.addAll(['volatility_alert', 'mandi_compare', 'price_trend']);
        break;
      case RegionFocus.mspGovt:
        cards.addAll(['msp_comparison', 'govt_procurement', 'sell_hold']);
        break;
      case RegionFocus.marketIntelligence:
        cards.addAll(['price_insight', 'sell_hold', 'mandi_compare']);
        break;
      case RegionFocus.balanced:
        cards.addAll(['weather', 'price_insight', 'sell_hold']);
        break;
    }

    // Crop-specific additions
    switch (crop) {
      case CropType.perishable:
        if (!cards.contains('volatility_alert')) cards.add('volatility_alert');
        cards.addAll(['daily_price', 'storage_countdown', 'sell_window']);
        break;
      case CropType.semiPerishable:
        cards.addAll(['price_trend', 'storage_advice']);
        if (!cards.contains('msp_comparison')) cards.add('msp_comparison');
        break;
      case CropType.grain:
        if (!cards.contains('msp_comparison')) cards.add('msp_comparison');
        cards.addAll(['long_term_trend', 'storage_optimization']);
        if (!cards.contains('sell_hold')) cards.add('sell_hold');
        break;
    }

    // Deduplicate while preserving order
    final seen = <String>{};
    return cards.where((c) => seen.add(c)).toList();
  }

  static List<IntelligenceAlert> _buildOfflineAlerts(
    String? state, String? crop, CropType cropType, bool storageAvailable,
  ) {
    final alerts = <IntelligenceAlert>[];
    final month = DateTime.now().month;

    // Region alerts
    if (state == 'Kerala' && [6, 7, 8, 9, 10].contains(month)) {
      alerts.add(const IntelligenceAlert(
        type: 'weather_warning', severity: 'high', icon: '🌧️',
        title: 'Monsoon Active',
        message: 'Heavy rainfall expected. Secure stored crop and avoid transport.',
        action: 'Check weather forecast before any market trip.',
      ));
    }

    if (state == 'Karnataka') {
      alerts.add(const IntelligenceAlert(
        type: 'volatility_watch', severity: 'medium', icon: '📊',
        title: 'Price Volatility Active',
        message: 'Karnataka mandis show high price variation. Compare before selling.',
        action: 'Check at least 3 mandis before finalizing sale.',
      ));
    }

    if (state == 'Tamil Nadu') {
      alerts.add(const IntelligenceAlert(
        type: 'msp_info', severity: 'info', icon: '🏛️',
        title: 'Government Procurement Active',
        message: 'Check if your district has active procurement centers.',
        action: 'Visit nearest Uzhavar Sandhai for direct consumer sale.',
      ));
    }

    if (state == 'Maharashtra') {
      alerts.add(const IntelligenceAlert(
        type: 'market_intel', severity: 'medium', icon: '📈',
        title: 'Market Intelligence Update',
        message: 'High arrival volumes in nearby mandis. Monitor prices closely.',
        action: 'Compare prices across Pune, Nashik, and Nagpur mandis.',
      ));
    }

    // Crop alerts
    if (cropType == CropType.perishable) {
      final shelf = _getShelfLife(crop);
      alerts.add(IntelligenceAlert(
        type: 'perishable_warning', severity: 'high', icon: '⏰',
        title: '$crop — Sell within $shelf days',
        message: '$crop is perishable. Quality drops rapidly after harvest.',
        action: 'Plan sale within $shelf days of harvest.',
      ));
    } else if (cropType == CropType.grain) {
      if (storageAvailable) {
        final shelf = _getShelfLife(crop);
        alerts.add(IntelligenceAlert(
          type: 'storage_optimization', severity: 'info', icon: '🏪',
          title: 'Storage Advantage',
          message: 'You can store $crop for up to $shelf days. Wait for best price.',
          action: 'Monitor moisture weekly. Check for pests monthly.',
        ));
      } else {
        alerts.add(IntelligenceAlert(
          type: 'no_storage_warning', severity: 'medium', icon: '⚠️',
          title: 'No Storage Available',
          message: 'Without storage, sell $crop within 2 weeks of harvest.',
          action: 'Consider renting warehouse space or selling at MSP procurement.',
        ));
      }
    }

    return alerts;
  }

  static MspContext? _lookupMsp(String? crop, String? state) {
    const mspData = {
      'Rice': {'msp': 2300, 'bonus': {'Tamil Nadu': 200, 'Telangana': 500}},
      'Wheat': {'msp': 2275, 'bonus': {'Madhya Pradesh': 200, 'Punjab': 100}},
      'Maize': {'msp': 2090, 'bonus': {}},
      'Soybean': {'msp': 4892, 'bonus': {'Madhya Pradesh': 200}},
      'Cotton': {'msp': 7121, 'bonus': {'Gujarat': 200}},
      'Sugarcane': {'msp': 340, 'bonus': {'Uttar Pradesh': 35, 'Maharashtra': 15}},
      'Groundnut': {'msp': 6783, 'bonus': {}},
      'Onion': {'msp': 0, 'bonus': {}},
    };

    final entry = mspData[crop];
    if (entry == null) return null;

    final baseMsp = (entry['msp'] as int).toDouble();
    final bonusMap = entry['bonus'] as Map<String, int>;
    final stateBonus = (bonusMap[state] ?? 0).toDouble();

    return MspContext(
      baseMsp: baseMsp,
      stateBonus: stateBonus,
      effectiveMsp: baseMsp + stateBonus,
      hasMsp: baseMsp > 0,
      crop: crop ?? '',
    );
  }

  // ═══════════════════════════════════════════════════
  // PARSERS
  // ═══════════════════════════════════════════════════
  static RegionFocus _parseRegionFocus(String? s) {
    switch (s) {
      case 'weather_heavy': return RegionFocus.weatherHeavy;
      case 'volatility_mandi': return RegionFocus.volatilityMandi;
      case 'msp_govt': return RegionFocus.mspGovt;
      case 'market_intelligence': return RegionFocus.marketIntelligence;
      default: return RegionFocus.balanced;
    }
  }

  static CropType _parseCropType(String? s) {
    switch (s) {
      case 'perishable': return CropType.perishable;
      case 'semi_perishable': return CropType.semiPerishable;
      default: return CropType.grain;
    }
  }

  static AdviceStyle _parseAdviceStyle(String? s) {
    switch (s) {
      case 'urgent': return AdviceStyle.urgent;
      case 'patient': return AdviceStyle.patient;
      case 'strategic': return AdviceStyle.strategic;
      default: return AdviceStyle.balanced;
    }
  }
}
