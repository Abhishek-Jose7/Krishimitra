"""
AI Overseer Service — Meta-Layer Above Models  (v1.1)

Sits ABOVE yield, price, and recommendation models.
Does NOT replace them. Instead:
  - Evaluates outputs for anomalies
  - Cross-validates predictions against simple baselines
  - Detects model drift AND reacts (forces conservative decisions)
  - Adjusts confidence: CLAMPED to 40–95% (never 0, never 100)
  - Overrides dangerous advice for perishables
  - Logs every decision to DB audit trail
  - Communicates in risk language, not percentages

Architecture:  Models → Overseer → Final Advice

v1.1 changes:
  - FIX 1: Confidence clamped 0.40–0.95 (no paralysis, no overconfidence)
  - FIX 3: OverseerLog DB audit trail for every decision
  - FIX 4: Risk-language communication (not raw percentages)
  - FIX 5: Drift causes behavioral changes (short horizon + conservative)
"""

import datetime
import json
import logging
import math
from database.db import db
from database.models import PriceHistory, EvaluationMetric, OverseerLog

logger = logging.getLogger('overseer')

# Confidence bounds — NEVER exceed these
CONFIDENCE_FLOOR = 0.40   # Avoids "0% confidence" paralysis
CONFIDENCE_CEILING = 0.95  # Avoids dangerous overconfidence

# Model version registry — tracks what models are active
MODEL_REGISTRY = {
    'yield_model': {'version': '0.1-dummy', 'type': 'pickle', 'trained_on': 'synthetic', 'last_updated': '2026-02-21'},
    'price_forecast_model': {'version': '0.1-dummy', 'type': 'pickle', 'trained_on': 'synthetic', 'last_updated': '2026-02-21'},
    'recommendation_engine': {'version': '2.0', 'type': 'rule-based', 'trained_on': 'n/a', 'last_updated': '2026-02-21'},
    'overseer': {'version': '1.1', 'type': 'deterministic', 'trained_on': 'n/a', 'last_updated': '2026-02-22'},
}

# Risk language mapping — farmers think in risk, not percentages
RISK_LANGUAGE = {
    (0.85, 1.00): {'label': 'High reliability', 'farmer_msg': 'This prediction is based on strong data and consistent patterns'},
    (0.70, 0.85): {'label': 'Good reliability', 'farmer_msg': 'This prediction is fairly reliable, with some minor uncertainties'},
    (0.55, 0.70): {'label': 'Moderate reliability', 'farmer_msg': 'This prediction has noticeable uncertainty — consider checking with local traders'},
    (0.40, 0.55): {'label': 'Limited reliability', 'farmer_msg': 'This prediction has significant uncertainty — verify with mandi contacts before acting'},
}


def _confidence_to_risk_language(score):
    """Convert raw confidence score to farmer-friendly risk language."""
    for (low, high), lang in RISK_LANGUAGE.items():
        if low <= score < high:
            return lang
    if score >= 1.0:
        return RISK_LANGUAGE[(0.85, 1.00)]
    return RISK_LANGUAGE[(0.40, 0.55)]


class Overseer:
    """
    Deterministic AI oversight layer.
    Every check is transparent, explainable, and auditable.
    No black-box decisions — every flag has a clear reason.
    """

    @staticmethod
    def evaluate(recommendation_data, forecast_data=None, features=None, farmer_id=None):
        """
        Main entry point. Takes raw recommendation output and returns
        an oversight verdict with adjusted confidence, warnings, and
        potential overrides.

        Returns:
        {
            adjusted_confidence: float (0.40–0.95, CLAMPED),
            confidence_risk_label: str (farmer-friendly),
            confidence_risk_message: str (plain English),
            warnings: [{ code, severity, message, detail }],
            overrides: [{ field, old_value, new_value, reason }],
            drift_action: { ... } or None,
            anomalies_detected: int,
            drift_status: { ... },
            model_versions: { ... },
            verdict: 'APPROVED' | 'APPROVED_WITH_WARNINGS' | 'OVERRIDDEN' | 'FLAGGED',
        }
        """
        score = CONFIDENCE_CEILING  # Start at ceiling, not 1.0
        warnings = []
        overrides = []
        anomalies = 0
        drift_action = None

        crop = recommendation_data.get('crop', 'Rice')
        current_price = recommendation_data.get('current_price_per_quintal', 0)
        peak_price = recommendation_data.get('peak_price_per_quintal', 0)
        wait_days = recommendation_data.get('wait_days', 0)
        risk_level = recommendation_data.get('risk_level', 'LOW')
        recommendation = recommendation_data.get('recommendation', 'HOLD')
        mandi = recommendation_data.get('mandi', 'Pune Mandi')

        # ═══════════════════════════════════════
        # CHECK 1: Anomaly Detection
        # ═══════════════════════════════════════
        anomaly_result = _check_anomalies(current_price, peak_price, wait_days, forecast_data)
        score -= anomaly_result['penalty']
        warnings.extend(anomaly_result['warnings'])
        anomalies += anomaly_result['count']

        # ═══════════════════════════════════════
        # CHECK 2: Model Cross-Validation
        # ═══════════════════════════════════════
        crossval_result = _cross_validate_forecast(crop, current_price, peak_price, wait_days)
        score -= crossval_result['penalty']
        warnings.extend(crossval_result['warnings'])

        # ═══════════════════════════════════════
        # CHECK 3: Perishable Risk Amplification
        # ═══════════════════════════════════════
        perishable_result = _check_perishable_risk(crop, recommendation, wait_days, risk_level)
        score -= perishable_result['penalty']
        warnings.extend(perishable_result['warnings'])
        if perishable_result.get('override'):
            overrides.append(perishable_result['override'])

        # ═══════════════════════════════════════
        # CHECK 4: Data Quality & Completeness
        # ═══════════════════════════════════════
        quality_result = _check_data_quality(features, recommendation_data)
        score -= quality_result['penalty']
        warnings.extend(quality_result['warnings'])

        # ═══════════════════════════════════════
        # CHECK 5: Drift Monitoring + REACTION
        # ═══════════════════════════════════════
        drift_result = _detect_drift(crop, mandi)

        if drift_result['drift_detected']:
            score -= 0.1
            warnings.append({
                'code': 'DRIFT_DETECTED',
                'severity': 'medium',
                'message': 'Price pattern may have shifted from historical norms',
                'detail': drift_result['detail'],
            })

            # FIX 5: Drift REACTION — don't just reduce confidence, change behavior
            drift_action = _react_to_drift(drift_result, recommendation, wait_days, crop)
            if drift_action.get('override'):
                overrides.append(drift_action['override'])
            warnings.extend(drift_action.get('warnings', []))

        # ═══════════════════════════════════════
        # CHECK 6: Historical Accuracy Self-Check
        # ═══════════════════════════════════════
        accuracy_result = _check_historical_accuracy(crop)
        score -= accuracy_result['penalty']
        warnings.extend(accuracy_result['warnings'])

        # ═══════════════════════════════════════
        # FIX 1: CLAMP confidence to safe range
        # Never 0% (paralysis) or 100% (overconfidence)
        # ═══════════════════════════════════════
        adjusted_confidence = max(CONFIDENCE_FLOOR, min(CONFIDENCE_CEILING, score))

        # FIX 4: Convert to risk language
        risk_lang = _confidence_to_risk_language(adjusted_confidence)

        # Determine verdict
        if overrides:
            verdict = 'OVERRIDDEN'
        elif anomalies >= 2 or adjusted_confidence < 0.5:
            verdict = 'FLAGGED'
        elif warnings:
            verdict = 'APPROVED_WITH_WARNINGS'
        else:
            verdict = 'APPROVED'

        oversight = {
            'adjusted_confidence': round(adjusted_confidence, 3),
            'original_confidence': CONFIDENCE_CEILING,
            'confidence_delta': round(adjusted_confidence - CONFIDENCE_CEILING, 3),
            # FIX 4: Risk language instead of raw percentages
            'confidence_risk_label': risk_lang['label'],
            'confidence_risk_message': risk_lang['farmer_msg'],
            'warnings': warnings,
            'warning_count': len(warnings),
            'overrides': overrides,
            'anomalies_detected': anomalies,
            'drift_status': drift_result,
            'drift_action': drift_action,
            'model_versions': MODEL_REGISTRY,
            'verdict': verdict,
            'verdict_emoji': _verdict_emoji(verdict),
            'overseer_version': MODEL_REGISTRY['overseer']['version'],
        }

        # Log the oversight result
        logger.info(f"Overseer verdict: {verdict} | confidence: {adjusted_confidence:.2f} | "
                     f"warnings: {len(warnings)} | anomalies: {anomalies} | crop: {crop}")

        # ═══════════════════════════════════════
        # FIX 3: Persist audit trail to DB
        # ═══════════════════════════════════════
        final_decision = recommendation
        override_reason = None
        for o in overrides:
            if o['field'] == 'recommendation':
                final_decision = o['new_value']
                override_reason = o['reason']

        _log_to_db(
            farmer_id=farmer_id,
            crop=crop,
            mandi=mandi,
            original_decision=recommendation,
            final_decision=final_decision,
            reason=override_reason,
            verdict=verdict,
            confidence_before=CONFIDENCE_CEILING,
            confidence_after=adjusted_confidence,
            warning_count=len(warnings),
            anomaly_count=anomalies,
            drift_detected=drift_result.get('drift_detected', False),
            warnings_list=warnings,
        )

        return oversight


# ═══════════════════════════════════════════════════
# FIX 3: AUDIT LOGGING
# ═══════════════════════════════════════════════════

def _log_to_db(farmer_id, crop, mandi, original_decision, final_decision,
               reason, verdict, confidence_before, confidence_after,
               warning_count, anomaly_count, drift_detected, warnings_list):
    """Persist every overseer decision to the audit trail."""
    try:
        log_entry = OverseerLog(
            farmer_id=farmer_id,
            crop=crop,
            mandi=mandi,
            original_decision=original_decision,
            final_decision=final_decision,
            reason=reason,
            verdict=verdict,
            confidence_before=confidence_before,
            confidence_after=confidence_after,
            warning_count=warning_count,
            anomaly_count=anomaly_count,
            drift_detected=drift_detected,
            warnings_json=json.dumps(warnings_list, default=str),
        )
        db.session.add(log_entry)
        db.session.commit()
        logger.info(f"Overseer log #{log_entry.id} saved: {verdict} for {crop}")
    except Exception as e:
        logger.warning(f"Failed to save overseer log: {e}")
        db.session.rollback()


# ═══════════════════════════════════════════════════
# FIX 5: DRIFT REACTION — behavioral changes
# ═══════════════════════════════════════════════════

def _react_to_drift(drift_result, recommendation, wait_days, crop):
    """
    When drift is detected, don't just reduce confidence.
    Force SHORT-TERM HORIZON and CONSERVATIVE decision.
    """
    action = {'warnings': [], 'override': None}
    shift_pct = drift_result.get('shift_pct', 0)
    direction = drift_result.get('direction', 'unknown')

    # If significant upward drift + recommending HOLD: cap hold to 14 days
    if shift_pct > 15 and recommendation == 'HOLD' and wait_days > 14:
        action['override'] = {
            'field': 'wait_days',
            'old_value': wait_days,
            'new_value': 14,
            'reason': f'Drift detected ({shift_pct:.0f}% {direction} shift). '
                      f'Reducing forecast horizon from {wait_days} to 14 days for safety.',
        }
        action['warnings'].append({
            'code': 'DRIFT_HORIZON_REDUCED',
            'severity': 'high',
            'message': f'Forecast horizon reduced from {wait_days} to 14 days due to market shift',
            'detail': f'A {shift_pct:.0f}% {direction} price shift was detected. '
                      f'Long-term predictions are unreliable during regime changes. '
                      f'Reassess in 14 days.',
        })

    # If significant downward drift + recommending HOLD: force SELL
    if shift_pct > 15 and direction == 'downward' and recommendation == 'HOLD':
        action['override'] = {
            'field': 'recommendation',
            'old_value': 'HOLD',
            'new_value': 'SELL NOW',
            'reason': f'Drift detected: prices have dropped {shift_pct:.0f}% in the last week. '
                      f'Holding {crop} during a downward shift risks further losses.',
        }
        action['warnings'].append({
            'code': 'DRIFT_FORCED_SELL',
            'severity': 'critical',
            'message': f'⚠️ Market downtrend detected — overseer recommends selling {crop} now',
            'detail': f'Prices have shifted {shift_pct:.0f}% downward. '
                      f'Continuing to hold is risky in a falling market.',
        })

    # Conservative advice in any drift scenario
    if shift_pct > 10:
        action['warnings'].append({
            'code': 'DRIFT_CONSERVATIVE_MODE',
            'severity': 'medium',
            'message': 'Market conditions are shifting — advice is set to conservative mode',
            'detail': 'During market regime changes, the system automatically favors '
                      'lower-risk decisions and shorter forecast windows.',
        })

    return action


# ═══════════════════════════════════════════════════
# INDIVIDUAL CHECK FUNCTIONS
# ═══════════════════════════════════════════════════

def _check_anomalies(current_price, peak_price, wait_days, forecast_data):
    """Flags unrealistic predictions."""
    penalty = 0
    warnings = []
    count = 0

    if current_price > 0:
        price_jump_pct = ((peak_price - current_price) / current_price) * 100

        # Anomaly 1: Unrealistic spike (>20% in forecast window)
        if price_jump_pct > 20:
            penalty += 0.15
            count += 1
            warnings.append({
                'code': 'UNREALISTIC_SPIKE',
                'severity': 'high',
                'message': f'Predicted {price_jump_pct:.0f}% price increase — unusually high',
                'detail': f'Current: ₹{current_price:.0f}, Peak: ₹{peak_price:.0f}. '
                          f'Jumps >20% are rare and often model artifacts.',
            })

        # Anomaly 2: Price predicted to drop >15%
        if price_jump_pct < -15:
            penalty += 0.10
            count += 1
            warnings.append({
                'code': 'SHARP_DECLINE_PREDICTED',
                'severity': 'high',
                'message': f'Predicted {abs(price_jump_pct):.0f}% price drop',
                'detail': 'Sharp declines this large are unusual. Verify with real market data.',
            })

    # Anomaly 3: Very long hold recommendation (>60 days)
    if wait_days > 60:
        penalty += 0.08
        count += 1
        warnings.append({
            'code': 'EXCESSIVE_HOLD_PERIOD',
            'severity': 'medium',
            'message': f'Hold period of {wait_days} days is very long',
            'detail': 'Predictions beyond 60 days are highly uncertain. Reassess periodically.',
        })

    # Anomaly 4: Forecast volatility check
    if forecast_data and 'forecast' in forecast_data:
        prices = [p['price'] for p in forecast_data['forecast']]
        if prices:
            import numpy as np
            std = float(np.std(prices))
            mean = float(np.mean(prices))
            cv = std / mean if mean > 0 else 0

            if cv > 0.15:
                penalty += 0.08
                count += 1
                warnings.append({
                    'code': 'HIGH_FORECAST_VARIANCE',
                    'severity': 'medium',
                    'message': f'Forecast shows high variance (CV={cv:.2f})',
                    'detail': 'Wide price swings in the forecast suggest unstable predictions.',
                })

    return {'penalty': penalty, 'warnings': warnings, 'count': count}


def _cross_validate_forecast(crop, current_price, peak_price, wait_days):
    """
    Compare model forecast against simple rolling average baseline.
    If they diverge wildly, reduce confidence.
    """
    penalty = 0
    warnings = []

    try:
        cutoff = datetime.date.today() - datetime.timedelta(days=30)
        history = (
            PriceHistory.query
            .filter_by(crop=crop)
            .filter(PriceHistory.date >= cutoff)
            .order_by(PriceHistory.date.asc())
            .all()
        )

        if len(history) >= 7:
            actual_prices = [h.price for h in history]
            rolling_trend = (actual_prices[-1] - actual_prices[0]) / actual_prices[0] * 100 if actual_prices[0] > 0 else 0

            daily_rate = rolling_trend / 30
            baseline_peak = current_price * (1 + (daily_rate * wait_days / 100))

            if peak_price > 0 and baseline_peak > 0:
                divergence = abs(peak_price - baseline_peak) / baseline_peak * 100

                if divergence > 25:
                    penalty += 0.10
                    warnings.append({
                        'code': 'FORECAST_BASELINE_DIVERGENCE',
                        'severity': 'medium',
                        'message': f'Model forecast diverges {divergence:.0f}% from rolling average trend',
                        'detail': f'Model predicts ₹{peak_price:.0f}, rolling average suggests ₹{baseline_peak:.0f}.',
                    })
        else:
            warnings.append({
                'code': 'INSUFFICIENT_CROSSVAL_DATA',
                'severity': 'low',
                'message': 'Not enough historical data for forecast cross-validation',
                'detail': f'Only {len(history)} data points. Need 7+ for rolling average comparison.',
            })

    except Exception as e:
        logger.warning(f"Cross-validation check failed: {e}")

    return {'penalty': penalty, 'warnings': warnings}


def _check_perishable_risk(crop, recommendation, wait_days, risk_level):
    """
    For perishable crops (Onion, Sugarcane), amplify risk.
    Can override HOLD → SELL if danger is too high.
    """
    PERISHABLE_CROPS = {
        'Onion': {'max_safe_days': 14, 'risk_multiplier': 2.5},
        'Sugarcane': {'max_safe_days': 3, 'risk_multiplier': 4.0},
        'Tomato': {'max_safe_days': 7, 'risk_multiplier': 3.0},
    }

    penalty = 0
    warnings = []
    override = None

    perishable = PERISHABLE_CROPS.get(crop)
    if not perishable:
        return {'penalty': 0, 'warnings': [], 'override': None}

    max_days = perishable['max_safe_days']

    if wait_days > max_days * 0.5:
        penalty += 0.10
        warnings.append({
            'code': 'PERISHABLE_HOLD_RISK',
            'severity': 'high',
            'message': f'{crop} is perishable — holding {wait_days} days is risky (max safe: {max_days} days)',
            'detail': f'{crop} quality degrades rapidly. Storage beyond {max_days} days risks significant spoilage.',
        })

    if recommendation == 'HOLD' and wait_days > max_days:
        override = {
            'field': 'recommendation',
            'old_value': 'HOLD',
            'new_value': 'SELL NOW',
            'reason': f'Overseer override: {crop} cannot be safely stored for {wait_days} days '
                      f'(max safe storage: {max_days} days). Selling now prevents spoilage losses.',
        }
        penalty += 0.15
        warnings.append({
            'code': 'PERISHABLE_OVERRIDE',
            'severity': 'critical',
            'message': f'⚠️ Overseer overriding HOLD → SELL for {crop}',
            'detail': override['reason'],
        })

    if risk_level == 'HIGH':
        penalty += 0.05 * perishable['risk_multiplier']
        warnings.append({
            'code': 'PERISHABLE_HIGH_VOLATILITY',
            'severity': 'high',
            'message': f'{crop} + high volatility = very risky combination',
            'detail': 'Perishable crops with volatile prices should be sold quickly.',
        })

    return {'penalty': penalty, 'warnings': warnings, 'override': override}


def _check_data_quality(features, recommendation_data):
    """Checks if the underlying data is sufficient for reliable advice."""
    penalty = 0
    warnings = []

    if not features:
        penalty += 0.10
        warnings.append({
            'code': 'NO_FEATURES_COMPUTED',
            'severity': 'medium',
            'message': 'Advanced features not available for this prediction',
            'detail': 'Without historical momentum, seasonal indices, and arrival data, advice quality is lower.',
        })
        return {'penalty': penalty, 'warnings': warnings}

    momentum = features.get('price_momentum', {})
    if momentum.get('data_points', 0) < 3:
        penalty += 0.05
        warnings.append({
            'code': 'SPARSE_PRICE_DATA',
            'severity': 'medium',
            'message': f"Only {momentum.get('data_points', 0)} price data points for momentum",
            'detail': 'Need at least 7 days of price history for reliable momentum calculation.',
        })

    seasonal = features.get('seasonal_index', {})
    if seasonal.get('interpretation') == 'default_pattern':
        penalty += 0.03
        warnings.append({
            'code': 'DEFAULT_SEASONAL_DATA',
            'severity': 'low',
            'message': 'Using default seasonal patterns instead of actual historical data',
            'detail': 'Seasonal adjustments are generic. They will improve as more data is collected.',
        })

    rainfall = features.get('rainfall_anomaly', {})
    if rainfall.get('interpretation') == 'no_data':
        penalty += 0.03
        warnings.append({
            'code': 'NO_WEATHER_HISTORY',
            'severity': 'low',
            'message': 'No historical weather data for anomaly detection',
            'detail': 'Weather impact on prices cannot be assessed without historical baselines.',
        })

    return {'penalty': penalty, 'warnings': warnings}


def _detect_drift(crop, mandi):
    """
    Simple distribution shift detection.
    Compares recent 7-day price distribution vs last 30 days.
    """
    try:
        now = datetime.date.today()
        recent_7 = now - datetime.timedelta(days=7)
        recent_30 = now - datetime.timedelta(days=30)

        recent_prices = (
            PriceHistory.query
            .filter_by(crop=crop, mandi=mandi)
            .filter(PriceHistory.date >= recent_7)
            .all()
        )

        baseline_prices = (
            PriceHistory.query
            .filter_by(crop=crop, mandi=mandi)
            .filter(PriceHistory.date >= recent_30, PriceHistory.date < recent_7)
            .all()
        )

        if len(recent_prices) < 3 or len(baseline_prices) < 5:
            return {
                'drift_detected': False,
                'detail': 'Insufficient data for drift detection',
                'recent_mean': None,
                'baseline_mean': None,
            }

        recent_mean = sum(p.price for p in recent_prices) / len(recent_prices)
        baseline_mean = sum(p.price for p in baseline_prices) / len(baseline_prices)

        shift_pct = abs(recent_mean - baseline_mean) / baseline_mean * 100 if baseline_mean > 0 else 0
        drift_detected = shift_pct > 10

        direction = 'upward' if recent_mean > baseline_mean else 'downward'

        return {
            'drift_detected': drift_detected,
            'shift_pct': round(shift_pct, 1),
            'direction': direction,
            'recent_mean': round(recent_mean, 2),
            'baseline_mean': round(baseline_mean, 2),
            'detail': f"{'Significant' if drift_detected else 'Minor'} {direction} shift of {shift_pct:.1f}% detected"
                      f" (recent avg: ₹{recent_mean:.0f} vs baseline: ₹{baseline_mean:.0f})",
        }

    except Exception as e:
        logger.warning(f"Drift detection failed: {e}")
        return {'drift_detected': False, 'detail': f'Drift check error: {str(e)}'}


def _check_historical_accuracy(crop):
    """Self-assessment: how accurate have our past predictions been?"""
    penalty = 0
    warnings = []

    try:
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=90)
        metrics = (
            EvaluationMetric.query
            .filter_by(metric_type='price_forecast')
            .filter(EvaluationMetric.entity_id.contains(crop))
            .filter(EvaluationMetric.recorded_at >= cutoff)
            .filter(EvaluationMetric.error_pct.isnot(None))
            .all()
        )

        if not metrics:
            warnings.append({
                'code': 'NO_ACCURACY_HISTORY',
                'severity': 'low',
                'message': 'No past accuracy data available for self-assessment',
                'detail': 'As predictions are tracked and actuals submitted, accuracy will be monitored.',
            })
            return {'penalty': 0, 'warnings': warnings}

        avg_error = sum(m.error_pct for m in metrics) / len(metrics)

        if avg_error > 25:
            penalty += 0.15
            warnings.append({
                'code': 'HIGH_HISTORICAL_ERROR',
                'severity': 'high',
                'message': f'Past predictions for {crop} had {avg_error:.0f}% average error',
                'detail': f'Model has been inaccurate for {crop}. Treat advice with extra caution.',
            })
        elif avg_error > 15:
            penalty += 0.08
            warnings.append({
                'code': 'MODERATE_HISTORICAL_ERROR',
                'severity': 'medium',
                'message': f'Past predictions for {crop} had {avg_error:.0f}% average error',
                'detail': 'Moderate accuracy. Consider this when interpreting advice.',
            })

    except Exception as e:
        logger.warning(f"Historical accuracy check failed: {e}")

    return {'penalty': penalty, 'warnings': warnings}


def _verdict_emoji(verdict):
    return {
        'APPROVED': '✅',
        'APPROVED_WITH_WARNINGS': '⚠️',
        'OVERRIDDEN': '🔴',
        'FLAGGED': '🟡',
    }.get(verdict, '❓')
