"""
Feature Engineering Layer

Computes advanced features from historical data stored in the time-series tables.
These features feed into ML models, risk assessment, and recommendation logic.
"""

import datetime
from database.db import db
from database.models import PriceHistory, WeatherHistory, ArrivalVolume, DistrictCropStats
from sqlalchemy import func


class FeatureEngine:

    @staticmethod
    def price_momentum(crop, mandi, window=7):
        """
        7-day price momentum: rate of price change over the window.
        Returns: { momentum_pct, direction, avg_price, start_price, end_price }
        Positive momentum = prices rising, negative = falling.
        """
        cutoff = datetime.date.today() - datetime.timedelta(days=window)
        prices = (
            PriceHistory.query
            .filter_by(crop=crop, mandi=mandi)
            .filter(PriceHistory.date >= cutoff)
            .order_by(PriceHistory.date.asc())
            .all()
        )

        if len(prices) < 2:
            return {
                'momentum_pct': 0.0, 'direction': 'insufficient_data',
                'avg_price': 0, 'start_price': 0, 'end_price': 0,
                'data_points': len(prices),
            }

        start_price = prices[0].price
        end_price = prices[-1].price
        avg_price = sum(p.price for p in prices) / len(prices)
        momentum_pct = ((end_price - start_price) / start_price) * 100 if start_price > 0 else 0

        if momentum_pct > 2:
            direction = 'rising'
        elif momentum_pct < -2:
            direction = 'falling'
        else:
            direction = 'stable'

        return {
            'momentum_pct': round(momentum_pct, 2),
            'direction': direction,
            'avg_price': round(avg_price, 2),
            'start_price': round(start_price, 2),
            'end_price': round(end_price, 2),
            'data_points': len(prices),
        }

    @staticmethod
    def seasonal_index(crop, district, month=None):
        """
        Seasonal price index: ratio of this month's avg price to annual avg.
        > 1.0 means prices are above annual average this month.
        < 1.0 means prices are below average (harvest glut, etc).
        """
        if month is None:
            month = datetime.date.today().month

        # Get all prices for this crop in this district
        all_prices = (
            PriceHistory.query
            .filter_by(crop=crop, district=district)
            .all()
        )

        if not all_prices:
            # Return neutral index with default seasonal patterns
            seasonal_defaults = {
                1: 1.05, 2: 1.08, 3: 1.10, 4: 1.02, 5: 0.95, 6: 0.90,
                7: 0.88, 8: 0.85, 9: 0.92, 10: 0.98, 11: 1.05, 12: 1.10,
            }
            return {
                'index': seasonal_defaults.get(month, 1.0),
                'interpretation': 'default_pattern',
                'data_points': 0,
            }

        annual_avg = sum(p.price for p in all_prices) / len(all_prices)
        month_prices = [p.price for p in all_prices if p.date.month == month]

        if not month_prices or annual_avg == 0:
            return {'index': 1.0, 'interpretation': 'neutral', 'data_points': 0}

        month_avg = sum(month_prices) / len(month_prices)
        index = month_avg / annual_avg

        if index > 1.1:
            interpretation = 'above_average'
        elif index < 0.9:
            interpretation = 'below_average'
        else:
            interpretation = 'near_average'

        return {
            'index': round(index, 3),
            'interpretation': interpretation,
            'month_avg': round(month_avg, 2),
            'annual_avg': round(annual_avg, 2),
            'data_points': len(month_prices),
        }

    @staticmethod
    def rainfall_anomaly(district, days=30):
        """
        Compares recent rainfall against historical average.
        Positive anomaly = more rain than normal (flood risk, crop damage).
        Negative anomaly = drought conditions.
        """
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)
        recent = (
            WeatherHistory.query
            .filter_by(district=district)
            .filter(WeatherHistory.recorded_at >= cutoff)
            .all()
        )

        # Historical average (all time)
        all_records = WeatherHistory.query.filter_by(district=district).all()

        if not recent:
            return {
                'anomaly_mm': 0, 'anomaly_pct': 0,
                'interpretation': 'no_data', 'recent_total_mm': 0,
                'historical_avg_mm': 0,
            }

        recent_total = sum(r.rainfall or 0 for r in recent)
        recent_avg_daily = recent_total / len(recent)

        if all_records:
            hist_total = sum(r.rainfall or 0 for r in all_records)
            hist_avg_daily = hist_total / len(all_records)
        else:
            hist_avg_daily = recent_avg_daily  # no baseline

        expected_total = hist_avg_daily * days
        anomaly_mm = recent_total - expected_total
        anomaly_pct = (anomaly_mm / expected_total * 100) if expected_total > 0 else 0

        if anomaly_pct > 30:
            interpretation = 'excess_rainfall'
        elif anomaly_pct < -30:
            interpretation = 'deficit'
        else:
            interpretation = 'normal'

        return {
            'anomaly_mm': round(anomaly_mm, 1),
            'anomaly_pct': round(anomaly_pct, 1),
            'interpretation': interpretation,
            'recent_total_mm': round(recent_total, 1),
            'historical_avg_mm': round(expected_total, 1),
            'data_points': len(recent),
        }

    @staticmethod
    def arrival_pressure(crop, district, days=7):
        """
        Current arrival volume vs 30-day average.
        High pressure (>1.2) = oversupply, prices likely to drop.
        Low pressure (<0.8) = undersupply, prices may rise.
        """
        recent_cutoff = datetime.date.today() - datetime.timedelta(days=days)
        baseline_cutoff = datetime.date.today() - datetime.timedelta(days=30)

        recent = (
            ArrivalVolume.query
            .filter_by(crop=crop, district=district)
            .filter(ArrivalVolume.date >= recent_cutoff)
            .all()
        )

        baseline = (
            ArrivalVolume.query
            .filter_by(crop=crop, district=district)
            .filter(ArrivalVolume.date >= baseline_cutoff)
            .all()
        )

        if not recent or not baseline:
            return {
                'pressure_ratio': 1.0, 'interpretation': 'no_data',
                'recent_avg_tonnes': 0, 'baseline_avg_tonnes': 0,
            }

        recent_avg = sum(a.arrival_tonnes for a in recent) / len(recent)
        baseline_avg = sum(a.arrival_tonnes for a in baseline) / len(baseline)

        ratio = recent_avg / baseline_avg if baseline_avg > 0 else 1.0

        if ratio > 1.3:
            interpretation = 'high_pressure'
        elif ratio > 1.1:
            interpretation = 'moderate_pressure'
        elif ratio < 0.7:
            interpretation = 'low_supply'
        elif ratio < 0.9:
            interpretation = 'slightly_low'
        else:
            interpretation = 'normal'

        return {
            'pressure_ratio': round(ratio, 2),
            'interpretation': interpretation,
            'recent_avg_tonnes': round(recent_avg, 1),
            'baseline_avg_tonnes': round(baseline_avg, 1),
        }

    @staticmethod
    def district_yield_benchmark(crop, district):
        """
        Average yield from DistrictCropStats for this crop/district.
        Used to compare farmer's prediction against regional benchmarks.
        """
        stats = (
            DistrictCropStats.query
            .filter_by(crop=crop, district=district)
            .order_by(DistrictCropStats.year.desc())
            .limit(5)
            .all()
        )

        if not stats:
            # Fallback national averages (tonnes/hectare)
            defaults = {
                'Rice': 2.7, 'Wheat': 3.5, 'Maize': 3.0,
                'Soybean': 1.2, 'Cotton': 0.5, 'Onion': 17.0,
                'Sugarcane': 80.0, 'Groundnut': 1.8,
            }
            return {
                'avg_yield': defaults.get(crop, 2.0),
                'source': 'national_default',
                'years_of_data': 0,
            }

        avg_yield = sum(s.yield_per_hectare for s in stats if s.yield_per_hectare) / len(stats)
        best_year = max(stats, key=lambda s: s.yield_per_hectare or 0)
        worst_year = min(stats, key=lambda s: s.yield_per_hectare or float('inf'))

        return {
            'avg_yield': round(avg_yield, 2),
            'best_yield': round(best_year.yield_per_hectare or 0, 2),
            'worst_yield': round(worst_year.yield_per_hectare or 0, 2),
            'best_year': best_year.year,
            'worst_year': worst_year.year,
            'source': 'district_stats',
            'years_of_data': len(stats),
        }

    @staticmethod
    def compute_all_features(crop, district, mandi):
        """
        Aggregates all features into one dict for ML/decision use.
        """
        return {
            'price_momentum': FeatureEngine.price_momentum(crop, mandi),
            'seasonal_index': FeatureEngine.seasonal_index(crop, district),
            'rainfall_anomaly': FeatureEngine.rainfall_anomaly(district),
            'arrival_pressure': FeatureEngine.arrival_pressure(crop, district),
            'yield_benchmark': FeatureEngine.district_yield_benchmark(crop, district),
        }
