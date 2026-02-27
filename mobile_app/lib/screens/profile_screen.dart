import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:http/http.dart' as http;
import '../providers/farmer_profile_provider.dart';
import '../services/api_service.dart';
import '../theme.dart';
import '../widgets/app_button.dart';
import 'onboarding/language_screen.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  bool _isEditing = false;
  bool _isSaving = false;
  bool _showFeedback = false;

  // Edit controllers — initialized from stored profile
  final _landController = TextEditingController();
  final _actualYieldController = TextEditingController();
  String? _editCrop;
  String? _editDistrict;
  String? _editMandi;
  bool _editStorage = false;

  final List<String> _crops = ['Rice', 'Wheat', 'Maize', 'Soybean', 'Cotton', 'Sugarcane', 'Groundnut', 'Onion'];
  final List<String> _districts = [
    'Pune', 'Nashik', 'Nagpur', 'Aurangabad', 'Solapur',
    'Lucknow', 'Varanasi', 'Agra',
    'Bhopal', 'Indore',
    'Ludhiana', 'Amritsar',
    'Jaipur', 'Jodhpur',
    'Bengaluru', 'Mysuru',
    'Chennai', 'Madurai',
    'Hyderabad', 'Warangal',
  ];
  final List<String> _mandis = [
    'Pune Mandi', 'Nashik Mandi', 'Nagpur Mandi', 'Aurangabad Mandi',
    'Lucknow Mandi', 'Varanasi Mandi', 'Bhopal Mandi', 'Indore Mandi',
    'Ludhiana Mandi', 'Amritsar Mandi', 'Jaipur Mandi', 'Bengaluru Mandi',
    'Chennai Mandi', 'Hyderabad Mandi',
  ];

  @override
  void initState() {
    super.initState();
    _loadFromProfile();
  }

  void _loadFromProfile() {
    final profile = Provider.of<FarmerProfile>(context, listen: false);
    _landController.text = (profile.landSize ?? 2.0).toString();
    _editCrop = profile.primaryCrop ?? 'Rice';
    _editDistrict = profile.district ?? 'Pune';
    _editMandi = profile.nearestMandi ?? 'Pune Mandi';
    _editStorage = profile.storageAvailable;

    // Ensure dropdown values exist in lists
    if (!_crops.contains(_editCrop)) _editCrop = 'Rice';
    if (!_districts.contains(_editDistrict)) _editDistrict = 'Pune';
    if (!_mandis.contains(_editMandi)) _editMandi = 'Pune Mandi';
  }

  Future<void> _saveProfile() async {
    setState(() => _isSaving = true);
    final profile = Provider.of<FarmerProfile>(context, listen: false);
    final landSize = double.tryParse(_landController.text) ?? 2.0;

    // Update local profile
    await profile.setFarmProfile(
      crop: _editCrop!,
      land: landSize,
      storage: _editStorage,
    );

    if (_editDistrict != null) {
      await profile.setLocation(
        st: profile.state ?? 'Maharashtra',
        dist: _editDistrict!,
        lat: profile.latitude,
        lng: profile.longitude,
        mandi: _editMandi,
      );
    }

    // Sync to backend (best effort)
    try {
      await http.post(
        Uri.parse('${ApiService.baseUrl}/auth/update-profile'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'farmer_id': profile.farmerId,
          'primary_crop': _editCrop,
          'district': _editDistrict,
          'preferred_mandi': _editMandi,
          'land_size': landSize,
          'storage_available': _editStorage,
        }),
      );
    } catch (_) {}

    if (mounted) {
      setState(() {
        _isSaving = false;
        _isEditing = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text("Profile Updated! ✅"),
          backgroundColor: AppTheme.primaryGreen,
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(2)),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final profile = Provider.of<FarmerProfile>(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text("My Profile"),
        actions: [
          if (!_isEditing)
            TextButton.icon(
              onPressed: () => setState(() => _isEditing = true),
              icon: const Icon(Icons.edit, color: Colors.white, size: 18),
              label: const Text("Edit",
                  style: TextStyle(color: Colors.white, fontSize: 13)),
            ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // ── Profile Summary Card ──
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [AppTheme.primaryGreen, AppTheme.secondaryGreen],
                ),
                borderRadius: BorderRadius.circular(AppTheme.cardRadius),
              ),
              child: Column(
                children: [
                  Container(
                    width: 64,
                    height: 64,
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: const Icon(Icons.person, size: 32, color: Colors.white),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    profile.displayName,
                    style: AppTheme.headingMedium.copyWith(
                        color: Colors.white, fontSize: 18),
                  ),
                  Text(
                    profile.phone ?? '',
                    style: AppTheme.bodyMedium.copyWith(
                        color: Colors.white70, fontSize: 13),
                  ),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      "${profile.displayCrops} · ${profile.district ?? 'N/A'} · ${profile.landSize?.toStringAsFixed(1) ?? '0'} ha",
                      style: const TextStyle(color: Colors.white, fontSize: 11),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // ── Profile Details ──
            if (!_isEditing) ...[
              _infoTile(Icons.grass, "Crops", profile.displayCrops),
              _infoTile(Icons.location_on, "District", profile.district ?? 'N/A'),
              _infoTile(Icons.storefront, "Nearest Mandi", profile.nearestMandi ?? 'N/A'),
              _infoTile(Icons.square_foot, "Land Size", "${profile.landSize?.toStringAsFixed(1) ?? '0'} hectares (~${((profile.landSize ?? 0) / 0.4047).toStringAsFixed(0)} acres)"),
              _infoTile(Icons.warehouse, "Storage", profile.storageAvailable ? "Available" : "Not Available"),
              _infoTile(Icons.map, "State", profile.state ?? 'N/A'),
              _infoTile(Icons.language, "Language", profile.language.toUpperCase()),
              if (profile.soilType != null) _infoTile(Icons.terrain, "Soil Type", profile.soilType!),
              if (profile.irrigationType != null) _infoTile(Icons.water, "Irrigation", profile.irrigationType!),
            ],

            // ── Edit Mode ──
            if (_isEditing) ...[
              Text("Edit Farm Profile",
                  style: AppTheme.headingMedium.copyWith(fontSize: 16)),
              const SizedBox(height: 4),
              Text("Changes will be saved permanently.",
                  style: AppTheme.bodyMedium.copyWith(fontSize: 12)),
              const SizedBox(height: 16),

              DropdownButtonFormField(
                value: _editCrop,
                items: _crops.map((e) => DropdownMenuItem(value: e, child: Text(e))).toList(),
                onChanged: (v) => setState(() => _editCrop = v),
                decoration: AppTheme.inputDecoration("Primary Crop", Icons.grass),
              ),
              const SizedBox(height: 10),

              DropdownButtonFormField(
                value: _editDistrict,
                items: _districts.map((e) => DropdownMenuItem(value: e, child: Text(e))).toList(),
                onChanged: (v) => setState(() => _editDistrict = v),
                decoration: AppTheme.inputDecoration("District", Icons.location_on_outlined),
              ),
              const SizedBox(height: 10),

              DropdownButtonFormField(
                value: _editMandi,
                items: _mandis.map((e) => DropdownMenuItem(value: e, child: Text(e))).toList(),
                onChanged: (v) => setState(() => _editMandi = v),
                decoration: AppTheme.inputDecoration("Nearest Mandi", Icons.storefront),
              ),
              const SizedBox(height: 10),

              TextFormField(
                controller: _landController,
                keyboardType: TextInputType.number,
                decoration: AppTheme.inputDecoration("Land Size (Hectares)", Icons.square_foot),
              ),
              const SizedBox(height: 10),

              SwitchListTile(
                title: Text("Storage Available", style: AppTheme.bodyLarge.copyWith(fontSize: 14)),
                subtitle: Text("Can you store crop after harvest?", style: AppTheme.bodyMedium.copyWith(fontSize: 12)),
                value: _editStorage,
                onChanged: (v) => setState(() => _editStorage = v),
                activeColor: AppTheme.primaryGreen,
                contentPadding: EdgeInsets.zero,
              ),

              const SizedBox(height: 20),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: () {
                        _loadFromProfile();
                        setState(() => _isEditing = false);
                      },
                      style: OutlinedButton.styleFrom(
                        foregroundColor: AppTheme.textLight,
                        side: BorderSide(color: Colors.grey.shade300),
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(AppTheme.buttonRadius),
                        ),
                      ),
                      child: const Text("Cancel"),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: AppButton(
                      label: "Save Changes",
                      onPressed: _isSaving ? null : _saveProfile,
                      isLoading: _isSaving,
                      icon: Icons.save,
                    ),
                  ),
                ],
              ),
            ],

            // ── Post-Harvest Feedback ──
            const SizedBox(height: 28),
            GestureDetector(
              onTap: () => setState(() => _showFeedback = !_showFeedback),
              child: Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: AppTheme.lightGreen,
                  borderRadius: BorderRadius.circular(AppTheme.cardRadius),
                  border: Border.all(color: AppTheme.primaryGreen.withOpacity(0.2)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.feedback_outlined, color: AppTheme.primaryGreen, size: 20),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text("After Harvest?", style: AppTheme.headingMedium.copyWith(fontSize: 13)),
                          Text("Tell us actual yield to improve predictions", style: AppTheme.bodyMedium.copyWith(fontSize: 11)),
                        ],
                      ),
                    ),
                    Icon(_showFeedback ? Icons.expand_less : Icons.expand_more, color: AppTheme.primaryGreen),
                  ],
                ),
              ),
            ),

            if (_showFeedback) ...[
              const SizedBox(height: 10),
              TextFormField(
                controller: _actualYieldController,
                keyboardType: TextInputType.number,
                decoration: AppTheme.inputDecoration("Actual Production (Tons)", Icons.agriculture),
              ),
              const SizedBox(height: 10),
              AppButton(
                label: "Submit Feedback",
                onPressed: () async {
                  final value = double.tryParse(_actualYieldController.text);
                  if (value == null || value <= 0) return;
                  try {
                    final api = Provider.of<ApiService>(context, listen: false);
                    await api.submitActualYield(value);
                    if (mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: const Text("Thank you! This helps improve predictions. 🙏"),
                          backgroundColor: AppTheme.primaryGreen,
                          behavior: SnackBarBehavior.floating,
                        ),
                      );
                      setState(() => _showFeedback = false);
                    }
                  } catch (e) {
                    if (mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Error: $e")));
                    }
                  }
                },
                icon: Icons.send,
              ),
            ],

            // ── Logout ──
            const SizedBox(height: 32),
            Center(
              child: TextButton.icon(
                onPressed: () async {
                  final confirm = await showDialog<bool>(
                    context: context,
                    builder: (ctx) => AlertDialog(
                      title: const Text("Logout?"),
                      content: const Text("This will clear all saved data. You'll need to set up again."),
                      actions: [
                        TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text("Cancel")),
                        TextButton(
                          onPressed: () => Navigator.pop(ctx, true),
                          child: const Text("Logout", style: TextStyle(color: Colors.red)),
                        ),
                      ],
                    ),
                  );
                  if (confirm == true && mounted) {
                    final profile = Provider.of<FarmerProfile>(context, listen: false);
                    await profile.clearAll();
                    if (mounted) {
                      Navigator.pushAndRemoveUntil(
                        context,
                        MaterialPageRoute(builder: (_) => const LanguageScreen()),
                        (route) => false,
                      );
                    }
                  }
                },
                icon: const Icon(Icons.logout, color: AppTheme.error, size: 18),
                label: Text("Logout & Reset",
                    style: AppTheme.bodyMedium.copyWith(color: AppTheme.error, fontWeight: FontWeight.w600)),
              ),
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }

  Widget _infoTile(IconData icon, String label, String value) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(AppTheme.cardRadius),
        border: Border.all(color: AppTheme.cardBorder),
      ),
      child: Row(
        children: [
          Icon(icon, color: AppTheme.primaryGreen, size: 20),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: AppTheme.bodyMedium.copyWith(fontSize: 11)),
                Text(value, style: AppTheme.headingMedium.copyWith(fontSize: 14)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
