"""
Evaluation Service — Tracking Prediction Accuracy & Recommendation Success

Provides metrics that answer:
- How accurate are our price forecasts?
- How accurate are yield predictions?
- How often do our recommendations lead to better outcomes?
- What's the estimated profit uplift from following advice?
"""

import datetime
import json
from database.db import db
from database.models import EvaluationMetric, YieldPrediction, PriceHistory


class EvaluationService:

    @staticmethod
    def track_prediction(metric_type, entity_id, predicted, actual, context=None):
        """
        Records a prediction-vs-actual comparison.
        metric_type: 'price_forecast', 'yield_prediction', 'recommendation'
        entity_id: e.g. 'Rice_PuneMandi', farmer_id, etc.
        """
        error = abs(predicted - actual) if predicted is not None and actual is not None else None
        error_pct = (error / actual * 100) if actual and actual != 0 and error is not None else None

        metric = EvaluationMetric(
            metric_type=metric_type,
            entity_id=str(entity_id),
            predicted_value=predicted,
            actual_value=actual,
            error=error,
            error_pct=error_pct,
            context_json=json.dumps(context) if context else None,
        )
        db.session.add(metric)
        db.session.commit()
        return metric.to_dict()

    @staticmethod
    def forecast_accuracy(metric_type='price_forecast', days=30):
        """
        Computes Mean Absolute Error (MAE) and Mean Absolute Percentage Error (MAPE)
        for forecasts recorded in the last N days.
        """
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)
        metrics = (
            EvaluationMetric.query
            .filter_by(metric_type=metric_type)
            .filter(EvaluationMetric.recorded_at >= cutoff)
            .filter(EvaluationMetric.actual_value.isnot(None))
            .all()
        )

        if not metrics:
            return {
                'metric_type': metric_type,
                'period_days': days,
                'sample_size': 0,
                'mae': None,
                'mape': None,
                'message': 'No evaluation data available yet. Submit actual values to start tracking.',
            }

        errors = [m.error for m in metrics if m.error is not None]
        error_pcts = [m.error_pct for m in metrics if m.error_pct is not None]

        mae = sum(errors) / len(errors) if errors else None
        mape = sum(error_pcts) / len(error_pcts) if error_pcts else None

        return {
            'metric_type': metric_type,
            'period_days': days,
            'sample_size': len(metrics),
            'mae': round(mae, 2) if mae is not None else None,
            'mape': round(mape, 2) if mape is not None else None,
            'interpretation': _interpret_mape(mape),
        }

    @staticmethod
    def recommendation_success_rate(days=90):
        """
        What % of HOLD recommendations saw a price increase?
        What % of SELL NOW recommendations were at/near peak?
        """
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)
        metrics = (
            EvaluationMetric.query
            .filter_by(metric_type='recommendation')
            .filter(EvaluationMetric.recorded_at >= cutoff)
            .filter(EvaluationMetric.actual_value.isnot(None))
            .all()
        )

        if not metrics:
            return {
                'period_days': days,
                'total_tracked': 0,
                'success_rate': None,
                'message': 'No recommendation outcomes tracked yet.',
            }

        # error == 0 means recommendation was correct (convention)
        correct = sum(1 for m in metrics if m.error == 0)
        rate = (correct / len(metrics)) * 100

        return {
            'period_days': days,
            'total_tracked': len(metrics),
            'successful': correct,
            'success_rate': round(rate, 1),
            'interpretation': _interpret_success_rate(rate),
        }

    @staticmethod
    def yield_prediction_accuracy():
        """
        Compares predicted vs actual yield from YieldPrediction table.
        Only considers records where actual_yield is filled in (farmer feedback).
        """
        predictions = (
            YieldPrediction.query
            .filter(YieldPrediction.actual_yield.isnot(None))
            .order_by(YieldPrediction.prediction_date.desc())
            .limit(100)
            .all()
        )

        if not predictions:
            return {
                'sample_size': 0,
                'mae': None,
                'mape': None,
                'message': 'No actual yield data submitted by farmers yet.',
            }

        errors = []
        pct_errors = []
        for p in predictions:
            error = abs(p.predicted_yield - p.actual_yield)
            errors.append(error)
            if p.actual_yield > 0:
                pct_errors.append(error / p.actual_yield * 100)

        mae = sum(errors) / len(errors)
        mape = sum(pct_errors) / len(pct_errors) if pct_errors else None

        return {
            'sample_size': len(predictions),
            'mae': round(mae, 2),
            'mape': round(mape, 2) if mape is not None else None,
            'interpretation': _interpret_mape(mape),
        }

    @staticmethod
    def profit_uplift(days=90):
        """
        Estimated extra earnings from following recommendations vs selling immediately.
        Uses tracked recommendation metrics where we know the outcome.
        """
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)
        metrics = (
            EvaluationMetric.query
            .filter_by(metric_type='recommendation')
            .filter(EvaluationMetric.recorded_at >= cutoff)
            .filter(EvaluationMetric.actual_value.isnot(None))
            .filter(EvaluationMetric.predicted_value.isnot(None))
            .all()
        )

        if not metrics:
            return {
                'period_days': days,
                'total_tracked': 0,
                'avg_uplift_pct': None,
                'message': 'No uplift data available yet.',
            }

        uplifts = []
        for m in metrics:
            if m.predicted_value > 0:
                uplift = ((m.actual_value - m.predicted_value) / m.predicted_value) * 100
                uplifts.append(uplift)

        avg_uplift = sum(uplifts) / len(uplifts) if uplifts else 0

        return {
            'period_days': days,
            'total_tracked': len(metrics),
            'avg_uplift_pct': round(avg_uplift, 2),
            'interpretation': f"On average, following recommendations {'gained' if avg_uplift > 0 else 'lost'} {abs(avg_uplift):.1f}% compared to immediate selling.",
        }

    @staticmethod
    def get_evaluation_dashboard():
        """Full evaluation summary."""
        return {
            'price_forecast_accuracy': EvaluationService.forecast_accuracy('price_forecast'),
            'yield_prediction_accuracy': EvaluationService.yield_prediction_accuracy(),
            'recommendation_success': EvaluationService.recommendation_success_rate(),
            'profit_uplift': EvaluationService.profit_uplift(),
            'generated_at': datetime.datetime.utcnow().isoformat(),
        }


def _interpret_mape(mape):
    if mape is None:
        return 'No data'
    if mape < 10:
        return 'Excellent accuracy'
    elif mape < 20:
        return 'Good accuracy'
    elif mape < 30:
        return 'Fair accuracy — room for improvement'
    else:
        return 'Poor accuracy — model needs retraining'


def _interpret_success_rate(rate):
    if rate >= 80:
        return 'Excellent — recommendations are highly reliable'
    elif rate >= 60:
        return 'Good — most recommendations are correct'
    elif rate >= 40:
        return 'Fair — about as good as a coin flip'
    else:
        return 'Poor — recommendations need significant improvement'
