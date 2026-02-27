import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:fl_chart/fl_chart.dart';
import '../services/api_service.dart';
import '../providers/farmer_profile_provider.dart';
import '../theme.dart';
import '../widgets/app_card.dart';

class PriceScreen extends StatefulWidget {
  const PriceScreen({super.key});

  @override
  State<PriceScreen> createState() => _PriceScreenState();
}

class _PriceScreenState extends State<PriceScreen> {
  String _crop = '';
  String _mandi = '';
  Map<String, dynamic>? _result;
  bool _isLoading = false;

  List<String> _crops = [];
  List<String> _mandis = [];
  String _state = '';

  @override
  void initState() {
    super.initState();
    final profile = Provider.of<FarmerProfile>(context, listen: false);
    _state = profile.state ?? '';
    _crops = profile.crops.isNotEmpty ? profile.crops : [profile.primaryCrop ?? 'Rice'];
    _crop = _crops.first;
    _mandi = profile.nearestMandi ?? '${profile.district ?? "Pune"} Mandi';
    _mandis = [_mandi];
    _forecast();
  }

  Future<void> _forecast() async {
    setState(() => _isLoading = true);
    try {
      final api = Provider.of<ApiService>(context, listen: false);
      final result = await api.forecastPrice(_crop, _mandi, state: _state);
      setState(() => _result = result);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Error: $e")));
      }
    } finally {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Price Trends")),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: AppTheme.primaryGreen))
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: DropdownButtonFormField(
                          value: _crop,
                          items: _crops.map((e) => DropdownMenuItem(value: e, child: Text(e))).toList(),
                          onChanged: (v) {
                            setState(() => _crop = v!);
                            _forecast();
                          },
                          decoration: AppTheme.inputDecoration("Crop", Icons.grass),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: DropdownButtonFormField(
                          value: _mandi,
                          items: _mandis.map((e) => DropdownMenuItem(value: e, child: Text(e, style: const TextStyle(fontSize: 12)))).toList(),
                          onChanged: (v) {
                            setState(() => _mandi = v!);
                            _forecast();
                          },
                          decoration: AppTheme.inputDecoration("Mandi", Icons.storefront),
                        ),
                      ),
                    ],
                  ),

                  if (_result != null) ...[
                    const SizedBox(height: 20),
                    _buildPriceSummary(),
                    const SizedBox(height: 12),
                    _buildPeakCard(),
                    const SizedBox(height: 12),
                    _buildChart(),
                    const SizedBox(height: 12),
                    _buildVolatilityInfo(),
                  ],
                ],
              ),
            ),
    );
  }

  Widget _buildPriceSummary() {
    final currentPrice = (_result!['current_price'] ?? 0).toDouble();
    final trend = _result!['trend'] ?? 'Stable';
    final isRising = trend == 'Rising';
    final isFalling = trend == 'Falling';

    return AppCard(
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text("Today's Price", style: AppTheme.bodyMedium.copyWith(fontSize: 11)),
              const SizedBox(height: 2),
              Text(
                "₹${currentPrice.toStringAsFixed(0)}",
                style: AppTheme.headingLarge.copyWith(fontSize: 30),
              ),
              Text("/Quintal", style: AppTheme.bodyMedium.copyWith(fontSize: 10)),
            ],
          ),
          const Spacer(),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: (isRising
                  ? AppTheme.primaryGreen
                  : isFalling
                      ? AppTheme.error
                      : AppTheme.accentOrange),
              borderRadius: BorderRadius.circular(2),
            ),
            child: Row(
              children: [
                Icon(
                  isRising ? Icons.trending_up : isFalling ? Icons.trending_down : Icons.trending_flat,
                  color: Colors.white,
                  size: 18,
                ),
                const SizedBox(width: 4),
                Text(
                  trend,
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPeakCard() {
    final peakPrice = (_result!['peak_price'] ?? 0).toDouble();
    final peakDate = _result!['peak_date'] ?? '';

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.lightGreen,
        borderRadius: BorderRadius.circular(AppTheme.cardRadius),
        border: Border.all(color: AppTheme.primaryGreen.withOpacity(0.2)),
      ),
      child: Row(
        children: [
          const Icon(Icons.stars, color: AppTheme.primaryGreen, size: 24),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text("Expected Peak Price", style: AppTheme.bodyMedium.copyWith(fontSize: 11)),
                Text(
                  "₹${peakPrice.toStringAsFixed(0)}/Quintal",
                  style: AppTheme.headingMedium.copyWith(color: AppTheme.primaryGreen, fontSize: 16),
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text("Around", style: AppTheme.bodyMedium.copyWith(fontSize: 10)),
              Text(peakDate, style: AppTheme.bodyMedium.copyWith(fontWeight: FontWeight.bold, fontSize: 11)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildChart() {
    final forecast = _result!['forecast'] as List<dynamic>? ?? [];
    if (forecast.isEmpty) return const SizedBox.shrink();

    final spots = <FlSpot>[];
    double minY = double.infinity;
    double maxY = double.negativeInfinity;

    for (int i = 0; i < forecast.length; i++) {
      final price = (forecast[i]['price'] ?? 0).toDouble();
      spots.add(FlSpot(i.toDouble(), price));
      if (price < minY) minY = price;
      if (price > maxY) maxY = price;
    }

    return AppCard(
      padding: const EdgeInsets.only(right: 16, left: 8, top: 16, bottom: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(left: 12, bottom: 10),
            child: Text("90-Day Trend", style: AppTheme.headingMedium.copyWith(fontSize: 13)),
          ),
          AspectRatio(
            aspectRatio: 1.6,
            child: LineChart(
              LineChartData(
                gridData: FlGridData(
                  show: true,
                  drawVerticalLine: false,
                  horizontalInterval: (maxY - minY) / 4,
                  getDrawingHorizontalLine: (value) => FlLine(color: Colors.grey.shade200, strokeWidth: 1),
                ),
                titlesData: FlTitlesData(
                  show: true,
                  rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      interval: 30,
                      getTitlesWidget: (value, meta) {
                        final day = value.toInt();
                        String label = '';
                        if (day == 0) {
                          label = 'Today';
                        } else if (day == 30) {
                          label = '1 Mo';
                        } else if (day == 60) {
                          label = '2 Mo';
                        } else if (day == 89) {
                          label = '3 Mo';
                        }
                        return Padding(
                          padding: const EdgeInsets.only(top: 6),
                          child: Text(label, style: AppTheme.bodyMedium.copyWith(fontSize: 9)),
                        );
                      },
                    ),
                  ),
                  leftTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                ),
                borderData: FlBorderData(show: false),
                minY: minY - 100,
                maxY: maxY + 100,
                lineBarsData: [
                  LineChartBarData(
                    spots: spots,
                    isCurved: false,
                    color: AppTheme.primaryGreen,
                    barWidth: 2,
                    dotData: const FlDotData(show: false),
                    belowBarData: BarAreaData(
                      show: true,
                      color: AppTheme.primaryGreen.withOpacity(0.06),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildVolatilityInfo() {
    final volatility = (_result!['volatility'] ?? 0).toDouble();
    String level;
    Color color;
    String emoji;

    if (volatility < 0.1) {
      level = 'Stable';
      color = AppTheme.primaryGreen;
      emoji = '🟢';
    } else if (volatility < 0.2) {
      level = 'Moderate';
      color = AppTheme.accentOrange;
      emoji = '🟡';
    } else {
      level = 'Volatile';
      color = AppTheme.error;
      emoji = '🔴';
    }

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(AppTheme.cardRadius),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        children: [
          Text(emoji, style: const TextStyle(fontSize: 20)),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text("Market Stability: $level", style: AppTheme.bodyMedium.copyWith(fontWeight: FontWeight.bold, color: color, fontSize: 12)),
                Text(
                  volatility < 0.1
                      ? "Prices are steady. Safe to plan."
                      : volatility < 0.2
                          ? "Some ups and downs. Keep watching."
                          : "Prices changing fast. Be cautious.",
                  style: AppTheme.bodyMedium.copyWith(fontSize: 11, color: AppTheme.textDark),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
