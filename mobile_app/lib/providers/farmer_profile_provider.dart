import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

// ═══════════════════════════════════════════════════
// DATA MODELS
// ═══════════════════════════════════════════════════

/// A single crop record on a farm. This is the PRIMARY context
/// that drives the entire intelligence pipeline.
class FarmCropModel {
  final String id;
  final String farmId;
  final String cropName;
  final String? variety;
  final double areaHectares;
  final String? sowingDate;
  final String? expectedHarvestDate;
  final int? plantingYear;
  final int? treeCount;
  final bool isPerennial;
  final String? preferredMandi;

  FarmCropModel({
    required this.id,
    required this.farmId,
    required this.cropName,
    this.variety,
    this.areaHectares = 0,
    this.sowingDate,
    this.expectedHarvestDate,
    this.plantingYear,
    this.treeCount,
    this.isPerennial = false,
    this.preferredMandi,
  });

  factory FarmCropModel.fromJson(Map<String, dynamic> json) {
    return FarmCropModel(
      id: json['id']?.toString() ?? '',
      farmId: json['farm_id']?.toString() ?? '',
      cropName: json['crop_name'] ?? 'Rice',
      variety: json['variety'],
      areaHectares: (json['area_hectares'] ?? 0).toDouble(),
      sowingDate: json['sowing_date'],
      expectedHarvestDate: json['expected_harvest_date'],
      plantingYear: json['planting_year'],
      treeCount: json['tree_count'],
      isPerennial: json['is_perennial'] ?? false,
      preferredMandi: json['preferred_mandi'],
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'farm_id': farmId,
    'crop_name': cropName,
    'variety': variety,
    'area_hectares': areaHectares,
    'sowing_date': sowingDate,
    'expected_harvest_date': expectedHarvestDate,
    'planting_year': plantingYear,
    'tree_count': treeCount,
    'is_perennial': isPerennial,
    'preferred_mandi': preferredMandi,
  };

  /// Convert hectares to acres for display
  double get areaAcres => areaHectares / 0.4047;
}


/// A farm record belonging to a user.
class FarmModel {
  final String id;
  final String userId;
  final String? farmName;
  final double? totalLandHectares;
  final String? soilType;
  final String? irrigationType;
  final bool hasStorage;
  final double storageCapacityQuintals;
  final List<FarmCropModel> crops;

  FarmModel({
    required this.id,
    required this.userId,
    this.farmName,
    this.totalLandHectares,
    this.soilType,
    this.irrigationType,
    this.hasStorage = false,
    this.storageCapacityQuintals = 0,
    this.crops = const [],
  });

  factory FarmModel.fromJson(Map<String, dynamic> json) {
    final cropsList = (json['crops'] as List<dynamic>?)
        ?.map((c) => FarmCropModel.fromJson(c as Map<String, dynamic>))
        .toList() ?? [];

    return FarmModel(
      id: json['id']?.toString() ?? '',
      userId: json['user_id']?.toString() ?? '',
      farmName: json['farm_name'],
      totalLandHectares: (json['total_land_hectares'] ?? 0).toDouble(),
      soilType: json['soil_type'],
      irrigationType: json['irrigation_type'],
      hasStorage: json['has_storage'] ?? false,
      storageCapacityQuintals: (json['storage_capacity_quintals'] ?? 0).toDouble(),
      crops: cropsList,
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'user_id': userId,
    'farm_name': farmName,
    'total_land_hectares': totalLandHectares,
    'soil_type': soilType,
    'irrigation_type': irrigationType,
    'has_storage': hasStorage,
    'storage_capacity_quintals': storageCapacityQuintals,
    'crops': crops.map((c) => c.toJson()).toList(),
  };
}


// ═══════════════════════════════════════════════════
// FARMER PROFILE PROVIDER
// ═══════════════════════════════════════════════════

/// Central farmer profile state. Loaded once at app startup.
/// Now supports multi-farm, multi-crop with an active crop context.
class FarmerProfile extends ChangeNotifier {
  // ── Auth ──
  String? token;
  String? farmerId;  // Changed to String (UUID)
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

  // ── Farms & Crops (structured) ──
  List<FarmModel> farms = [];
  FarmCropModel? activeCrop;

  // ── Cache ──
  String? lastForecast;
  String? lastMandiPrices;
  String? lastYieldPrediction;
  String? lastSyncTimestamp;

  // ── Constructor ──
  FarmerProfile();

  // ═══════════════════════════════════════════════
  // COMPUTED GETTERS — backed by activeCrop
  // ═══════════════════════════════════════════════

  /// The crop name from the active context
  String? get primaryCrop => activeCrop?.cropName;

  /// Land size for the active crop (in hectares)
  double? get landSize => activeCrop?.areaHectares;

  /// Preferred mandi for the active crop
  String? get activeMandiName => activeCrop?.preferredMandi ?? nearestMandi;

  /// Whether storage is available (from the farm of the active crop)
  bool get storageAvailable {
    if (activeCrop == null) return false;
    final farm = farms.firstWhere(
      (f) => f.id == activeCrop!.farmId,
      orElse: () => FarmModel(id: '', userId: ''),
    );
    return farm.hasStorage;
  }

  /// Soil type from the active crop's farm
  String? get soilType {
    if (activeCrop == null) return null;
    final farm = farms.firstWhere(
      (f) => f.id == activeCrop!.farmId,
      orElse: () => FarmModel(id: '', userId: ''),
    );
    return farm.soilType;
  }

  /// Irrigation type from the active crop's farm
  String? get irrigationType {
    if (activeCrop == null) return null;
    final farm = farms.firstWhere(
      (f) => f.id == activeCrop!.farmId,
      orElse: () => FarmModel(id: '', userId: ''),
    );
    return farm.irrigationType;
  }

  /// All crop names across all farms (for backwards compat)
  List<String> get crops {
    return allFarmCrops.map((c) => c.cropName).toList();
  }

  /// All FarmCropModel records across all farms
  List<FarmCropModel> get allFarmCrops {
    return farms.expand((f) => f.crops).toList();
  }

  /// Display string for crops
  String get displayCrops {
    if (activeCrop != null) return activeCrop!.cropName;
    final names = crops;
    if (names.isEmpty) return 'N/A';
    return names.join(', ');
  }

  String get displayName {
    if (phone != null && phone!.length >= 4) {
      return 'Farmer ${phone!.substring(phone!.length - 4)}';
    }
    return 'Farmer';
  }

  /// Expected yield (estimated) for the active crop
  double get expectedYield {
    final area = activeCrop?.areaHectares ?? 0;
    if (area <= 0) return 0;
    double yieldPerHectare;
    switch ((primaryCrop ?? '').toLowerCase()) {
      case 'rice': yieldPerHectare = 4.7; break;
      case 'wheat': yieldPerHectare = 3.5; break;
      case 'maize': yieldPerHectare = 3.0; break;
      case 'soybean': yieldPerHectare = 1.2; break;
      case 'groundnut': yieldPerHectare = 1.6; break;
      case 'cotton': yieldPerHectare = 1.8; break;
      case 'sugarcane': yieldPerHectare = 70.0; break;
      case 'coconut': yieldPerHectare = 10.0; break;
      case 'onion': yieldPerHectare = 17.0; break;
      case 'tomato': yieldPerHectare = 25.0; break;
      case 'potato': yieldPerHectare = 22.0; break;
      default: yieldPerHectare = 3.0;
    }
    return area * yieldPerHectare;
  }

  // ═══════════════════════════════════════════════
  // ACTIVE CROP MANAGEMENT
  // ═══════════════════════════════════════════════

  /// Set the active crop context
  Future<void> setActiveCrop(FarmCropModel crop) async {
    activeCrop = crop;
    // Clear cached data since crop context changed
    lastForecast = null;
    lastMandiPrices = null;
    lastYieldPrediction = null;
    await saveToLocal();
  }

  /// Set active crop by ID
  Future<void> setActiveCropById(String cropId) async {
    for (final farm in farms) {
      for (final crop in farm.crops) {
        if (crop.id == cropId) {
          await setActiveCrop(crop);
          return;
        }
      }
    }
  }

  // ═══════════════════════════════════════════════
  // FARM DATA MANAGEMENT
  // ═══════════════════════════════════════════════

  /// Load farms from a backend response
  void loadFarmsFromJson(List<dynamic> farmsJson) {
    // Remember old active crop name for re-sync
    final oldCropName = activeCrop?.cropName;

    farms = farmsJson
        .map((f) => FarmModel.fromJson(f as Map<String, dynamic>))
        .toList();

    // Re-sync activeCrop: try to match by ID first, then by crop name
    if (activeCrop != null && allFarmCrops.isNotEmpty) {
      final byId = allFarmCrops.where((c) => c.id == activeCrop!.id);
      if (byId.isNotEmpty) {
        activeCrop = byId.first;
      } else if (oldCropName != null) {
        // ID changed (local → real UUID) — match by crop name
        final byName = allFarmCrops.where((c) => c.cropName == oldCropName);
        activeCrop = byName.isNotEmpty ? byName.first : allFarmCrops.first;
      } else {
        activeCrop = allFarmCrops.first;
      }
    } else if (allFarmCrops.isNotEmpty) {
      activeCrop = allFarmCrops.first;
    }
  }

  // ═══════════════════════════════════════════════
  // Load from SharedPreferences (called at startup)
  // ═══════════════════════════════════════════════
  Future<void> loadFromLocal() async {
    final prefs = await SharedPreferences.getInstance();

    token = prefs.getString('token');
    farmerId = prefs.getString('farmer_id');
    phone = prefs.getString('phone');

    language = prefs.getString('language') ?? 'en';
    onboardingComplete = prefs.getBool('onboarding_complete') ?? false;

    state = prefs.getString('state');
    district = prefs.getString('district');
    latitude = prefs.getDouble('latitude');
    longitude = prefs.getDouble('longitude');
    nearestMandi = prefs.getString('nearest_mandi');

    // ── Load structured farm data ──
    final farmsJson = prefs.getString('farms_data');
    if (farmsJson != null) {
      try {
        final decoded = json.decode(farmsJson) as List<dynamic>;
        farms = decoded.map((f) => FarmModel.fromJson(f as Map<String, dynamic>)).toList();
      } catch (_) {
        farms = [];
      }
    }

    // ── Restore active crop ──
    final activeCropId = prefs.getString('active_crop_id');
    if (activeCropId != null && allFarmCrops.isNotEmpty) {
      activeCrop = allFarmCrops.firstWhere(
        (c) => c.id == activeCropId,
        orElse: () => allFarmCrops.first,
      );
    } else if (allFarmCrops.isNotEmpty) {
      activeCrop = allFarmCrops.first;
    }

    // ── Cache ──
    lastForecast = prefs.getString('last_forecast');
    lastMandiPrices = prefs.getString('last_mandi_prices');
    lastYieldPrediction = prefs.getString('last_yield_prediction');
    lastSyncTimestamp = prefs.getString('last_sync_timestamp');

    notifyListeners();
  }

  // ═══════════════════════════════════════════════
  // Save to SharedPreferences
  // ═══════════════════════════════════════════════
  Future<void> saveToLocal() async {
    final prefs = await SharedPreferences.getInstance();

    if (token != null) prefs.setString('token', token!);
    if (farmerId != null) prefs.setString('farmer_id', farmerId!);
    if (phone != null) prefs.setString('phone', phone!);

    prefs.setString('language', language);
    prefs.setBool('onboarding_complete', onboardingComplete);

    if (state != null) prefs.setString('state', state!);
    if (district != null) prefs.setString('district', district!);
    if (latitude != null) prefs.setDouble('latitude', latitude!);
    if (longitude != null) prefs.setDouble('longitude', longitude!);
    if (nearestMandi != null) prefs.setString('nearest_mandi', nearestMandi!);

    // ── Save structured farm data ──
    prefs.setString('farms_data', json.encode(farms.map((f) => f.toJson()).toList()));

    // ── Save active crop ID ──
    if (activeCrop != null) {
      prefs.setString('active_crop_id', activeCrop!.id);
    } else {
      prefs.remove('active_crop_id');
    }

    // ── Cache ──
    if (lastForecast != null) prefs.setString('last_forecast', lastForecast!);
    if (lastMandiPrices != null) prefs.setString('last_mandi_prices', lastMandiPrices!);
    if (lastYieldPrediction != null) prefs.setString('last_yield_prediction', lastYieldPrediction!);
    if (lastSyncTimestamp != null) prefs.setString('last_sync_timestamp', lastSyncTimestamp!);

    notifyListeners();
  }

  // ═══════════════════════════════════════════════
  // Update helpers
  // ═══════════════════════════════════════════════
  Future<void> setLanguage(String lang) async {
    language = lang;
    await saveToLocal();
  }

  Future<void> setAuth({required String tkn, required String id, required String ph}) async {
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

  /// Legacy setFarmProfile — still works, but now creates FarmModel + FarmCropModel
  Future<void> setFarmProfile({
    required String crop,
    List<String>? crops,
    required double land,
    required bool storage,
    String? soil,
    String? irrigation,
    Map<String, double>? cropAreas,
  }) async {
    // This is called during onboarding. We build in-memory models here.
    // The backend call (update-profile) will create the actual DB records
    // and we'll reload from the backend response afterwards.

    // For now, create a temporary local farm model
    final farmId = 'local_${DateTime.now().millisecondsSinceEpoch}';
    final cropNames = crops ?? [crop];
    final perCropArea = cropAreas != null ? null : (land / cropNames.length);

    final farmCrops = cropNames.map((name) {
      final area = cropAreas != null
          ? (cropAreas[name] ?? 1.0) * 0.4047  // acres to hectares
          : perCropArea!;
      return FarmCropModel(
        id: 'local_${name}_${DateTime.now().millisecondsSinceEpoch}',
        farmId: farmId,
        cropName: name,
        areaHectares: area,
        preferredMandi: nearestMandi,
      );
    }).toList();

    farms = [FarmModel(
      id: farmId,
      userId: farmerId ?? '',
      farmName: 'My Farm',
      totalLandHectares: land,
      soilType: soil,
      irrigationType: irrigation,
      hasStorage: storage,
      crops: farmCrops,
    )];

    activeCrop = farmCrops.first;
    await saveToLocal();
  }

  Future<void> completeOnboarding() async {
    onboardingComplete = true;
    await saveToLocal();
  }

  // ── Cache helpers ──
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

  Map<String, dynamic>? get cachedForecast {
    if (lastForecast == null) return null;
    try { return json.decode(lastForecast!) as Map<String, dynamic>; }
    catch (_) { return null; }
  }

  List<dynamic>? get cachedMandiPrices {
    if (lastMandiPrices == null) return null;
    try { return json.decode(lastMandiPrices!) as List<dynamic>; }
    catch (_) { return null; }
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
    farms = [];
    activeCrop = null;
    lastForecast = null;
    lastMandiPrices = null;
    lastYieldPrediction = null;
    lastSyncTimestamp = null;
    notifyListeners();
  }
}
