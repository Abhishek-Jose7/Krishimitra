"""
Trust Engine — Confidence Explanation & Data Transparency

Generates human-readable trust signals so farmers understand
WHY the app gives specific advice, HOW reliable it is, and
WHAT data backs the recommendation.
"""

import datetime
from database.models import PriceHistory, EvaluationMetric, YieldPrediction
from database.db import db


class TrustEngine:

    @staticmethod
    def build_trust_context(recommendation, features=None):
        """
        Builds a complete trust context for a recommendation.

        Returns:
        {
            confidence_score: 0-100,
            confidence_factors: [{ factor, contribution, description }],
            data_sources: [{ source, freshness, reliability }],
            why_this_advice: "plain English explanation",
            what_could_go_wrong: "risk factors",
            similar_past_outcome: "historical context",
        }
        """
        factors = []
        total_confidence = 0

        # Factor 1: Historical price data availability
        price_data_points = _count_price_history(
            recommendation.get('crop', 'Rice'),
            recommendation.get('mandi', 'Pune Mandi'),
        )
        if price_data_points > 90:
            factors.append({
                'factor': 'Price History',
                'contribution': 25,
                'description': f'{price_data_points} days of price data available',
                'status': 'strong',
            })
            total_confidence += 25
        elif price_data_points > 30:
            factors.append({
                'factor': 'Price History',
                'contribution': 15,
                'description': f'{price_data_points} days of data (30+ needed for reliability)',
                'status': 'moderate',
            })
            total_confidence += 15
        else:
            factors.append({
                'factor': 'Price History',
                'contribution': 5,
                'description': f'Only {price_data_points} days of data. Predictions less reliable.',
                'status': 'weak',
            })
            total_confidence += 5

        # Factor 2: Feature quality
        if features:
            momentum = features.get('price_momentum', {})
            if momentum.get('data_points', 0) >= 5:
                factors.append({
                    'factor': 'Price Momentum',
                    'contribution': 15,
                    'description': f"7-day momentum: {momentum.get('momentum_pct', 0)}% ({momentum.get('direction', 'unknown')})",
                    'status': 'strong' if momentum.get('data_points', 0) >= 7 else 'moderate',
                })
                total_confidence += 15
            else:
                factors.append({
                    'factor': 'Price Momentum',
                    'contribution': 5,
                    'description': 'Insufficient recent price data for momentum calculation',
                    'status': 'weak',
                })
                total_confidence += 5

            seasonal = features.get('seasonal_index', {})
            if seasonal.get('data_points', 0) > 0:
                factors.append({
                    'factor': 'Seasonal Pattern',
                    'contribution': 15,
                    'description': f"Seasonal index: {seasonal.get('index', 1.0)} ({seasonal.get('interpretation', 'neutral')})",
                    'status': 'strong',
                })
                total_confidence += 15
            else:
                factors.append({
                    'factor': 'Seasonal Pattern',
                    'contribution': 8,
                    'description': 'Using default seasonal estimates (no historical data yet)',
                    'status': 'moderate',
                })
                total_confidence += 8

            rainfall = features.get('rainfall_anomaly', {})
            if rainfall.get('data_points', 0) > 0:
                factors.append({
                    'factor': 'Weather Data',
                    'contribution': 10,
                    'description': f"Rainfall anomaly: {rainfall.get('anomaly_pct', 0)}% ({rainfall.get('interpretation', 'unknown')})",
                    'status': 'strong',
                })
                total_confidence += 10
            else:
                factors.append({
                    'factor': 'Weather Data',
                    'contribution': 3,
                    'description': 'No weather history available. Using live weather only.',
                    'status': 'weak',
                })
                total_confidence += 3
        else:
            factors.append({
                'factor': 'Feature Analysis',
                'contribution': 5,
                'description': 'Advanced features not computed for this request',
                'status': 'weak',
            })
            total_confidence += 5

        # Factor 3: Mandi comparison breadth
        factors.append({
            'factor': 'Mandi Comparison',
            'contribution': 10,
            'description': '5 mandis compared with transport cost factored in',
            'status': 'moderate',
        })
        total_confidence += 10

        # Factor 4: ML model quality (currently dummy)
        factors.append({
            'factor': 'ML Model',
            'contribution': -15,
            'description': 'Using placeholder model (not trained on real data). Forecasts are simulated.',
            'status': 'critical_weakness',
        })
        total_confidence -= 15

        # Factor 5: Past recommendation accuracy
        past_accuracy = _get_recommendation_accuracy()
        if past_accuracy is not None:
            if past_accuracy > 70:
                contrib = 15
                status = 'strong'
            elif past_accuracy > 50:
                contrib = 8
                status = 'moderate'
            else:
                contrib = 3
                status = 'weak'
            factors.append({
                'factor': 'Track Record',
                'contribution': contrib,
                'description': f'Past recommendation accuracy: {past_accuracy:.0f}%',
                'status': status,
            })
            total_confidence += contrib
        else:
            factors.append({
                'factor': 'Track Record',
                'contribution': 0,
                'description': 'No past recommendations tracked yet',
                'status': 'no_data',
            })

        # Clamp confidence
        total_confidence = max(10, min(100, total_confidence))

        # Build data sources
        data_sources = [
            {'source': 'Price Forecast Model', 'freshness': 'Real-time', 'reliability': 'Low (dummy model)'},
            {'source': 'Mandi Prices', 'freshness': 'Simulated daily', 'reliability': 'Moderate (5 mandis)'},
            {'source': 'Weather Data', 'freshness': 'On-request', 'reliability': 'Moderate (OpenWeatherMap or mock)'},
            {'source': 'MSP Data', 'freshness': '2024-25 season', 'reliability': 'High (government published)'},
        ]

        # Build "why this advice"
        rec = recommendation.get('recommendation', 'HOLD')
        why = _build_why_explanation(recommendation, features, rec)

        # Build "what could go wrong"
        risks = _build_risk_factors(recommendation, features)

        # Similar past outcome
        past_outcome = _get_similar_past_outcome(
            recommendation.get('crop', 'Rice'),
            rec,
        )

        return {
            'confidence_score': total_confidence,
            'confidence_label': _confidence_label(total_confidence),
            'confidence_factors': factors,
            'data_sources': data_sources,
            'why_this_advice': why,
            'what_could_go_wrong': risks,
            'similar_past_outcome': past_outcome,
        }


def _confidence_label(score):
    if score >= 75:
        return 'High Confidence'
    elif score >= 50:
        return 'Moderate Confidence'
    elif score >= 30:
        return 'Low Confidence'
    else:
        return 'Very Low — Use With Caution'


def _count_price_history(crop, mandi):
    try:
        return PriceHistory.query.filter_by(crop=crop, mandi=mandi).count()
    except Exception:
        return 0


def _get_recommendation_accuracy():
    """Check if we have enough evaluation data to compute accuracy."""
    try:
        metrics = (
            EvaluationMetric.query
            .filter_by(metric_type='recommendation')
            .order_by(EvaluationMetric.recorded_at.desc())
            .limit(50)
            .all()
        )
        if len(metrics) < 5:
            return None
        correct = sum(1 for m in metrics if m.error == 0)
        return (correct / len(metrics)) * 100
    except Exception:
        return None


def _build_why_explanation(recommendation, features, rec):
    parts = []
    parts.append(f"We recommend {'holding your crop' if rec == 'HOLD' else 'selling now'} because:")

    # Price trend reason
    if features:
        momentum = features.get('price_momentum', {})
        if momentum.get('direction') == 'rising':
            parts.append(f"1) Prices rose {momentum.get('momentum_pct', 0)}% in the last 7 days")
        elif momentum.get('direction') == 'falling':
            parts.append(f"1) Prices fell {abs(momentum.get('momentum_pct', 0))}% in the last 7 days")
        else:
            parts.append("1) Prices have been stable recently")

        seasonal = features.get('seasonal_index', {})
        idx = seasonal.get('index', 1.0)
        if idx > 1.05:
            parts.append(f"2) Seasonal patterns show prices are {int((idx-1)*100)}% above annual average this month")
        elif idx < 0.95:
            parts.append(f"2) Seasonal patterns show prices are {int((1-idx)*100)}% below annual average (recovery expected)")
        else:
            parts.append("2) Seasonal prices are near average for this time of year")
    else:
        parts.append("1) Based on current market price and 90-day forecast")

    # Revenue reason
    extra = recommendation.get('extra_profit', 0)
    wait = recommendation.get('wait_days', 0)
    if rec == 'HOLD' and extra > 0:
        parts.append(f"3) Waiting ~{wait} days could earn ₹{extra:,.0f} more")
    elif rec == 'SELL NOW':
        risk = recommendation.get('risk_level', 'LOW')
        if risk == 'HIGH':
            parts.append("3) Market volatility is high — selling now reduces your risk")
        else:
            parts.append("3) Current price is near the forecasted peak")

    return " ".join(parts)


def _build_risk_factors(recommendation, features):
    risks = []

    risk_level = recommendation.get('risk_level', 'LOW')
    if risk_level == 'HIGH':
        risks.append("Market is volatile — prices could drop unexpectedly")
    elif risk_level == 'MEDIUM':
        risks.append("Some price fluctuation expected — prices may not follow forecast exactly")

    if features:
        rainfall = features.get('rainfall_anomaly', {})
        if rainfall.get('interpretation') == 'excess_rainfall':
            risks.append(f"Excess rainfall detected (+{rainfall.get('anomaly_pct', 0)}%) — crop quality/transport may be affected")
        elif rainfall.get('interpretation') == 'deficit':
            risks.append("Below-normal rainfall — supply shortage could spike prices but also hurt crop quality")

        arrivals = features.get('arrival_pressure', {})
        if arrivals.get('interpretation') == 'high_pressure':
            risks.append("High market arrivals detected — oversupply may push prices down")

    # Always note the model limitation
    risks.append("Forecast uses placeholder ML model — accuracy improves with real trained models")

    if not risks:
        risks.append("No significant risk factors identified")

    return risks


def _get_similar_past_outcome(crop, recommendation_type):
    """Look for similar past recommendations and their outcomes."""
    try:
        past = (
            EvaluationMetric.query
            .filter_by(metric_type='recommendation', entity_id=f'{crop}_{recommendation_type}')
            .filter(EvaluationMetric.actual_value.isnot(None))
            .order_by(EvaluationMetric.recorded_at.desc())
            .limit(10)
            .all()
        )
        if not past:
            return "No historical data yet. As more farmers use the system, we'll show how similar advice performed."

        successful = sum(1 for p in past if p.error == 0)
        rate = (successful / len(past)) * 100
        return f"In {len(past)} similar past situations, this advice was correct {rate:.0f}% of the time."
    except Exception:
        return "Historical comparison not available yet."
