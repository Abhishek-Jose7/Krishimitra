import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../providers/farmer_profile_provider.dart';
import '../services/api_service.dart';
import '../theme.dart';
import '../widgets/animated_bar.dart';
import 'forecast_detail_screen.dart';

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

  // Forecast data from real models
  Map<String, dynamic>? _forecast;
  bool _loadingForecast = false;

  static const Map<String, String> cropEmojis = {
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
    'Coconut': '🥥',
    'Ragi': '🌾',
    'Jowar': '🌾',
    'Bajra': '🌾',
    'Mustard': '🌻',
    'Gram': '🫘',
    'Lentils': '🫘',
    'Arecanut': '🌴',
    'Sunflower': '🌻',
    'Banana': '🍌',
    'Chilli': '🌶️',
    'Turmeric': '🌿',
    'Cumin': '🌿',
    'Pepper': '🌶️',
    'Cardamom': '🌿',
    'Mango': '🥭',
    'Grapes': '🍇',
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
      final mandis = await api.getMandiPrices(
        _selectedCrop,
        district: profile.district ?? '',
        state: profile.state ?? '',
      );
      setState(() {
        _mandis = mandis;
        _isLoading = false;
      });
    } catch (e) {
      if (mounted) setState(() => _isLoading = false);
    }
    // Also load forecast in background
    _loadForecast();
  }

  Future<void> _loadForecast() async {
    setState(() => _loadingForecast = true);
    try {
      final profile = Provider.of<FarmerProfile>(context, listen: false);
      final api = Provider.of<ApiService>(context, listen: false);
      final bestMandi =
          _mandis.isNotEmpty ? _mandis[0]['mandi'] as String? : null;
      final forecast = await api.getMandiForecast(
        _selectedCrop,
        state: profile.state ?? '',
        mandi: bestMandi,
      );
      if (mounted) setState(() => _forecast = forecast);
    } catch (_) {
      // No forecast available
    }
    if (mounted) setState(() => _loadingForecast = false);
  }

  String _estimateTravelTime(double distanceKm) {
    final minutes = (distanceKm / 30 * 60).round();
    if (minutes < 60) return '$minutes min drive';
    final hours = minutes ~/ 60;
    final remainingMin = minutes % 60;
    if (remainingMin == 0) return '$hours hr drive';
    return '${hours}h ${remainingMin}m drive';
  }

  Map<String, dynamic> _getMandiRisk(Map<String, dynamic> mandi) {
    final priceChange = (mandi['price_change'] ?? 0).toDouble();
    final priceSource = mandi['price_source'] ?? 'estimated';

    if (priceSource == 'model') {
      return {
        'level': 'MODEL',
        'message': 'Price from AI model prediction',
        'color': AppTheme.accentBlue,
        'icon': Icons.auto_awesome
      };
    }
    if (priceChange < -30) {
      return {
        'level': 'HIGH',
        'message': 'Price dropped today — stay alert',
        'color': AppTheme.error,
        'icon': Icons.warning_amber_rounded
      };
    } else if (priceChange < -10) {
      return {
        'level': 'MEDIUM',
        'message': 'Slight price dip today',
        'color': AppTheme.accentOrange,
        'icon': Icons.info_outline
      };
    }
    return {
      'level': 'LOW',
      'message': 'Stable prices today',
      'color': AppTheme.primaryGreen,
      'icon': Icons.check_circle_outline
    };
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
                    setState(() {
                      _selectedCrop = crop;
                      _forecast = null;
                    });
                    _loadPrices();
                  },
                  child: Container(
                    margin: const EdgeInsets.only(right: 10),
                    padding:
                        const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    decoration: BoxDecoration(
                      color: isSelected
                          ? AppTheme.primaryGreen
                          : AppTheme.background,
                      borderRadius: BorderRadius.circular(AppTheme.chipRadius),
                      border: Border.all(
                        color: isSelected
                            ? AppTheme.primaryGreen
                            : Colors.grey.shade300,
                        width: isSelected ? 2 : 1,
                      ),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(cropEmojis[crop] ?? '🌱',
                            style: const TextStyle(fontSize: 18)),
                        const SizedBox(width: 6),
                        Text(crop,
                            style: TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                                color: isSelected
                                    ? Colors.white
                                    : AppTheme.textDark)),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
          Divider(height: 1, color: Colors.grey.shade300),

          // Forecast banner — shows real model predictions
          if (_forecast != null) _buildForecastBanner(),

          // Mandi list
          Expanded(
            child: _isLoading
                ? const Center(
                    child:
                        CircularProgressIndicator(color: AppTheme.primaryGreen))
                : _mandis.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.store_mall_directory,
                                size: 56, color: Colors.grey.shade300),
                            const SizedBox(height: 12),
                            Text("No mandis found for your state",
                                style: AppTheme.bodyMedium
                                    .copyWith(color: AppTheme.textLight)),
                          ],
                        ),
                      )
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

  /// Forecast banner — top section with real model predictions
  Widget _buildForecastBanner() {
    final todayPrice = _forecast!['today_price'];
    final trend = _forecast!['trend_7d_pct'] ?? 0;
    final source = _forecast!['source'] ?? 'estimated';
    final isModelBased = source == 'xgboost_model';
    final trendUp = (trend as num).toDouble() > 0;

    return GestureDetector(
      onTap: () {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => ForecastDetailScreen(
              forecast: _forecast!,
              cropName: _selectedCrop,
            ),
          ),
        );
      },
      child: Container(
        margin: const EdgeInsets.fromLTRB(12, 10, 12, 4),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: isModelBased
                ? [
                    AppTheme.primaryGreen.withOpacity(0.08),
                    AppTheme.accentBlue.withOpacity(0.06)
                  ]
                : [Colors.grey.shade50, Colors.grey.shade100],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(AppTheme.cardRadius),
          border: Border.all(
              color: isModelBased
                  ? AppTheme.accentBlue.withOpacity(0.3)
                  : AppTheme.cardBorder),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                if (isModelBased) ...[
                  Icon(Icons.auto_awesome,
                      size: 14, color: AppTheme.accentBlue),
                  const SizedBox(width: 4),
                  Expanded(
                    child: Text("AI Price Prediction",
                        style: AppTheme.bodyMedium.copyWith(
                            fontSize: 10,
                            color: AppTheme.accentBlue,
                            fontWeight: FontWeight.w600)),
                  ),
                ] else ...[
                  Icon(Icons.show_chart, size: 14, color: AppTheme.textLight),
                  const SizedBox(width: 4),
                  Expanded(
                    child: Text("Price Forecast",
                        style: AppTheme.bodyMedium.copyWith(
                            fontSize: 10,
                            color: AppTheme.textLight,
                            fontWeight: FontWeight.w600)),
                  ),
                ],
                Text("Tap for details →",
                    style: AppTheme.bodyMedium
                        .copyWith(fontSize: 9, color: AppTheme.accentBlue)),
              ],
            ),
            const SizedBox(height: 10),

            // Price + Trend row — use Flexible to prevent overflow
            Row(
              children: [
                Flexible(
                  flex: 3,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text("Today's Price",
                          style: AppTheme.bodyMedium.copyWith(fontSize: 10)),
                      FittedBox(
                        fit: BoxFit.scaleDown,
                        alignment: Alignment.centerLeft,
                        child: Text(
                            "₹${(todayPrice as num).toStringAsFixed(0)}/qtl",
                            style: AppTheme.headingMedium.copyWith(
                                fontSize: 18, color: AppTheme.primaryGreen)),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 16),
                Flexible(
                  flex: 2,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text("7-Day Trend",
                          style: AppTheme.bodyMedium.copyWith(fontSize: 10)),
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                              trendUp ? Icons.trending_up : Icons.trending_down,
                              color: trendUp
                                  ? AppTheme.primaryGreen
                                  : AppTheme.error,
                              size: 16),
                          const SizedBox(width: 3),
                          Text(
                              "${trendUp ? '+' : ''}${(trend as num).toStringAsFixed(1)}%",
                              style: TextStyle(
                                fontSize: 14,
                                fontWeight: FontWeight.w700,
                                color: trendUp
                                    ? AppTheme.primaryGreen
                                    : AppTheme.error,
                              )),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),

            // Mini 7-day forecast bars
            if (_forecast!['forecast_7day'] != null) ...[
              const SizedBox(height: 8),
              _buildMiniChart(_forecast!['forecast_7day']),
            ],
          ],
        ),
      ),
    );
  }

  /// Mini bar chart of 7-day forecast — compact version
  Widget _buildMiniChart(List<dynamic> forecast) {
    if (forecast.isEmpty) return const SizedBox.shrink();
    final prices =
        forecast.take(7).map((f) => (f['price'] as num).toDouble()).toList();
    final minP = prices.reduce((a, b) => a < b ? a : b);
    final maxP = prices.reduce((a, b) => a > b ? a : b);
    final range = maxP - minP;

    return SizedBox(
      height: 44,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: List.generate(prices.length, (i) {
          final normalized = range > 0 ? (prices[i] - minP) / range : 0.5;
          final barHeight = 10.0 + (normalized * 20.0);
          final isMax = prices[i] == maxP;
          return Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 2),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.end,
                mainAxisSize: MainAxisSize.min,
                children: [
                  AnimatedBar(
                    targetHeight: barHeight,
                    delay: Duration(milliseconds: i * 80),
                    decoration: BoxDecoration(
                      color: isMax
                          ? AppTheme.primaryGreen
                          : AppTheme.primaryGreen.withOpacity(0.3),
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text("D${i + 1}",
                      style:
                          TextStyle(fontSize: 7, color: Colors.grey.shade500)),
                ],
              ),
            ),
          );
        }),
      ),
    );
  }

  Widget _buildMandiCard(Map<String, dynamic> mandi, int index) {
    final isNearest = mandi['is_nearest'] == true;
    final isFirstNonNearest = !isNearest &&
        _mandis.where((m) => m['is_nearest'] != true).toList().indexOf(mandi) ==
            0;
    final isHighlighted = isNearest || isFirstNonNearest;

    final priceChange = (mandi['price_change'] ?? 0).toDouble();
    final isUp = priceChange >= 0;
    final distanceKm = (mandi['distance_km'] ?? 0).toDouble();
    final netPrice =
        (mandi['effective_price'] ?? mandi['today_price'] ?? 0).toDouble();
    final rawPrice = (mandi['today_price'] ?? 0).toDouble();
    final transportCost = (mandi['transport_cost'] ?? 0).toDouble();
    final mandiRisk = _getMandiRisk(mandi);
    final mandiState = mandi['state'] ?? '';

    // Sample real tiny square photo for the crop based on _selectedCrop
    final cropImageUrl =
        'https://images.unsplash.com/photo-1586201375761-83865001e31c?ixlib=rb-4.0.3&auto=format&fit=crop&w=150&q=80'; // generic grain

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(AppTheme.cardRadius),
        border: Border.all(
          color: isNearest
              ? AppTheme.primaryGreen
              : isFirstNonNearest
                  ? AppTheme.accentBlue
                  : AppTheme.cardBorder,
          width: isHighlighted ? 2 : 1,
        ),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF1A4731).withOpacity(0.08),
            blurRadius: 12,
            offset: const Offset(0, 2),
          )
        ],
      ),
      child: Stack(
        children: [
          // Background Photo with Warm Sepia-Tinted Overlay
          Positioned.fill(
            child: Image.network(
              'https://images.unsplash.com/photo-1581578731548-c64695cc6952?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80', // Mandi generic
              fit: BoxFit.cover,
              color: AppTheme.accentGold
                  .withOpacity(0.9), // Amber gradient / sepia tone
              colorBlendMode: BlendMode.multiply,
            ),
          ),
          // Content over photo needs a slight white tint for readability
          Positioned.fill(
            child: Container(
              color: Colors.white.withOpacity(0.85),
            ),
          ),

          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 18), // Space for top-left Badge
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Tiny square photo (crop pill) instead of emoji/round
                    ClipRRect(
                      borderRadius: BorderRadius.circular(4),
                      child: Image.network(
                        cropImageUrl,
                        width: 24,
                        height: 24,
                        fit: BoxFit.cover,
                      ),
                    ),
                    const SizedBox(width: 8),

                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(mandi['mandi'] ?? '',
                              style:
                                  AppTheme.headingLarge.copyWith(fontSize: 18),
                              overflow: TextOverflow.ellipsis),
                          const SizedBox(height: 4),
                          if (mandiState.isNotEmpty)
                            Padding(
                              padding: const EdgeInsets.only(bottom: 4),
                              child: Text(
                                  "${mandi['district'] ?? ''}, $mandiState",
                                  style: AppTheme.bodyMedium.copyWith(
                                      fontSize: 11, color: AppTheme.textDark)),
                            ),
                          const SizedBox(height: 4),
                          // Tags row — distance + travel time
                          Wrap(
                            spacing: 6,
                            runSpacing: 6,
                            children: [
                              _tag(
                                  Icons.location_on,
                                  "${distanceKm.toStringAsFixed(0)} km",
                                  AppTheme.textDark),
                              _tag(
                                  Icons.directions_car,
                                  _estimateTravelTime(distanceKm),
                                  AppTheme.textDark),
                              _tag(
                                  Icons.local_shipping,
                                  "-₹${transportCost.toStringAsFixed(0)}",
                                  AppTheme.textDark),
                            ],
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 10),

                    // Price column
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text("₹${netPrice.toStringAsFixed(0)}",
                            style: AppTheme.headingLarge.copyWith(
                                color: mandi['is_best_profit'] == true
                                    ? AppTheme.primaryGreen
                                    : AppTheme.textDark,
                                fontSize: 24,
                                fontWeight: FontWeight.w900)),
                        Text("Net Profit / Qtl",
                            style: AppTheme.bodyMedium.copyWith(
                                fontSize: 10,
                                color: AppTheme.primaryGreen,
                                fontWeight: FontWeight.bold)),
                        const SizedBox(height: 4),
                        Text("Market: ₹${rawPrice.toStringAsFixed(0)}",
                            style: AppTheme.bodyMedium.copyWith(
                                fontSize: 11,
                                color: AppTheme.textDark,
                                decoration: TextDecoration.lineThrough)),
                        Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                                isUp
                                    ? Icons.arrow_upward
                                    : Icons.arrow_downward,
                                color: isUp
                                    ? AppTheme.primaryGreen
                                    : AppTheme.error,
                                size: 12),
                            Text("₹${priceChange.abs().toStringAsFixed(0)}",
                                style: TextStyle(
                                    fontSize: 11,
                                    color: isUp
                                        ? AppTheme.primaryGreen
                                        : AppTheme.error,
                                    fontWeight: FontWeight.w700)),
                          ],
                        ),
                      ],
                    ),
                  ],
                ),

                // Risk / source indicator
                const SizedBox(height: 12),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: (mandiRisk['color'] as Color).withOpacity(0.06),
                    borderRadius: BorderRadius.circular(AppTheme.chipRadius),
                  ),
                  child: Row(
                    children: [
                      Icon(mandiRisk['icon'] as IconData,
                          color: mandiRisk['color'] as Color, size: 14),
                      const SizedBox(width: 6),
                      Text(mandiRisk['message'] as String,
                          style: TextStyle(
                              fontSize: 11,
                              color: mandiRisk['color'] as Color,
                              fontWeight: FontWeight.bold)),
                      const Spacer(),
                      Text(
                          "Deduced: ₹${transportCost.toStringAsFixed(0)} (Fuel/Transport)",
                          style: TextStyle(
                              fontSize: 9, color: AppTheme.textLight)),
                    ],
                  ),
                ),
                const SizedBox(height: 16),

                // BOOK SLOT & SELL BUTTON — THE NEW USP FEATURE
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: () => _showBookingSheet(mandi),
                    icon: const Icon(Icons.calendar_today, size: 16),
                    label: const Text("BOOK SLOT & SELL NOW"),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: mandi['is_best_profit'] == true
                          ? AppTheme.primaryGreen
                          : AppTheme.accentBlue,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      elevation: 0,
                    ),
                  ),
                ),
              ],
            ),
          ),

          // BADGE POSTION: Top-Left
          if (isNearest || mandi['is_best_profit'] == true)
            Positioned(
              top: 0,
              left: 0,
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: mandi['is_best_profit'] == true
                      ? AppTheme.primaryGreen
                      : AppTheme.accentBlue,
                  borderRadius: const BorderRadius.only(
                    bottomRight: Radius.circular(8),
                  ),
                ),
                child: Text(
                  mandi['is_best_profit'] == true
                      ? "🏆 BEST PROFIT"
                      : "📍 NEAREST",
                  style: const TextStyle(
                      color: Colors.white,
                      fontSize: 9,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 0.5),
                ),
              ),
            ),
        ],
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
          Text(text,
              style: TextStyle(
                  fontSize: 10, color: color, fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }

  void _showBookingSheet(Map<String, dynamic> mandi) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => _MandiBookingSheet(
        mandi: mandi,
        crop: _selectedCrop,
      ),
    );
  }
}

class _MandiBookingSheet extends StatefulWidget {
  final Map<String, dynamic> mandi;
  final String crop;

  const _MandiBookingSheet({required this.mandi, required this.crop});

  @override
  State<_MandiBookingSheet> createState() => _MandiBookingSheetState();
}

class _MandiBookingSheetState extends State<_MandiBookingSheet> {
  DateTime _selectedDate = DateTime.now().add(const Duration(days: 1));
  String _selectedSlot = "08:00 AM - 10:00 AM";
  double _quantity = 10.0;
  bool _isBooking = false;

  final List<String> _slots = [
    "08:00 AM - 10:00 AM",
    "10:00 AM - 12:00 PM",
    "12:00 PM - 02:00 PM",
    "02:00 PM - 04:00 PM",
  ];

  @override
  Widget build(BuildContext context) {
    final netPrice =
        (widget.mandi['effective_price'] ?? widget.mandi['today_price'] ?? 0)
            .toDouble();
    final estimatedTotal = _quantity * netPrice;

    return Container(
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.only(
          topLeft: Radius.circular(32),
          topRight: Radius.circular(32),
        ),
      ),
      padding: const EdgeInsets.fromLTRB(24, 12, 24, 40),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.grey.shade300,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: 24),
          Text(
            "Book Slot at ${widget.mandi['mandi']}",
            style: GoogleFonts.dmSans(
              fontSize: 22,
              fontWeight: FontWeight.w800,
              color: AppTheme.textDark,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            "Skip the 10-hour queue. Your spot will be reserved.",
            style: GoogleFonts.dmSans(fontSize: 14, color: AppTheme.textLight),
          ),
          const SizedBox(height: 24),

          // Date Selection
          Text("Select Date",
              style: GoogleFonts.dmSans(
                  fontWeight: FontWeight.w700, fontSize: 16)),
          const SizedBox(height: 12),
          SizedBox(
            height: 80,
            child: ListView.builder(
              scrollDirection: Axis.horizontal,
              itemCount: 7,
              itemBuilder: (context, index) {
                final date = DateTime.now().add(Duration(days: index + 1));
                final isSelected = date.day == _selectedDate.day;
                return GestureDetector(
                  onTap: () => setState(() => _selectedDate = date),
                  child: Container(
                    width: 70,
                    margin: const EdgeInsets.only(right: 12),
                    decoration: BoxDecoration(
                      color: isSelected
                          ? AppTheme.primaryGreen
                          : Colors.grey.shade50,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(
                        color: isSelected
                            ? AppTheme.primaryGreen
                            : Colors.grey.shade200,
                      ),
                    ),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          DateFormat('EEE').format(date).toUpperCase(),
                          style: GoogleFonts.dmSans(
                            color: isSelected ? Colors.white70 : Colors.grey,
                            fontSize: 10,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        Text(
                          date.day.toString(),
                          style: GoogleFonts.dmSans(
                            color:
                                isSelected ? Colors.white : AppTheme.textDark,
                            fontSize: 20,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
          const SizedBox(height: 24),

          // Time Slot Selection
          Text("Arrival Time",
              style: GoogleFonts.dmSans(
                  fontWeight: FontWeight.w700, fontSize: 16)),
          const SizedBox(height: 12),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: _slots.map((slot) {
              final isSelected = slot == _selectedSlot;
              return GestureDetector(
                onTap: () => setState(() => _selectedSlot = slot),
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                  decoration: BoxDecoration(
                    color: isSelected
                        ? AppTheme.primaryGreen.withOpacity(0.1)
                        : Colors.white,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: isSelected
                          ? AppTheme.primaryGreen
                          : Colors.grey.shade300,
                    ),
                  ),
                  child: Text(
                    slot,
                    style: GoogleFonts.dmSans(
                      color: isSelected
                          ? AppTheme.primaryGreen
                          : AppTheme.textDark,
                      fontSize: 13,
                      fontWeight:
                          isSelected ? FontWeight.bold : FontWeight.w500,
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
          const SizedBox(height: 24),

          // Quantity Row
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text("Quantity (Quintals)",
                  style: GoogleFonts.dmSans(
                      fontWeight: FontWeight.w700, fontSize: 16)),
              Row(
                children: [
                  _qtyBtn(Icons.remove, () {
                    if (_quantity > 1) setState(() => _quantity -= 1);
                  }),
                  const SizedBox(width: 16),
                  Text(_quantity.toStringAsFixed(0),
                      style: GoogleFonts.dmSans(
                          fontSize: 20, fontWeight: FontWeight.w800)),
                  const SizedBox(width: 16),
                  _qtyBtn(Icons.add, () {
                    setState(() => _quantity += 1);
                  }),
                ],
              ),
            ],
          ),
          const SizedBox(height: 32),

          // Summary & Confirm
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: AppTheme.background,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: Colors.grey.shade200),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text("Total Estimated Payout",
                        style: GoogleFonts.dmSans(
                            color: AppTheme.textLight, fontSize: 12)),
                    Text("₹${estimatedTotal.toStringAsFixed(0)}",
                        style: GoogleFonts.dmSans(
                          color: AppTheme.textDark,
                          fontSize: 26,
                          fontWeight: FontWeight.w900,
                        )),
                  ],
                ),
                SizedBox(
                  height: 54,
                  width: 140,
                  child: ElevatedButton(
                    onPressed: _isBooking ? null : _confirmBooking,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.primaryGreen,
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(16),
                      ),
                      elevation: 0,
                    ),
                    child: _isBooking
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(
                                color: Colors.white, strokeWidth: 2),
                          )
                        : Text("CONFIRM",
                            style: GoogleFonts.dmSans(
                                fontWeight: FontWeight.w900, fontSize: 16)),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _qtyBtn(IconData icon, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: Colors.white,
          shape: BoxShape.circle,
          border: Border.all(color: Colors.grey.shade300),
        ),
        child: Icon(icon, size: 20, color: AppTheme.primaryGreen),
      ),
    );
  }

  void _confirmBooking() async {
    setState(() => _isBooking = true);
    // Simulate API call
    await Future.delayed(const Duration(seconds: 2));

    if (mounted) {
      Navigator.pop(context); // Close sheet
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Row(
            children: [
              const Icon(Icons.check_circle, color: Colors.white),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                    "Slot booked! See you at ${widget.mandi['mandi']} on ${DateFormat('MMM dd').format(_selectedDate)}."),
              ),
            ],
          ),
          backgroundColor: AppTheme.primaryGreen,
          behavior: SnackBarBehavior.floating,
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          margin: const EdgeInsets.all(16),
        ),
      );
    }
  }
}
