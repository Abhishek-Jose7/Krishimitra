import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/farmer_profile_provider.dart';
import '../services/api_service.dart';
import '../theme.dart';

class MandiScreen extends StatefulWidget {
  const MandiScreen({super.key});

  @override
  State<MandiScreen> createState() => _MandiScreenState();
}

class _MandiScreenState extends State<MandiScreen> {
  List<dynamic> _mandis = [];
  bool _isLoading = true;
  String _selectedCrop = 'Rice';

  List<String> _crops = ['Rice', 'Wheat', 'Maize', 'Soybean'];

  static const Map<String, String> cropEmojis = {
    'Rice': '🌾', 'Wheat': '🌿', 'Maize': '🌽', 'Soybean': '🫘',
    'Cotton': '☁️', 'Sugarcane': '🎋', 'Groundnut': '🥜', 'Onion': '🧅',
    'Tomato': '🍅', 'Potato': '🥔',
  };

  @override
  void initState() {
    super.initState();
    final profile = Provider.of<FarmerProfile>(context, listen: false);
    _selectedCrop = profile.primaryCrop ?? 'Rice';
    // Use farmer's crops if available
    if (profile.crops.isNotEmpty) {
      _crops = profile.crops;
    }
    _loadPrices();
  }

  Future<void> _loadPrices() async {
    setState(() => _isLoading = true);
    try {
      final profile = Provider.of<FarmerProfile>(context, listen: false);
      final api = Provider.of<ApiService>(context, listen: false);
      final mandis = await api.getMandiPrices(_selectedCrop, district: profile.district ?? 'Pune');
      setState(() {
        _mandis = mandis;
        _isLoading = false;
      });
    } catch (e) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  // Estimate travel time from distance (assume 30 km/h for rural roads)
  String _estimateTravelTime(double distanceKm) {
    final minutes = (distanceKm / 30 * 60).round();
    if (minutes < 60) return '$minutes min drive';
    final hours = minutes ~/ 60;
    final remainingMin = minutes % 60;
    if (remainingMin == 0) return '$hours hr drive';
    return '${hours}h ${remainingMin}m drive';
  }

  // Simulate arrival volume risk per mandi
  Map<String, dynamic> _getMandiRisk(Map<String, dynamic> mandi) {
    final arrival = (mandi['arrival_volume'] ?? 'normal').toString().toLowerCase();
    final priceChange = (mandi['price_change'] ?? 0).toDouble();

    if (arrival == 'high' || priceChange < -30) {
      return {'level': 'HIGH', 'message': 'High arrival today — price may drop', 'color': AppTheme.error, 'icon': Icons.warning_amber_rounded};
    } else if (arrival == 'medium' || priceChange < -10) {
      return {'level': 'MEDIUM', 'message': 'Moderate arrivals', 'color': AppTheme.accentOrange, 'icon': Icons.info_outline};
    }
    return {'level': 'LOW', 'message': 'Normal arrivals', 'color': AppTheme.primaryGreen, 'icon': Icons.check_circle_outline};
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Nearby Mandi Prices")),
      body: Column(
        children: [
          // Crop selector
          Container(
            height: 64,
            color: AppTheme.surface,
            padding: const EdgeInsets.symmetric(vertical: 10),
            child: ListView.builder(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 12),
              itemCount: _crops.length,
              itemBuilder: (context, index) {
                final crop = _crops[index];
                final isSelected = crop == _selectedCrop;
                return GestureDetector(
                  onTap: () {
                    setState(() => _selectedCrop = crop);
                    _loadPrices();
                  },
                  child: Container(
                    margin: const EdgeInsets.only(right: 10),
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    decoration: BoxDecoration(
                      color: isSelected ? AppTheme.primaryGreen : AppTheme.background,
                      borderRadius: BorderRadius.circular(AppTheme.chipRadius),
                      border: Border.all(
                        color: isSelected ? AppTheme.primaryGreen : Colors.grey.shade300,
                        width: isSelected ? 2 : 1,
                      ),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(cropEmojis[crop] ?? '🌱', style: const TextStyle(fontSize: 18)),
                        const SizedBox(width: 6),
                        Text(crop, style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600,
                            color: isSelected ? Colors.white : AppTheme.textDark)),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
          Divider(height: 1, color: Colors.grey.shade300),

          // Mandi list
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator(color: AppTheme.primaryGreen))
                : RefreshIndicator(
                    onRefresh: _loadPrices,
                    color: AppTheme.primaryGreen,
                    child: ListView.builder(
                      padding: const EdgeInsets.all(12),
                      itemCount: _mandis.length,
                      itemBuilder: (context, index) {
                        final mandi = _mandis[index];
                        return _buildMandiCard(mandi, index);
                      },
                    ),
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildMandiCard(Map<String, dynamic> mandi, int index) {
    final isBest = index == 0;
    final priceChange = (mandi['price_change'] ?? 0).toDouble();
    final isUp = priceChange >= 0;
    final distanceKm = (mandi['distance_km'] ?? 0).toDouble();
    final netPrice = (mandi['effective_price'] ?? mandi['today_price'] ?? 0).toDouble();
    final rawPrice = (mandi['today_price'] ?? 0).toDouble();
    final transportCost = (mandi['transport_cost'] ?? 0).toDouble();
    final mandiRisk = _getMandiRisk(mandi);

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(AppTheme.cardRadius),
        border: Border.all(
          color: isBest ? AppTheme.primaryGreen : Colors.grey.shade200,
          width: isBest ? 2 : 1,
        ),
        boxShadow: isBest ? [BoxShadow(color: AppTheme.primaryGreen.withOpacity(0.1), blurRadius: 8, offset: const Offset(0, 2))] : [],
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Mandi name + details
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          if (isBest)
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              margin: const EdgeInsets.only(right: 6),
                              decoration: BoxDecoration(
                                color: AppTheme.primaryGreen,
                                borderRadius: BorderRadius.circular(2),
                              ),
                              child: const Text("BEST",
                                  style: TextStyle(color: Colors.white, fontSize: 9, fontWeight: FontWeight.bold)),
                            ),
                          Expanded(
                            child: Text(mandi['mandi'] ?? '',
                                style: AppTheme.headingMedium.copyWith(fontSize: 15),
                                overflow: TextOverflow.ellipsis),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      // Tags row — distance + travel time
                      Row(
                        children: [
                          _tag(Icons.location_on, "${distanceKm.toStringAsFixed(0)} km", Colors.grey.shade600),
                          const SizedBox(width: 6),
                          _tag(Icons.directions_car, _estimateTravelTime(distanceKm), Colors.grey.shade600),
                          const SizedBox(width: 6),
                          _tag(Icons.local_shipping, "-₹${transportCost.toStringAsFixed(0)}", Colors.grey.shade600),
                        ],
                      ),
                    ],
                  ),
                ),

                const SizedBox(width: 10),

                // Price column — NET price is primary, raw is secondary
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    // NET price — large and primary
                    Text("₹${netPrice.toStringAsFixed(0)}",
                        style: AppTheme.headingLarge.copyWith(
                          color: isBest ? AppTheme.primaryGreen : AppTheme.textDark,
                          fontSize: 24, fontWeight: FontWeight.w800)),
                    Text("Net / Quintal", style: AppTheme.bodyMedium.copyWith(fontSize: 10, color: AppTheme.textLight)),
                    const SizedBox(height: 2),
                    // Raw price — smaller
                    Text("Market: ₹${rawPrice.toStringAsFixed(0)}",
                        style: AppTheme.bodyMedium.copyWith(fontSize: 11, color: Colors.grey)),
                    // Price change
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(isUp ? Icons.arrow_upward : Icons.arrow_downward,
                            color: isUp ? AppTheme.primaryGreen : AppTheme.error, size: 12),
                        Text("₹${priceChange.abs().toStringAsFixed(0)}",
                            style: TextStyle(fontSize: 10, color: isUp ? AppTheme.primaryGreen : AppTheme.error, fontWeight: FontWeight.w600)),
                      ],
                    ),
                  ],
                ),
              ],
            ),

            // Risk indicator per mandi
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: (mandiRisk['color'] as Color).withOpacity(0.06),
                borderRadius: BorderRadius.circular(4),
              ),
              child: Row(
                children: [
                  Icon(mandiRisk['icon'] as IconData, color: mandiRisk['color'] as Color, size: 14),
                  const SizedBox(width: 6),
                  Text(mandiRisk['message'] as String,
                      style: TextStyle(fontSize: 10, color: mandiRisk['color'] as Color, fontWeight: FontWeight.w500)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _tag(IconData icon, String text, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.08),
        borderRadius: BorderRadius.circular(2),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 10, color: color),
          const SizedBox(width: 2),
          Text(text, style: TextStyle(fontSize: 10, color: color, fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }
}
