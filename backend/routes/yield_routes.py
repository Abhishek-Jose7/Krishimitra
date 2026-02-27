from flask import Blueprint, request, jsonify
from services.yield_service import YieldService
from services.farmer_service import FarmerService
from flask_jwt_extended import jwt_required, get_jwt_identity
from database.models import YieldPrediction
from database.db import db

yield_bp = Blueprint('yield_bp', __name__)

@yield_bp.route('/yield/predict', methods=['POST'])
@jwt_required(optional=True)
def predict_yield():
    data = request.json
    if not data:
        return jsonify({"error": "No input data provided"}), 400

    # ── Load context from farm_crop_id if provided ──
    farm_crop_id = data.get('farm_crop_id')
    if farm_crop_id:
        ctx = FarmerService.get_crop_context(farm_crop_id)
        if ctx:
            # Merge DB context into the request data (request data can override)
            for key in ['crop', 'district', 'state', 'land_size', 'soil_type',
                        'irrigation_type', 'sowing_date']:
                if key not in data or data[key] is None:
                    data[key] = ctx.get(key)
            data['farm_crop_id'] = farm_crop_id

    # Inject farmer_id if logged in
    try:
        current_user_id = get_jwt_identity()
        if current_user_id:
            data['farmer_id'] = current_user_id
    except:
        pass

    result = YieldService.predict_yield(data)
    if result:
        return jsonify(result), 200
    return jsonify({"error": "Prediction failed"}), 500

@yield_bp.route('/yield/actual', methods=['POST'])
@jwt_required()
def submit_actual_yield():
    data = request.json
    current_user_id = get_jwt_identity()

    actual_yield = data.get('actual_production')
    if not actual_yield:
         return jsonify({"error": "Actual production is required"}), 400

    # Try to find prediction by farm_crop_id first, then by farmer_id
    farm_crop_id = data.get('farm_crop_id')
    last_prediction = None

    if farm_crop_id:
        last_prediction = YieldPrediction.query.filter_by(
            farm_crop_id=farm_crop_id
        ).order_by(YieldPrediction.prediction_date.desc()).first()

    if not last_prediction:
        last_prediction = YieldPrediction.query.filter_by(
            farmer_id=current_user_id
        ).order_by(YieldPrediction.prediction_date.desc()).first()

    if last_prediction:
        last_prediction.actual_yield = float(actual_yield)
        db.session.commit()
        return jsonify({"success": True, "message": "Feedback recorded, model will retrain."}), 200
    else:
        return jsonify({"error": "No prior prediction found to validate against."}), 404
