import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../providers/farmer_profile_provider.dart';
import '../../theme.dart';
import 'farm_setup_screen.dart';

/// Screen 3: Smart Location Detection
/// Attempts GPS auto-detection. Falls back to manual dropdown.
class LocationScreen extends StatefulWidget {
  const LocationScreen({super.key});

  @override
  State<LocationScreen> createState() => _LocationScreenState();
}

class _LocationScreenState extends State<LocationScreen>
    with SingleTickerProviderStateMixin {
  bool _isDetecting = false;
  bool _detectionDone = false;
  bool _useManual = false;

  String? _detectedState;
  String? _detectedDistrict;
  double? _detectedLat;
  double? _detectedLng;
  String? _detectedMandi;

  // Manual fallback
  String? _manualState;
  String? _manualDistrict;

  late AnimationController _animCtrl;
  late Animation<double> _fadeAnim;

  // Available states and districts
  final Map<String, List<String>> _stateDistricts = {
    'Maharashtra': [
      'Pune', 'Nashik', 'Nagpur', 'Aurangabad', 'Solapur', 'Kolhapur',
      'Sangli', 'Satara', 'Ahmednagar', 'Latur',
    ],
    'Uttar Pradesh': [
      'Lucknow', 'Varanasi', 'Agra', 'Kanpur', 'Allahabad',
      'Meerut', 'Gorakhpur', 'Bareilly',
    ],
    'Madhya Pradesh': [
      'Bhopal', 'Indore', 'Jabalpur', 'Gwalior', 'Ujjain',
      'Sagar', 'Rewa', 'Satna',
    ],
    'Punjab': [
      'Ludhiana', 'Amritsar', 'Jalandhar', 'Patiala', 'Bathinda',
      'Mohali', 'Sangrur', 'Moga',
    ],
    'Rajasthan': [
      'Jaipur', 'Jodhpur', 'Udaipur', 'Kota', 'Ajmer',
      'Bikaner', 'Alwar', 'Sikar',
    ],
    'Karnataka': [
      'Bengaluru', 'Mysuru', 'Hubli', 'Mangaluru', 'Belgaum',
      'Davangere', 'Bellary', 'Shimoga',
    ],
    'Tamil Nadu': [
      'Chennai', 'Madurai', 'Coimbatore', 'Tiruchirappalli', 'Salem',
      'Erode', 'Tirunelveli', 'Thanjavur',
    ],
    'Telangana': [
      'Hyderabad', 'Warangal', 'Nizamabad', 'Karimnagar', 'Khammam',
      'Nalgonda', 'Mahbubnagar', 'Adilabad',
    ],
    'Andhra Pradesh': [
      'Visakhapatnam', 'Vijayawada', 'Guntur', 'Nellore', 'Kurnool',
      'Tirupati', 'Rajahmundry', 'Kakinada',
    ],
    'Gujarat': [
      'Ahmedabad', 'Surat', 'Vadodara', 'Rajkot', 'Bhavnagar',
      'Jamnagar', 'Junagadh', 'Anand',
    ],
    'West Bengal': [
      'Kolkata', 'Howrah', 'Durgapur', 'Siliguri', 'Burdwan',
      'Malda', 'Murshidabad', 'Nadia',
    ],
    'Bihar': [
      'Patna', 'Gaya', 'Muzaffarpur', 'Bhagalpur', 'Darbhanga',
      'Purnia', 'Ara', 'Begusarai',
    ],
    'Odisha': [
      'Bhubaneswar', 'Cuttack', 'Berhampur', 'Sambalpur', 'Rourkela',
      'Balasore', 'Puri', 'Koraput',
    ],
    'Haryana': [
      'Chandigarh', 'Gurugram', 'Faridabad', 'Hisar', 'Karnal',
      'Panipat', 'Ambala', 'Rohtak',
    ],
  };

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
    _animCtrl.dispose();
    super.dispose();
  }

  Future<void> _detectLocation() async {
    setState(() {
      _isDetecting = true;
      _detectionDone = false;
    });

    try {
      // Try using the geolocator package
      // For simplicity and reliability, we attempt a basic detection
      // In a real app, this would use Geolocator.getCurrentPosition()
      // and then reverse geocode with the geocoding package
      
      // Simulated detection for development
      // (Replace with actual geolocator call in production)
      await Future.delayed(const Duration(seconds: 2));

      // Simulated coordinates (Pune, Maharashtra)
      _detectedLat = 18.5204;
      _detectedLng = 73.8567;
      _detectedState = 'Maharashtra';
      _detectedDistrict = 'Pune';
      _detectedMandi = 'Pune Mandi';

      setState(() {
        _detectionDone = true;
        _isDetecting = false;
      });
    } catch (e) {
      setState(() {
        _isDetecting = false;
        _useManual = true;
      });
    }
  }

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
                const SizedBox(height: 32),

                // ── Illustration ──
                Container(
                  width: 80,
                  height: 80,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [Color(0xFF1565C0), Color(0xFF42A5F5)],
                    ),
                    borderRadius: BorderRadius.circular(20),
                    boxShadow: [
                      BoxShadow(
                        color: const Color(0xFF1565C0).withOpacity(0.25),
                        blurRadius: 20,
                        offset: const Offset(0, 8),
                      ),
                    ],
                  ),
                  child: const Icon(Icons.location_on,
                      color: Colors.white, size: 40),
                ),
                const SizedBox(height: 28),

                Text(
                  "Where is your farm?",
                  style: AppTheme.headingLarge.copyWith(fontSize: 24),
                ),
                const SizedBox(height: 6),
                Text(
                  "We'll use this to show prices at your nearest mandi.\nYou only need to do this once.",
                  style: AppTheme.bodyMedium.copyWith(fontSize: 14, height: 1.5),
                ),
                const SizedBox(height: 28),

                // ── AUTO DETECT SECTION ──
                if (!_useManual && !_detectionDone) ...[
                  // Auto detect button
                  SizedBox(
                    height: 56,
                    child: ElevatedButton.icon(
                      onPressed: _isDetecting ? null : _detectLocation,
                      icon: _isDetecting
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(
                                  strokeWidth: 2, color: Colors.white),
                            )
                          : const Icon(Icons.my_location, size: 22),
                      label: Text(
                        _isDetecting
                            ? "Detecting location..."
                            : "Detect My Location Automatically",
                        style: AppTheme.buttonText.copyWith(fontSize: 14),
                      ),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.accentBlue,
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(
                          borderRadius:
                              BorderRadius.circular(AppTheme.buttonRadius),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // Manual fallback link
                  Center(
                    child: TextButton(
                      onPressed: () => setState(() => _useManual = true),
                      child: Text(
                        "Or select manually →",
                        style: AppTheme.bodyMedium.copyWith(
                          color: AppTheme.primaryGreen,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ),
                ],

                // ── DETECTION RESULT ──
                if (_detectionDone) ...[
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius:
                          BorderRadius.circular(AppTheme.cardRadius),
                      border: Border.all(
                          color: AppTheme.primaryGreen, width: 1.5),
                      boxShadow: [
                        BoxShadow(
                          color: AppTheme.primaryGreen.withOpacity(0.1),
                          blurRadius: 12,
                          offset: const Offset(0, 4),
                        ),
                      ],
                    ),
                    child: Column(
                      children: [
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.all(8),
                              decoration: BoxDecoration(
                                color: AppTheme.lightGreen,
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: const Icon(Icons.check_circle,
                                  color: AppTheme.primaryGreen, size: 24),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Text(
                                "Location Detected!",
                                style: AppTheme.headingMedium.copyWith(
                                  fontSize: 16,
                                  color: AppTheme.primaryGreen,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 16),
                        _detailRow(Icons.map, "State", _detectedState ?? ''),
                        _detailRow(Icons.location_city, "District",
                            _detectedDistrict ?? ''),
                        _detailRow(
                            Icons.storefront, "Nearest Mandi",
                            _detectedMandi ?? ''),
                        const SizedBox(height: 8),
                        TextButton.icon(
                          onPressed: () => setState(() {
                            _detectionDone = false;
                            _useManual = true;
                          }),
                          icon: const Icon(Icons.edit, size: 16),
                          label: const Text("Not correct? Select manually"),
                          style: TextButton.styleFrom(
                            foregroundColor: AppTheme.textLight,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 24),
                  _buildContinueButton(),
                ],

                // ── MANUAL SELECTION ──
                if (_useManual) ...[
                  // State dropdown
                  DropdownButtonFormField<String>(
                    value: _manualState,
                    items: _stateDistricts.keys
                        .map((e) =>
                            DropdownMenuItem(value: e, child: Text(e)))
                        .toList(),
                    onChanged: (v) {
                      setState(() {
                        _manualState = v;
                        _manualDistrict = null;
                      });
                    },
                    decoration: AppTheme.inputDecoration(
                        "Select State", Icons.map_outlined),
                  ),
                  const SizedBox(height: 12),

                  // District dropdown
                  if (_manualState != null)
                    DropdownButtonFormField<String>(
                      value: _manualDistrict,
                      items: (_stateDistricts[_manualState] ?? [])
                          .map((e) =>
                              DropdownMenuItem(value: e, child: Text(e)))
                          .toList(),
                      onChanged: (v) =>
                          setState(() => _manualDistrict = v),
                      decoration: AppTheme.inputDecoration(
                          "Select District", Icons.location_city_outlined),
                    ),

                  const SizedBox(height: 16),

                  // Back to auto detect
                  Center(
                    child: TextButton.icon(
                      onPressed: () => setState(() => _useManual = false),
                      icon: const Icon(Icons.my_location, size: 16),
                      label: const Text("Try auto-detect instead"),
                      style: TextButton.styleFrom(
                        foregroundColor: AppTheme.accentBlue,
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),

                  if (_manualDistrict != null) _buildContinueButton(),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _detailRow(IconData icon, String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Icon(icon, color: AppTheme.textLight, size: 18),
          const SizedBox(width: 10),
          Text("$label: ",
              style: AppTheme.bodyMedium.copyWith(fontSize: 13)),
          Text(value,
              style: AppTheme.headingMedium.copyWith(fontSize: 14)),
        ],
      ),
    );
  }

  Widget _buildContinueButton() {
    return SizedBox(
      height: 52,
      child: ElevatedButton(
        onPressed: _onContinue,
        style: ElevatedButton.styleFrom(
          backgroundColor: AppTheme.primaryGreen,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppTheme.buttonRadius),
          ),
          elevation: 2,
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text("Continue", style: AppTheme.buttonText),
            const SizedBox(width: 8),
            const Icon(Icons.arrow_forward, size: 20),
          ],
        ),
      ),
    );
  }

  void _onContinue() async {
    final profile = Provider.of<FarmerProfile>(context, listen: false);

    if (_detectionDone) {
      await profile.setLocation(
        st: _detectedState!,
        dist: _detectedDistrict!,
        lat: _detectedLat,
        lng: _detectedLng,
        mandi: _detectedMandi,
      );
    } else if (_useManual && _manualDistrict != null) {
      await profile.setLocation(
        st: _manualState!,
        dist: _manualDistrict!,
        mandi: '$_manualDistrict Mandi',
      );
    }

    if (mounted) {
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => const FarmSetupScreen()),
      );
    }
  }
}
