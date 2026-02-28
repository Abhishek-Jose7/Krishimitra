import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:http/http.dart' as http;
import 'package:google_fonts/google_fonts.dart';
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
      backgroundColor: const Color(0xFFF9F9F9),
      body: SingleChildScrollView(
        child: Column(
          children: [
            // ── Green Header Section ──
            Container(
              padding: const EdgeInsets.fromLTRB(20, 60, 20, 40),
              width: double.infinity,
              decoration: const BoxDecoration(
                color: Color(0xFF2D6A4F),
                borderRadius: BorderRadius.only(
                  bottomLeft: Radius.circular(32),
                  bottomRight: Radius.circular(32),
                ),
              ),
              child: Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Icon(Icons.arrow_back, color: Colors.white),
                      Row(
                        children: [
                          if (!_isEditing)
                            IconButton(
                              onPressed: () => setState(() => _isEditing = true),
                              icon: const Icon(Icons.edit, color: Colors.white, size: 20),
                            ),
                          const Icon(Icons.more_vert, color: Colors.white),
                        ],
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  Row(
                    children: [
                      Stack(
                        children: [
                          Container(
                            width: 80,
                            height: 80,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              border: Border.all(color: Colors.white, width: 2),
                              image: const DecorationImage(
                                image: NetworkImage('https://images.unsplash.com/photo-1542010589-059798ca8512?w=400&q=80'),
                                fit: BoxFit.cover,
                              ),
                            ),
                          ),
                          Positioned(
                            bottom: 0,
                            left: 0,
                            child: Container(
                              padding: const EdgeInsets.all(4),
                              decoration: const BoxDecoration(
                                color: Colors.white,
                                shape: BoxShape.circle,
                              ),
                              child: const Text("3", style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold)),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              profile.displayName,
                              style: GoogleFonts.dmSans(
                                color: Colors.white,
                                fontSize: 24,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            Text(
                              "Progressive Farmer",
                              style: GoogleFonts.dmSans(
                                color: Colors.white70,
                                fontSize: 14,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),
                  Row(
                    children: [
                      const Icon(Icons.location_on, color: Colors.white, size: 16),
                      const SizedBox(width: 4),
                      Text(
                        "${profile.district ?? 'N/A'}, ${profile.state ?? 'India'}",
                        style: const TextStyle(color: Colors.white),
                      ),
                      const Spacer(),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: const Text(
                          "+ Follow",
                          style: TextStyle(color: Color(0xFF2D6A4F), fontWeight: FontWeight.bold, fontSize: 12),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 32),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                      _statItem(profile.landSize?.toStringAsFixed(1) ?? '0', "HA LAND"),
                      _statItem("1.2K", "FOLLOWING"),
                      _statItem("86", "HEALTH SCORE"),
                    ],
                  ),
                  const SizedBox(height: 32),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                      _iconButton(Icons.map_outlined),
                      _iconButton(Icons.notifications_none),
                      _iconButton(Icons.image_outlined),
                      _iconButton(Icons.nightlight_outlined),
                    ],
                  ),
                ],
              ),
            ),

            // ── White Content Section ──
            Transform.translate(
              offset: const Offset(0, -20),
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.fromLTRB(20, 32, 20, 40),
                decoration: const BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.only(
                    topLeft: Radius.circular(32),
                    topRight: Radius.circular(32),
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    if (!_isEditing) ...[
                      _sectionTitle("Farm Profile"),
                      const SizedBox(height: 16),
                      _infoTile(Icons.grass, "Primary Crop", profile.displayCrops),
                      _infoTile(Icons.storefront, "Preferred Mandi", profile.nearestMandi ?? 'N/A'),
                      _infoTile(Icons.warehouse, "Storage", profile.storageAvailable ? "Available" : "Not Available"),
                      const SizedBox(height: 24),
                      _sectionTitle("Account Settings"),
                      const SizedBox(height: 16),
                      _infoTile(Icons.phone, "Phone Number", profile.phone ?? 'N/A'),
                      _infoTile(Icons.language, "Language", profile.language.toUpperCase()),
                      const SizedBox(height: 32),
                      AppButton(
                        label: "Logout",
                        onPressed: _logout,
                        backgroundColor: Colors.red.shade50,
                        textColor: Colors.red,
                        icon: Icons.logout,
                      ),
                    ],

                    if (_isEditing) ...[
                      _sectionTitle("Edit Profile"),
                      const SizedBox(height: 16),
                      DropdownButtonFormField(
                        value: _editCrop,
                        items: _crops.map((e) => DropdownMenuItem(value: e, child: Text(e))).toList(),
                        onChanged: (v) => setState(() => _editCrop = v),
                        decoration: AppTheme.inputDecoration("Primary Crop", Icons.grass),
                      ),
                      const SizedBox(height: 12),
                      DropdownButtonFormField(
                        value: _editDistrict,
                        items: _districts.map((e) => DropdownMenuItem(value: e, child: Text(e))).toList(),
                        onChanged: (v) => setState(() => _editDistrict = v),
                        decoration: AppTheme.inputDecoration("District", Icons.location_on_outlined),
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: _landController,
                        keyboardType: TextInputType.number,
                        decoration: AppTheme.inputDecoration("Land Size (HA)", Icons.square_foot),
                      ),
                      const SizedBox(height: 24),
                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton(
                              onPressed: () => setState(() => _isEditing = false),
                              style: OutlinedButton.styleFrom(
                                padding: const EdgeInsets.symmetric(vertical: 16),
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                              ),
                              child: const Text("Cancel"),
                            ),
                          ),
                          const SizedBox(width: 16),
                          Expanded(
                            child: AppButton(
                              label: "Save",
                              onPressed: _isSaving ? null : _saveProfile,
                              isLoading: _isSaving,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _statItem(String value, String label) {
    return Column(
      children: [
        Text(
          value,
          style: GoogleFonts.dmSans(
            color: Colors.white,
            fontSize: 20,
            fontWeight: FontWeight.bold,
          ),
        ),
        Text(
          label,
          style: GoogleFonts.dmSans(
            color: Colors.white54,
            fontSize: 10,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }

  Widget _iconButton(IconData icon) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.2),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Icon(icon, color: Colors.white, size: 20),
    );
  }

  Widget _sectionTitle(String title) {
    return Text(
      title,
      style: GoogleFonts.dmSans(
        fontSize: 18,
        fontWeight: FontWeight.bold,
        color: const Color(0xFF2D6A4F),
      ),
    );
  }

  Widget _infoTile(IconData icon, String label, String value) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFFF9F9F9),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        children: [
          Icon(icon, color: const Color(0xFF2D6A4F), size: 20),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: const TextStyle(color: Colors.grey, fontSize: 12)),
                Text(value, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _logout() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text("Logout?"),
        content: const Text("This will clear all saved data."),
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
  }
}
