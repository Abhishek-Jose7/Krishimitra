from flask import Blueprint, request, jsonify
from services.yield_service import get_yield_advisory, get_yield_options, YieldService
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


@yield_bp.route('/yield/simulate', methods=['POST'])
@jwt_required(optional=True)
def simulate_yield():
    """
    Run the Mysuru smart-yield simulation pipeline and return
    a plain-text advisory for the given configuration.

    Request JSON body:
      {
        "district": "...",
        "crop": "...",
        "season": "...",
        "soil_type": "...",
        "irrigation": "...",
        "area": 1.5
      }
    """
    data = request.json or {}
    try:
        payload = get_yield_advisory(data)
        advisory = payload.get("advisory", "")
        summary = payload.get("summary")
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400
    except Exception as exc:  # pragma: no cover - defensive
        # Log but do not leak internals to clients
        print(f"Yield simulation failed: {exc}")
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Yield simulation failed. Please try again later.",
                }
            ),
            500,
        )

    return jsonify({"status": "success", "advisory": advisory, "summary": summary}), 200


@yield_bp.route('/yield/options', methods=['GET'])
def yield_options():
    """
    Return dynamic option lists (district, crop, season, soil_type, irrigation, area)
    backed by mysuru_agri_ai datasets.
    """
    district = request.args.get("district") or "Mysuru"
    try:
        opts = get_yield_options(district)
    except Exception as exc:  # pragma: no cover - defensive
        print(f"Failed to load yield options: {exc}")
        return jsonify({"error": "Failed to load yield options"}), 500
    return jsonify(opts), 200

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
