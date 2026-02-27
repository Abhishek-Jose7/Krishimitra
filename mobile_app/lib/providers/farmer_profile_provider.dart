import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Central farmer profile state. Loaded once at app startup from SharedPreferences.
/// Every screen reads from this. Data is written once during onboarding and
/// never asked again unless the user taps "Edit Farm Profile".
class FarmerProfile extends ChangeNotifier {
  // ── Auth ──
  String? token;
  int? farmerId;
  String? phone;

  // ── Onboarding ──
  String language = 'en';
  bool onboardingComplete = false;

  // ── Location ──
  String? state;
  String? district;
  double? latitude;
  double? longitude;
  String? nearestMandi;

  // ── Farm ──
  String? primaryCrop;
  List<String> crops = [];
  double? landSize;
  bool storageAvailable = false;
  String? soilType;
  String? irrigationType;

  // ── Cache ──
  String? lastForecast;
  String? lastMandiPrices;
  String? lastYieldPrediction;
  String? lastSyncTimestamp;

  // ── Constructor ──
  FarmerProfile();

  // ═══════════════════════════════════════════
  // Load from SharedPreferences (called at startup)
  // ═══════════════════════════════════════════
  Future<void> loadFromLocal() async {
    final prefs = await SharedPreferences.getInstance();

    token = prefs.getString('token');
    farmerId = prefs.getInt('farmer_id');
    phone = prefs.getString('phone');

    language = prefs.getString('language') ?? 'en';
    onboardingComplete = prefs.getBool('onboarding_complete') ?? false;

    state = prefs.getString('state');
    district = prefs.getString('district');
    latitude = prefs.getDouble('latitude');
    longitude = prefs.getDouble('longitude');
    nearestMandi = prefs.getString('nearest_mandi');

    primaryCrop = prefs.getString('primary_crop');
    final cropsJson = prefs.getString('crops');
    if (cropsJson != null) {
      try { crops = List<String>.from(json.decode(cropsJson)); } catch (_) { crops = []; }
    } else {
      crops = primaryCrop != null ? [primaryCrop!] : [];
    }
    landSize = prefs.getDouble('land_size');
    storageAvailable = prefs.getBool('storage_available') ?? false;
    soilType = prefs.getString('soil_type');
    irrigationType = prefs.getString('irrigation_type');

    lastForecast = prefs.getString('last_forecast');
    lastMandiPrices = prefs.getString('last_mandi_prices');
    lastYieldPrediction = prefs.getString('last_yield_prediction');
    lastSyncTimestamp = prefs.getString('last_sync_timestamp');

    notifyListeners();
  }

  // ═══════════════════════════════════════════
  // Save to SharedPreferences
  // ═══════════════════════════════════════════
  Future<void> saveToLocal() async {
    final prefs = await SharedPreferences.getInstance();

    if (token != null) prefs.setString('token', token!);
    if (farmerId != null) prefs.setInt('farmer_id', farmerId!);
    if (phone != null) prefs.setString('phone', phone!);

    prefs.setString('language', language);
    prefs.setBool('onboarding_complete', onboardingComplete);

    if (state != null) prefs.setString('state', state!);
    if (district != null) prefs.setString('district', district!);
    if (latitude != null) prefs.setDouble('latitude', latitude!);
    if (longitude != null) prefs.setDouble('longitude', longitude!);
    if (nearestMandi != null) prefs.setString('nearest_mandi', nearestMandi!);

    if (primaryCrop != null) prefs.setString('primary_crop', primaryCrop!);
    prefs.setString('crops', json.encode(crops));
    if (landSize != null) prefs.setDouble('land_size', landSize!);
    prefs.setBool('storage_available', storageAvailable);
    if (soilType != null) prefs.setString('soil_type', soilType!);
    if (irrigationType != null) prefs.setString('irrigation_type', irrigationType!);

    if (lastForecast != null) prefs.setString('last_forecast', lastForecast!);
    if (lastMandiPrices != null) prefs.setString('last_mandi_prices', lastMandiPrices!);
    if (lastYieldPrediction != null) prefs.setString('last_yield_prediction', lastYieldPrediction!);
    if (lastSyncTimestamp != null) prefs.setString('last_sync_timestamp', lastSyncTimestamp!);

    notifyListeners();
  }

  // ═══════════════════════════════════════════
  // Update specific fields and persist
  // ═══════════════════════════════════════════
  Future<void> setLanguage(String lang) async {
    language = lang;
    await saveToLocal();
  }

  Future<void> setAuth({required String tkn, required int id, required String ph}) async {
    token = tkn;
    farmerId = id;
    phone = ph;
    await saveToLocal();
  }

  Future<void> setLocation({
    required String st,
    required String dist,
    double? lat,
    double? lng,
    String? mandi,
  }) async {
    state = st;
    district = dist;
    latitude = lat;
    longitude = lng;
    nearestMandi = mandi;
    await saveToLocal();
  }

  Future<void> setFarmProfile({
    required String crop,
    List<String>? crops,
    required double land,
    required bool storage,
    String? soil,
    String? irrigation,
  }) async {
    primaryCrop = crop;
    this.crops = crops ?? [crop];
    landSize = land;
    storageAvailable = storage;
    soilType = soil;
    irrigationType = irrigation;
    await saveToLocal();
  }

  /// Display string for all crops
  String get displayCrops {
    if (crops.isEmpty) return primaryCrop ?? 'N/A';
    return crops.join(', ');
  }

  Future<void> completeOnboarding() async {
    onboardingComplete = true;
    await saveToLocal();
  }

  // Store cached data for offline-first
  Future<void> cacheData({
    String? forecast,
    String? mandiPrices,
    String? yieldPrediction,
  }) async {
    if (forecast != null) lastForecast = forecast;
    if (mandiPrices != null) lastMandiPrices = mandiPrices;
    if (yieldPrediction != null) lastYieldPrediction = yieldPrediction;
    lastSyncTimestamp = DateTime.now().toIso8601String();
    await saveToLocal();
  }

  // Parse cached JSON safely
  Map<String, dynamic>? get cachedForecast {
    if (lastForecast == null) return null;
    try {
      return json.decode(lastForecast!) as Map<String, dynamic>;
    } catch (_) {
      return null;
    }
  }

  List<dynamic>? get cachedMandiPrices {
    if (lastMandiPrices == null) return null;
    try {
      return json.decode(lastMandiPrices!) as List<dynamic>;
    } catch (_) {
      return null;
    }
  }

  // Get farmer name for greeting
  String get displayName {
    if (phone != null && phone!.length >= 4) {
      return 'Farmer ${phone!.substring(phone!.length - 4)}';
    }
    return 'Farmer';
  }

  // Computed: expected yield
  double get expectedYield {
    if (landSize == null) return 0;
    // Average yield per hectare (Rice ≈ 4.7 tons/ha India avg)
    double yieldPerHectare;
    switch ((primaryCrop ?? '').toLowerCase()) {
      case 'rice':
        yieldPerHectare = 4.7;
        break;
      case 'wheat':
        yieldPerHectare = 3.5;
        break;
      case 'maize':
        yieldPerHectare = 3.0;
        break;
      case 'soybean':
        yieldPerHectare = 1.2;
        break;
      default:
        yieldPerHectare = 3.0;
    }
    return landSize! * yieldPerHectare;
  }

  // ═════════════════
  // RESET (logout)
  // ═════════════════
  Future<void> clearAll() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
    token = null;
    farmerId = null;
    phone = null;
    language = 'en';
    onboardingComplete = false;
    state = null;
    district = null;
    latitude = null;
    longitude = null;
    nearestMandi = null;
    primaryCrop = null;
    crops = [];
    landSize = null;
    storageAvailable = false;
    soilType = null;
    irrigationType = null;
    lastForecast = null;
    lastMandiPrices = null;
    lastYieldPrediction = null;
    lastSyncTimestamp = null;
    notifyListeners();
  }
}
