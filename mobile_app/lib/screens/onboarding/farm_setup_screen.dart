import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:http/http.dart' as http;
import '../../providers/farmer_profile_provider.dart';
import '../../services/api_service.dart';
import '../../theme.dart';
import '../home_screen.dart';

/// Screen 4: Farm Profile Setup
/// Multi-crop with per-crop area + custom crop + auto-inferred storage.
class FarmSetupScreen extends StatefulWidget {
  const FarmSetupScreen({super.key});

  @override
  State<FarmSetupScreen> createState() => _FarmSetupScreenState();
}

class _FarmSetupScreenState extends State<FarmSetupScreen>
    with SingleTickerProviderStateMixin {
  // Per-crop selection with area
  final Map<String, double> _cropAreas = {}; // crop name → area in acres
  final _customCropController = TextEditingController();
  bool _showCustomInput = false;
  bool _showAdvanced = false;
  String? _soilType;
  String? _irrigationType;
  bool _isLoading = false;
  String _areaUnit = 'Acres'; // Acres or Hectares

  late AnimationController _animCtrl;
  late Animation<double> _fadeAnim;

  final List<Map<String, dynamic>> _crops = [
    {'name': 'Rice', 'icon': '🌾', 'color': const Color(0xFF4CAF50), 'perishable': false},
    {'name': 'Wheat', 'icon': '🌿', 'color': const Color(0xFFF9A825), 'perishable': false},
    {'name': 'Maize', 'icon': '🌽', 'color': const Color(0xFFFF9800), 'perishable': false},
    {'name': 'Soybean', 'icon': '🫘', 'color': const Color(0xFF8BC34A), 'perishable': false},
    {'name': 'Cotton', 'icon': '☁️', 'color': const Color(0xFF90A4AE), 'perishable': false},
    {'name': 'Sugarcane', 'icon': '🎋', 'color': const Color(0xFF66BB6A), 'perishable': false},
    {'name': 'Groundnut', 'icon': '🥜', 'color': const Color(0xFFD7A86E), 'perishable': false},
    {'name': 'Onion', 'icon': '🧅', 'color': const Color(0xFFE91E63), 'perishable': true},
    {'name': 'Tomato', 'icon': '🍅', 'color': const Color(0xFFF44336), 'perishable': true},
    {'name': 'Potato', 'icon': '🥔', 'color': const Color(0xFF795548), 'perishable': false},
  ];

  final List<Map<String, dynamic>> _customCrops = [];

  final List<String> _soilTypes = [
    'Alluvial', 'Black / Regur', 'Red & Yellow', 'Laterite',
    'Desert / Sandy', 'Mountain', 'I don\'t know',
  ];

  final List<String> _irrigationTypes = [
    'Rainfed', 'Canal', 'Bore Well', 'Drip', 'Sprinkler', 'Flood',
  ];

  @override
  void initState() {
    super.initState();
    _animCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 600),
    );
    _fadeAnim = CurvedAnimation(parent: _animCtrl, curve: Curves.easeOut);
    _animCtrl.forward();
  }

  @override
  void dispose() {
    _customCropController.dispose();
    _animCtrl.dispose();
    // Dispose controllers for area inputs
    super.dispose();
  }

  List<Map<String, dynamic>> get _allCrops => [..._crops, ..._customCrops];

  bool _isPerishable(String cropName) {
    final crop = _allCrops.firstWhere(
        (c) => c['name'] == cropName,
        orElse: () => {'perishable': false});
    return crop['perishable'] == true;
  }

  // Auto-infer storage based on selected crops
  bool get _autoStorage {
    if (_cropAreas.isEmpty) return false;
    // If ALL crops are perishable → no storage needed (can't store)
    // If ANY crop is storable → storage helps
    return _cropAreas.keys.any((crop) => !_isPerishable(crop));
  }

  void _toggleCrop(String name) {
    setState(() {
      if (_cropAreas.containsKey(name)) {
        _cropAreas.remove(name);
      } else {
        _cropAreas[name] = 1.0; // Default 1 acre
      }
    });
  }

  void _addCustomCrop() {
    final name = _customCropController.text.trim();
    if (name.isEmpty) return;

    final exists = _allCrops.any(
        (c) => (c['name'] as String).toLowerCase() == name.toLowerCase());
    if (exists) {
      final existingName = _allCrops.firstWhere(
          (c) => (c['name'] as String).toLowerCase() == name.toLowerCase())['name'];
      setState(() {
        if (!_cropAreas.containsKey(existingName)) _cropAreas[existingName] = 1.0;
        _customCropController.clear();
        _showCustomInput = false;
      });
      return;
    }

    final capitalized = name[0].toUpperCase() + name.substring(1);
    setState(() {
      _customCrops.add({
        'name': capitalized,
        'icon': '🌱',
        'color': const Color(0xFF78909C),
        'perishable': false,
      });
      _cropAreas[capitalized] = 1.0;
      _customCropController.clear();
      _showCustomInput = false;
    });
  }

  double get _totalArea => _cropAreas.values.fold(0, (a, b) => a + b);
  double _toHectares(double acres) => acres * 0.4047;
  double _fromHectares(double hectares) => hectares / 0.4047;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      body: SafeArea(
        child: FadeTransition(
          opacity: _fadeAnim,
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const SizedBox(height: 24),

                // ── Progress indicator: Step 4/4 ──
                Row(
                  children: List.generate(4, (i) {
                    return Expanded(
                      child: Container(
                        height: 4,
                        margin: const EdgeInsets.symmetric(horizontal: 2),
                        decoration: BoxDecoration(
                          color: AppTheme.primaryGreen,
                          borderRadius: BorderRadius.circular(2),
                        ),
                      ),
                    );
                  }),
                ),
                const SizedBox(height: 28),

                // ── Header ──
                Container(
                  width: 72, height: 72,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [Color(0xFFE65100), Color(0xFFFF9800)],
                    ),
                    borderRadius: BorderRadius.circular(18),
                    boxShadow: [
                      BoxShadow(
                        color: const Color(0xFFE65100).withOpacity(0.25),
                        blurRadius: 20,
                        offset: const Offset(0, 8),
                      ),
                    ],
                  ),
                  child: const Icon(Icons.agriculture, color: Colors.white, size: 36),
                ),
                const SizedBox(height: 20),
                Text("Tell us about your farm",
                    style: AppTheme.headingLarge.copyWith(fontSize: 24)),
                const SizedBox(height: 4),
                Text("Just a few quick questions. You won't need to answer these again.",
                    style: AppTheme.bodyMedium.copyWith(fontSize: 14, height: 1.4)),
                const SizedBox(height: 28),

                // ═══════════════════════════
                // Q1: CROPS (MULTI-SELECT)
                // ═══════════════════════════
                Row(
                  children: [
                    Expanded(
                      child: Text("① What crops do you grow?",
                          style: AppTheme.headingMedium.copyWith(fontSize: 15)),
                    ),
                    if (_cropAreas.isNotEmpty)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: AppTheme.primaryGreen,
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Text("${_cropAreas.length} selected",
                            style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w600)),
                      ),
                  ],
                ),
                const SizedBox(height: 4),
                Text("Select all that apply. You can set area for each below.",
                    style: AppTheme.bodyMedium.copyWith(fontSize: 12, color: Colors.grey)),
                const SizedBox(height: 10),

                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    ..._allCrops.map((crop) {
                      final isSelected = _cropAreas.containsKey(crop['name']);
                      return GestureDetector(
                        onTap: () => _toggleCrop(crop['name']),
                        child: AnimatedContainer(
                          duration: const Duration(milliseconds: 200),
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                          decoration: BoxDecoration(
                            color: isSelected ? (crop['color'] as Color) : Colors.white,
                            borderRadius: BorderRadius.circular(AppTheme.chipRadius),
                            border: Border.all(
                              color: isSelected ? (crop['color'] as Color) : Colors.grey.shade300,
                              width: isSelected ? 2 : 1,
                            ),
                            boxShadow: isSelected
                                ? [BoxShadow(color: (crop['color'] as Color).withOpacity(0.25), blurRadius: 8, offset: const Offset(0, 2))]
                                : [],
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(crop['icon'], style: const TextStyle(fontSize: 18)),
                              const SizedBox(width: 6),
                              Text(crop['name'], style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600,
                                  color: isSelected ? Colors.white : AppTheme.textDark)),
                              if (isSelected) ...[
                                const SizedBox(width: 4),
                                const Icon(Icons.check_circle, color: Colors.white, size: 16),
                              ],
                            ],
                          ),
                        ),
                      );
                    }),

                    // "Other crop" button
                    GestureDetector(
                      onTap: () => setState(() => _showCustomInput = !_showCustomInput),
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 200),
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                        decoration: BoxDecoration(
                          color: _showCustomInput ? AppTheme.accentBlue.withOpacity(0.1) : Colors.white,
                          borderRadius: BorderRadius.circular(AppTheme.chipRadius),
                          border: Border.all(
                            color: _showCustomInput ? AppTheme.accentBlue : Colors.grey.shade300,
                          ),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(_showCustomInput ? Icons.close : Icons.add, size: 16,
                                color: _showCustomInput ? AppTheme.accentBlue : AppTheme.textLight),
                            const SizedBox(width: 4),
                            Text(_showCustomInput ? "Cancel" : "Other crop",
                                style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600,
                                    color: _showCustomInput ? AppTheme.accentBlue : AppTheme.textLight)),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),

                // Custom crop input
                if (_showCustomInput) ...[
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _customCropController,
                          textCapitalization: TextCapitalization.words,
                          style: AppTheme.bodyMedium.copyWith(fontSize: 14),
                          decoration: InputDecoration(
                            hintText: "Enter crop name",
                            hintStyle: TextStyle(color: Colors.grey.shade400, fontSize: 14),
                            filled: true, fillColor: Colors.white,
                            prefixIcon: const Icon(Icons.eco, color: AppTheme.primaryGreen, size: 20),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(AppTheme.inputRadius),
                                borderSide: BorderSide(color: Colors.grey.shade300)),
                            focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(AppTheme.inputRadius),
                                borderSide: const BorderSide(color: AppTheme.primaryGreen, width: 2)),
                            contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
                          ),
                          onSubmitted: (_) => _addCustomCrop(),
                        ),
                      ),
                      const SizedBox(width: 8),
                      SizedBox(
                        height: 48,
                        child: ElevatedButton(
                          onPressed: _addCustomCrop,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppTheme.primaryGreen,
                            foregroundColor: Colors.white,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.inputRadius)),
                            padding: const EdgeInsets.symmetric(horizontal: 16),
                          ),
                          child: const Text("Add", style: TextStyle(fontWeight: FontWeight.w600)),
                        ),
                      ),
                    ],
                  ),
                ],

                const SizedBox(height: 20),

                // ═══════════════════════════
                // Q2: PER-CROP AREA
                // ═══════════════════════════
                if (_cropAreas.isNotEmpty) ...[
                  Row(
                    children: [
                      Expanded(
                        child: Text("② How much land for each crop?",
                            style: AppTheme.headingMedium.copyWith(fontSize: 15)),
                      ),
                      // Unit toggle
                      GestureDetector(
                        onTap: () => setState(() => _areaUnit = _areaUnit == 'Acres' ? 'Hectares' : 'Acres'),
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                          decoration: BoxDecoration(
                            color: AppTheme.lightGreen,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Text(_areaUnit, style: AppTheme.bodyMedium.copyWith(
                              color: AppTheme.primaryGreen, fontWeight: FontWeight.w600, fontSize: 12)),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  ..._cropAreas.entries.map((entry) {
                    final crop = _allCrops.firstWhere(
                        (c) => c['name'] == entry.key,
                        orElse: () => {'name': entry.key, 'icon': '🌱', 'color': Colors.grey});
                    return Container(
                      margin: const EdgeInsets.only(bottom: 8),
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(AppTheme.cardRadius),
                        border: Border.all(color: Colors.grey.shade200),
                      ),
                      child: Row(
                        children: [
                          Text(crop['icon'] ?? '🌱', style: const TextStyle(fontSize: 20)),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(entry.key, style: AppTheme.headingMedium.copyWith(fontSize: 13)),
                                if (_isPerishable(entry.key))
                                  Text("⚡ Perishable — sell quickly",
                                      style: AppTheme.bodyMedium.copyWith(fontSize: 10, color: AppTheme.accentOrange)),
                              ],
                            ),
                          ),
                          SizedBox(
                            width: 70,
                            child: TextField(
                              keyboardType: const TextInputType.numberWithOptions(decimal: true),
                              style: AppTheme.headingMedium.copyWith(fontSize: 16),
                              textAlign: TextAlign.center,
                              decoration: InputDecoration(
                                hintText: "1",
                                contentPadding: const EdgeInsets.symmetric(vertical: 8, horizontal: 6),
                                border: OutlineInputBorder(
                                    borderRadius: BorderRadius.circular(8),
                                    borderSide: BorderSide(color: Colors.grey.shade300)),
                                focusedBorder: OutlineInputBorder(
                                    borderRadius: BorderRadius.circular(8),
                                    borderSide: const BorderSide(color: AppTheme.primaryGreen, width: 2)),
                                isDense: true,
                              ),
                              controller: TextEditingController(text: entry.value.toStringAsFixed(entry.value == entry.value.roundToDouble() ? 0 : 1)),
                              onChanged: (v) {
                                final val = double.tryParse(v);
                                if (val != null && val > 0) {
                                  _cropAreas[entry.key] = val;
                                }
                              },
                            ),
                          ),
                          const SizedBox(width: 6),
                          Text(_areaUnit == 'Acres' ? 'ac' : 'ha',
                              style: AppTheme.bodyMedium.copyWith(fontSize: 12, color: AppTheme.textLight)),
                        ],
                      ),
                    );
                  }),

                  // Total area summary
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    decoration: BoxDecoration(
                      color: AppTheme.lightGreen,
                      borderRadius: BorderRadius.circular(AppTheme.cardRadius),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text("Total", style: AppTheme.headingMedium.copyWith(fontSize: 13, color: AppTheme.primaryGreen)),
                        Text(
                          _areaUnit == 'Acres'
                              ? "${_totalArea.toStringAsFixed(1)} acres (~${_toHectares(_totalArea).toStringAsFixed(1)} ha)"
                              : "${_totalArea.toStringAsFixed(1)} ha (~${_fromHectares(_totalArea).toStringAsFixed(1)} acres)",
                          style: AppTheme.headingMedium.copyWith(fontSize: 13, color: AppTheme.primaryGreen),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 8),

                  // Storage auto-inference
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: _autoStorage ? const Color(0xFFE8F5E9) : const Color(0xFFFFF3E0),
                      borderRadius: BorderRadius.circular(AppTheme.cardRadius),
                      border: Border.all(color: _autoStorage ? AppTheme.primaryGreen.withOpacity(0.3) : AppTheme.accentOrange.withOpacity(0.3)),
                    ),
                    child: Row(
                      children: [
                        Icon(_autoStorage ? Icons.warehouse : Icons.local_shipping,
                            color: _autoStorage ? AppTheme.primaryGreen : AppTheme.accentOrange, size: 20),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                _autoStorage ? "Storage recommended" : "Quick sell crops",
                                style: AppTheme.headingMedium.copyWith(fontSize: 12,
                                    color: _autoStorage ? AppTheme.primaryGreen : AppTheme.accentOrange),
                              ),
                              Text(
                                _autoStorage
                                    ? "Grains like ${_cropAreas.keys.where((c) => !_isPerishable(c)).join(', ')} can be stored for better prices"
                                    : "Perishable crops need quick selling — we'll prioritize mandi timing",
                                style: AppTheme.bodyMedium.copyWith(fontSize: 10),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
                const SizedBox(height: 24),

                // ═══════════════════════════
                // ADVANCED SETUP (Optional)
                // ═══════════════════════════
                GestureDetector(
                  onTap: () => setState(() => _showAdvanced = !_showAdvanced),
                  child: Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(AppTheme.cardRadius),
                      border: Border.all(color: Colors.grey.shade200),
                    ),
                    child: Row(
                      children: [
                        Icon(_showAdvanced ? Icons.expand_less : Icons.expand_more,
                            color: AppTheme.textLight, size: 20),
                        const SizedBox(width: 8),
                        Text("Advanced Setup (Optional)",
                            style: AppTheme.bodyMedium.copyWith(fontSize: 13, fontWeight: FontWeight.w500)),
                      ],
                    ),
                  ),
                ),

                if (_showAdvanced) ...[
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    value: _soilType,
                    items: _soilTypes.map((e) => DropdownMenuItem(value: e, child: Text(e))).toList(),
                    onChanged: (v) => setState(() => _soilType = v),
                    decoration: AppTheme.inputDecoration("Soil Type", Icons.terrain),
                  ),
                  const SizedBox(height: 10),
                  DropdownButtonFormField<String>(
                    value: _irrigationType,
                    items: _irrigationTypes.map((e) => DropdownMenuItem(value: e, child: Text(e))).toList(),
                    onChanged: (v) => setState(() => _irrigationType = v),
                    decoration: AppTheme.inputDecoration("Irrigation Type", Icons.water),
                  ),
                ],

                const SizedBox(height: 28),

                // ═══════════════════════════
                // SUBMIT
                // ═══════════════════════════
                SizedBox(
                  height: 54,
                  child: ElevatedButton(
                    onPressed: _canSubmit() && !_isLoading ? _onSubmit : null,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.primaryGreen,
                      foregroundColor: Colors.white,
                      disabledBackgroundColor: Colors.grey.shade300,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.buttonRadius)),
                      elevation: 2,
                    ),
                    child: _isLoading
                        ? const SizedBox(width: 22, height: 22,
                            child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                        : Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const Icon(Icons.check_circle, size: 22),
                              const SizedBox(width: 8),
                              Text("Start Using KrishiMitra", style: AppTheme.buttonText),
                            ],
                          ),
                  ),
                ),
                const SizedBox(height: 20),
              ],
            ),
          ),
        ),
      ),
    );
  }

  bool _canSubmit() {
    return _cropAreas.isNotEmpty && _totalArea > 0;
  }

  Future<void> _onSubmit() async {
    setState(() => _isLoading = true);

    final profile = Provider.of<FarmerProfile>(context, listen: false);
    final cropsList = _cropAreas.keys.toList();
    final primaryCrop = cropsList.first;

    // Convert all areas to hectares
    final cropsPayload = <Map<String, dynamic>>[];
    for (final entry in _cropAreas.entries) {
      final areaInAcres = _areaUnit == 'Acres' ? entry.value : _fromHectares(entry.value);
      final areaHectares = areaInAcres * 0.4047;
      cropsPayload.add({
        'crop_name': entry.key,
        'area_hectares': areaHectares,
        'preferred_mandi': profile.nearestMandi,
      });
    }

    final totalHa = cropsPayload.fold<double>(0, (sum, c) => sum + (c['area_hectares'] as double));

    // Save locally first (with temporary IDs)
    await profile.setFarmProfile(
      crop: primaryCrop,
      crops: cropsList,
      land: totalHa,
      storage: _autoStorage,
      soil: _soilType,
      irrigation: _irrigationType,
      cropAreas: _cropAreas,
    );
    await profile.completeOnboarding();

    // Sync to backend — send structured payload
    try {
      final response = await http.post(
        Uri.parse('${ApiService.baseUrl}/auth/update-profile'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'farmer_id': profile.farmerId,
          'language': profile.language,
          'state': profile.state,
          'district': profile.district,
          'latitude': profile.latitude,
          'longitude': profile.longitude,
          'onboarding_complete': true,
          // Structured farm + crops payload
          'farm': {
            'farm_name': 'My Farm',
            'soil_type': _soilType,
            'irrigation_type': _irrigationType,
            'has_storage': _autoStorage,
          },
          'crops': cropsPayload,
          'preferred_mandi': profile.nearestMandi,
        }),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        // Reload farms from backend (they now have real IDs)
        if (data['farms'] != null && (data['farms'] as List).isNotEmpty) {
          profile.loadFarmsFromJson(data['farms'] as List<dynamic>);
          await profile.saveToLocal();
        }
      }
    } catch (_) {}

    if (mounted) {
      Navigator.pushAndRemoveUntil(context,
          MaterialPageRoute(builder: (_) => const HomeScreen()), (route) => false);
    }
  }
}
