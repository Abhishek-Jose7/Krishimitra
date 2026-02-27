import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/farmer_profile_provider.dart';
import '../services/api_service.dart';
import '../theme.dart';
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
    'Rice': '🌾', 'Wheat': '🌿', 'Maize': '🌽', 'Soybean': '🫘',
    'Cotton': '☁️', 'Sugarcane': '🎋', 'Groundnut': '🥜', 'Onion': '🧅',
    'Tomato': '🍅', 'Potato': '🥔', 'Coconut': '🥥', 'Ragi': '🌾',
    'Jowar': '🌾', 'Bajra': '🌾', 'Mustard': '🌻', 'Gram': '🫘',
    'Lentils': '🫘', 'Arecanut': '🌴', 'Sunflower': '🌻', 'Banana': '🍌',
    'Chilli': '🌶️', 'Turmeric': '🌿', 'Cumin': '🌿', 'Pepper': '🌶️',
    'Cardamom': '🌿', 'Mango': '🥭', 'Grapes': '🍇',
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
      final bestMandi = _mandis.isNotEmpty ? _mandis[0]['mandi'] as String? : null;
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
      return {'level': 'MODEL', 'message': 'Price from AI model prediction', 'color': AppTheme.accentBlue, 'icon': Icons.auto_awesome};
    }
    if (priceChange < -30) {
      return {'level': 'HIGH', 'message': 'Price dropped today — stay alert', 'color': AppTheme.error, 'icon': Icons.warning_amber_rounded};
    } else if (priceChange < -10) {
      return {'level': 'MEDIUM', 'message': 'Slight price dip today', 'color': AppTheme.accentOrange, 'icon': Icons.info_outline};
    }
    return {'level': 'LOW', 'message': 'Stable prices today', 'color': AppTheme.primaryGreen, 'icon': Icons.check_circle_outline};
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

          // Forecast banner — shows real model predictions
          if (_forecast != null) _buildForecastBanner(),

          // Mandi list
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator(color: AppTheme.primaryGreen))
                : _mandis.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.store_mall_directory, size: 56, color: Colors.grey.shade300),
                            const SizedBox(height: 12),
                            Text("No mandis found for your state",
                                style: AppTheme.bodyMedium.copyWith(color: AppTheme.textLight)),
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
                ? [AppTheme.primaryGreen.withOpacity(0.08), AppTheme.accentBlue.withOpacity(0.06)]
                : [Colors.grey.shade50, Colors.grey.shade100],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(AppTheme.cardRadius),
          border: Border.all(color: isModelBased ? AppTheme.accentBlue.withOpacity(0.3) : Colors.grey.shade200),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                if (isModelBased) ...[
                  Icon(Icons.auto_awesome, size: 14, color: AppTheme.accentBlue),
                  const SizedBox(width: 4),
                  Expanded(
                    child: Text("AI Price Prediction",
                        style: AppTheme.bodyMedium.copyWith(fontSize: 10, color: AppTheme.accentBlue, fontWeight: FontWeight.w600)),
                  ),
                ] else ...[
                  Icon(Icons.show_chart, size: 14, color: AppTheme.textLight),
                  const SizedBox(width: 4),
                  Expanded(
                    child: Text("Price Forecast",
                        style: AppTheme.bodyMedium.copyWith(fontSize: 10, color: AppTheme.textLight, fontWeight: FontWeight.w600)),
                  ),
                ],
                Text("Tap for details →",
                    style: AppTheme.bodyMedium.copyWith(fontSize: 9, color: AppTheme.accentBlue)),
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
                      Text("Today's Price", style: AppTheme.bodyMedium.copyWith(fontSize: 10)),
                      FittedBox(
                        fit: BoxFit.scaleDown,
                        alignment: Alignment.centerLeft,
                        child: Text("₹${(todayPrice as num).toStringAsFixed(0)}/qtl",
                            style: AppTheme.headingMedium.copyWith(fontSize: 18, color: AppTheme.primaryGreen)),
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
                      Text("7-Day Trend", style: AppTheme.bodyMedium.copyWith(fontSize: 10)),
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(trendUp ? Icons.trending_up : Icons.trending_down,
                              color: trendUp ? AppTheme.primaryGreen : AppTheme.error, size: 16),
                          const SizedBox(width: 3),
                          Text("${trendUp ? '+' : ''}${(trend as num).toStringAsFixed(1)}%",
                              style: TextStyle(
                                fontSize: 14, fontWeight: FontWeight.w700,
                                color: trendUp ? AppTheme.primaryGreen : AppTheme.error,
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
    final prices = forecast.take(7).map((f) => (f['price'] as num).toDouble()).toList();
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
                  Container(
                    height: barHeight,
                    decoration: BoxDecoration(
                      color: isMax ? AppTheme.primaryGreen : AppTheme.primaryGreen.withOpacity(0.3),
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text("D${i + 1}", style: TextStyle(fontSize: 7, color: Colors.grey.shade500)),
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
    // "Best price" is the first non-nearest mandi (they're sorted by effective_price)
    final isFirstNonNearest = !isNearest &&
        _mandis.where((m) => m['is_nearest'] != true).toList().indexOf(mandi) == 0;
    final isHighlighted = isNearest || isFirstNonNearest;

    final priceChange = (mandi['price_change'] ?? 0).toDouble();
    final isUp = priceChange >= 0;
    final distanceKm = (mandi['distance_km'] ?? 0).toDouble();
    final netPrice = (mandi['effective_price'] ?? mandi['today_price'] ?? 0).toDouble();
    final rawPrice = (mandi['today_price'] ?? 0).toDouble();
    final transportCost = (mandi['transport_cost'] ?? 0).toDouble();
    final mandiRisk = _getMandiRisk(mandi);
    final mandiState = mandi['state'] ?? '';

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(AppTheme.cardRadius),
        border: Border.all(
          color: isNearest
              ? AppTheme.primaryGreen
              : isFirstNonNearest
                  ? AppTheme.accentBlue
                  : Colors.grey.shade200,
          width: isHighlighted ? 2 : 1,
        ),
        boxShadow: isHighlighted ? [BoxShadow(color: (isNearest ? AppTheme.primaryGreen : AppTheme.accentBlue).withOpacity(0.1), blurRadius: 8, offset: const Offset(0, 2))] : [],
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
                          if (isNearest)
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              margin: const EdgeInsets.only(right: 6),
                              decoration: BoxDecoration(
                                color: AppTheme.primaryGreen,
                                borderRadius: BorderRadius.circular(2),
                              ),
                              child: const Text("📍 NEAREST",
                                  style: TextStyle(color: Colors.white, fontSize: 8, fontWeight: FontWeight.bold)),
                            )
                          else if (isFirstNonNearest)
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              margin: const EdgeInsets.only(right: 6),
                              decoration: BoxDecoration(
                                color: AppTheme.accentBlue,
                                borderRadius: BorderRadius.circular(2),
                              ),
                              child: const Text("⭐ BEST PRICE",
                                  style: TextStyle(color: Colors.white, fontSize: 8, fontWeight: FontWeight.bold)),
                            ),
                          Expanded(
                            child: Text(mandi['mandi'] ?? '',
                                style: AppTheme.headingMedium.copyWith(fontSize: 15),
                                overflow: TextOverflow.ellipsis),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      // State + district label
                      if (mandiState.isNotEmpty)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 4),
                          child: Text("${mandi['district'] ?? ''}, $mandiState",
                              style: AppTheme.bodyMedium.copyWith(fontSize: 10, color: Colors.grey.shade500)),
                        ),
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

                // Price column
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text("₹${netPrice.toStringAsFixed(0)}",
                        style: AppTheme.headingLarge.copyWith(
                          color: isNearest ? AppTheme.primaryGreen : isFirstNonNearest ? AppTheme.accentBlue : AppTheme.textDark,
                          fontSize: 24, fontWeight: FontWeight.w800)),
                    Text("Net / Quintal", style: AppTheme.bodyMedium.copyWith(fontSize: 10, color: AppTheme.textLight)),
                    const SizedBox(height: 2),
                    Text("Market: ₹${rawPrice.toStringAsFixed(0)}",
                        style: AppTheme.bodyMedium.copyWith(fontSize: 11, color: Colors.grey)),
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

            // Risk / source indicator
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
