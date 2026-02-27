import 'package:flutter/material.dart';
import '../theme.dart';
import '../widgets/animated_bar.dart';

/// Detailed forecast screen — shows full 7-day price forecast
/// with chart, per-day breakdown, and reasoning.
class ForecastDetailScreen extends StatelessWidget {
  final Map<String, dynamic> forecast;
  final String cropName;

  const ForecastDetailScreen({
    super.key,
    required this.forecast,
    required this.cropName,
  });

  @override
  Widget build(BuildContext context) {
    final todayPrice = (forecast['today_price'] as num?)?.toDouble() ?? 0;
    final trend = (forecast['trend_7d_pct'] as num?)?.toDouble() ?? 0;
    final trendUp = trend > 0;
    final source = forecast['source'] ?? 'estimated';
    final isModel = source == 'xgboost_model';
    final bestDay = forecast['best_day'] as Map<String, dynamic>?;
    final forecastDays = forecast['forecast_7day'] as List<dynamic>? ?? [];
    final day30 = forecast['day_30'] as Map<String, dynamic>?;

    return Scaffold(
      appBar: AppBar(
        title: Text("$cropName Price Forecast"),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Source badge ──
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(
                color: isModel
                    ? AppTheme.accentBlue.withOpacity(0.08)
                    : AppTheme.selectedBg,
                borderRadius: BorderRadius.circular(AppTheme.chipRadius),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    isModel ? Icons.auto_awesome : Icons.show_chart,
                    size: 14,
                    color: isModel ? AppTheme.accentBlue : AppTheme.textMuted,
                  ),
                  const SizedBox(width: 6),
                  Text(
                    isModel ? "XGBoost AI Model Prediction" : "Statistical Forecast",
                    style: AppTheme.bodyMedium.copyWith(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: isModel ? AppTheme.accentBlue : AppTheme.textMuted,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // ── Today's price card ──
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [AppTheme.primaryGreen, AppTheme.secondaryGreen],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(AppTheme.cardRadius),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text("Today's Predicted Price",
                      style: AppTheme.bodyMedium.copyWith(fontSize: 12, color: Colors.white70)),
                  const SizedBox(height: 4),
                  Text("₹${todayPrice.toStringAsFixed(0)} / quintal",
                      style: AppTheme.headingLarge.copyWith(color: Colors.white, fontSize: 28)),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      _badge(
                        icon: trendUp ? Icons.trending_up : Icons.trending_down,
                        label: "${trendUp ? '+' : ''}${trend.toStringAsFixed(1)}% (7-day trend)",
                        color: trendUp ? Colors.green.shade100 : Colors.red.shade100,
                        textColor: trendUp ? Colors.green.shade800 : Colors.red.shade800,
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // ── 7-Day Forecast Chart ──
            Text("7-Day Price Forecast", style: AppTheme.headingMedium.copyWith(fontSize: 16)),
            const SizedBox(height: 4),
            Text("Predicted prices for the next 7 days",
                style: AppTheme.bodyMedium.copyWith(fontSize: 12)),
            const SizedBox(height: 12),

            if (forecastDays.isNotEmpty) _buildChart(forecastDays),

            const SizedBox(height: 20),

            // ── Per-day breakdown ──
            Text("Daily Breakdown", style: AppTheme.headingMedium.copyWith(fontSize: 16)),
            const SizedBox(height: 10),
            ...forecastDays.asMap().entries.map((entry) {
              final i = entry.key;
              final day = entry.value;
              final price = (day['price'] as num?)?.toDouble() ?? 0;
              final date = day['date'] ?? 'Day ${i + 1}';
              final isBest = bestDay != null && bestDay['day'] == i + 1;
              final diff = price - todayPrice;
              final diffUp = diff >= 0;

              return Container(
                margin: const EdgeInsets.only(bottom: 6),
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                decoration: BoxDecoration(
                  color: isBest ? AppTheme.primaryGreen.withOpacity(0.06) : Colors.white,
                  borderRadius: BorderRadius.circular(AppTheme.cardRadius),
                  border: Border.all(
                    color: isBest ? AppTheme.primaryGreen : AppTheme.cardBorder,
                    width: isBest ? 1.5 : 1,
                  ),
                ),
                child: Row(
                  children: [
                    // Day number
                    Container(
                      width: 36,
                      height: 36,
                      decoration: BoxDecoration(
                        color: isBest
                            ? AppTheme.primaryGreen
                            : AppTheme.lightGreen,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Center(
                        child: Text("D${i + 1}",
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w700,
                              color: isBest ? Colors.white : AppTheme.primaryGreen,
                            )),
                      ),
                    ),
                    const SizedBox(width: 12),
                    // Date + best label
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(date, style: AppTheme.bodyLarge.copyWith(fontSize: 13, fontWeight: FontWeight.w500)),
                          if (isBest)
                            Text("⭐ Best day to sell",
                                style: TextStyle(fontSize: 10, color: AppTheme.primaryGreen, fontWeight: FontWeight.w600)),
                        ],
                      ),
                    ),
                    // Price + diff
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text("₹${price.toStringAsFixed(0)}",
                            style: AppTheme.headingMedium.copyWith(
                              fontSize: 16,
                              color: isBest ? AppTheme.primaryGreen : AppTheme.textDark,
                            )),
                        Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(diffUp ? Icons.arrow_upward : Icons.arrow_downward,
                                size: 10, color: diffUp ? AppTheme.primaryGreen : AppTheme.error),
                            Text("₹${diff.abs().toStringAsFixed(0)} vs today",
                                style: TextStyle(
                                  fontSize: 9,
                                  color: diffUp ? AppTheme.primaryGreen : AppTheme.error,
                                  fontWeight: FontWeight.w500,
                                )),
                          ],
                        ),
                      ],
                    ),
                  ],
                ),
              );
            }),

            // ── 30-Day prediction ──
            if (day30 != null) ...[
              const SizedBox(height: 20),
              Text("30-Day Outlook", style: AppTheme.headingMedium.copyWith(fontSize: 16)),
              const SizedBox(height: 10),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppTheme.accentBlue.withOpacity(0.05),
                  borderRadius: BorderRadius.circular(AppTheme.cardRadius),
                  border: Border.all(color: AppTheme.accentBlue.withOpacity(0.2)),
                ),
                child: Row(
                  children: [
                    Icon(Icons.calendar_month, color: AppTheme.accentBlue, size: 28),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text("Predicted price in 30 days",
                              style: AppTheme.bodyMedium.copyWith(fontSize: 11)),
                          Text("₹${(day30['predicted_price'] as num?)?.toStringAsFixed(0) ?? '—'} / quintal",
                              style: AppTheme.headingMedium.copyWith(fontSize: 18, color: AppTheme.accentBlue)),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ],

            // ── Reasoning section ──
            const SizedBox(height: 20),
            Text("How This Prediction Works", style: AppTheme.headingMedium.copyWith(fontSize: 16)),
            const SizedBox(height: 10),
            _reasoningCard(
              Icons.memory,
              "Model",
              isModel
                  ? "XGBoost gradient-boosted decision tree trained on historical market data specific to your region."
                  : "Statistical price model using historical trend analysis.",
            ),
            _reasoningCard(
              Icons.dataset,
              "Data Sources",
              "Historical mandi prices, seasonal patterns, festival/marriage season demand, monsoon impact, and government MSP data.",
            ),
            _reasoningCard(
              Icons.trending_up,
              "Trend Analysis",
              trendUp
                  ? "Prices are trending upward over the next 7 days. Consider holding if you have storage."
                  : "Prices are expected to dip slightly. Consider selling sooner if storage is limited.",
            ),
            if (bestDay != null)
              _reasoningCard(
                Icons.star,
                "Best Sell Day",
                "Day ${bestDay['day'] ?? '?'} shows the highest predicted price after accounting for storage costs. "
                "Selling on this day maximizes your net earnings.",
              ),
            _reasoningCard(
              Icons.warning_amber,
              "Important",
              "These are model predictions based on historical patterns. Actual prices can differ due to sudden weather events, "
              "policy changes, or unexpected market shifts. Always cross-check with your local mandi before making decisions.",
            ),

            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }

  Widget _buildChart(List<dynamic> forecastDays) {
    final prices = forecastDays.take(7).map((f) => (f['price'] as num).toDouble()).toList();
    final minP = prices.reduce((a, b) => a < b ? a : b);
    final maxP = prices.reduce((a, b) => a > b ? a : b);
    final range = maxP - minP;

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(AppTheme.cardRadius),
        border: Border.all(color: AppTheme.cardBorder),
      ),
      child: SizedBox(
        height: 120,
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: List.generate(prices.length, (i) {
            final normalized = range > 0 ? (prices[i] - minP) / range : 0.5;
            final barHeight = 20 + (normalized * 70);
            final isMax = prices[i] == maxP;
            final isMin = prices[i] == minP;
            return Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 3),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    Text("₹${prices[i].toStringAsFixed(0)}",
                        style: TextStyle(
                          fontSize: 9,
                          fontWeight: isMax ? FontWeight.w700 : FontWeight.w400,
                          color: isMax
                              ? AppTheme.primaryGreen
                              : isMin
                                  ? AppTheme.error
                                  : AppTheme.textMuted,
                        )),
                    const SizedBox(height: 4),
                     AnimatedBar(
                      targetHeight: barHeight,
                      delay: Duration(milliseconds: i * 120),
                      decoration: BoxDecoration(
                        color: isMax
                            ? AppTheme.primaryGreen
                            : isMin
                                ? AppTheme.error.withOpacity(0.4)
                                : AppTheme.primaryGreen.withOpacity(0.3),
                        borderRadius: BorderRadius.circular(3),
                      ),
                    ),
                    const SizedBox(height: 4),
                     Text("Day ${i + 1}",
                        style: TextStyle(fontSize: 9, color: AppTheme.textMuted)),
                  ],
                ),
              ),
            );
          }),
        ),
      ),
    );
  }

  Widget _badge({
    required IconData icon,
    required String label,
    required Color color,
    required Color textColor,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(AppTheme.chipRadius),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: textColor),
          const SizedBox(width: 4),
          Text(label, style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: textColor)),
        ],
      ),
    );
  }

  Widget _reasoningCard(IconData icon, String title, String body) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(AppTheme.cardRadius),
        border: Border.all(color: AppTheme.cardBorder),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF1A4731).withOpacity(0.08),
            blurRadius: 12,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              color: AppTheme.lightGreen,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(icon, size: 16, color: AppTheme.primaryGreen),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: AppTheme.headingMedium.copyWith(fontSize: 13)),
                const SizedBox(height: 3),
                Text(body,
                    style: AppTheme.bodyMedium.copyWith(fontSize: 12, height: 1.4)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
