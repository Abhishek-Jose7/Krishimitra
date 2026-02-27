"""
Evaluation Routes — Model accuracy and recommendation metrics

GET /metrics/evaluation              — Full evaluation dashboard
GET /metrics/accuracy/<metric_type>  — Specific metric accuracy
POST /metrics/track                  — Record a prediction outcome
GET /metrics/scheduler               — Background scheduler status
"""

from flask import Blueprint, request, jsonify
from services.evaluation_service import EvaluationService

evaluation_bp = Blueprint('evaluation', __name__, url_prefix='/metrics')


@evaluation_bp.route('/evaluation', methods=['GET'])
def evaluation_dashboard():
    """Returns comprehensive evaluation metrics."""
    return jsonify(EvaluationService.get_evaluation_dashboard())


@evaluation_bp.route('/accuracy/<metric_type>', methods=['GET'])
def accuracy(metric_type):
    """Returns accuracy for a specific metric type (price_forecast, yield_prediction, recommendation)."""
    days = request.args.get('days', 30, type=int)
    result = EvaluationService.forecast_accuracy(metric_type, days)
    return jsonify(result)


@evaluation_bp.route('/track', methods=['POST'])
def track_prediction():
    """Record a prediction vs actual comparison."""
    data = request.json
    metric_type = data.get('metric_type')
    entity_id = data.get('entity_id')
    predicted = data.get('predicted_value')
    actual = data.get('actual_value')

    if not all([metric_type, predicted is not None, actual is not None]):
        return jsonify({'error': 'metric_type, predicted_value, and actual_value are required'}), 400

    result = EvaluationService.track_prediction(
        metric_type=metric_type,
        entity_id=entity_id,
        predicted=float(predicted),
        actual=float(actual),
        context=data.get('context'),
    )
    return jsonify({'metric': result}), 201


@evaluation_bp.route('/scheduler', methods=['GET'])
def scheduler_status():
    """Returns background scheduler job status."""
    try:
        from services.scheduler import get_scheduler_status
        return jsonify(get_scheduler_status())
    except Exception as e:
        return jsonify({'error': str(e), 'running': False})
