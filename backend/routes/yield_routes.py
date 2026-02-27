from flask import Blueprint, request, jsonify
from services.yield_service import YieldService
from flask_jwt_extended import jwt_required, get_jwt_identity
from database.models import YieldPrediction
from database.db import db

yield_bp = Blueprint('yield_bp', __name__)

@yield_bp.route('/yield/predict', methods=['POST'])
@jwt_required(optional=True) # Optional for now to allow testing without login if needed, or strict. User said "Now user is authenticated" so let's try to get ID.
def predict_yield():
    data = request.json
    if not data:
        return jsonify({"error": "No input data provided"}), 400
    
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
    
    actual_yield = data.get('actual_production') # in tons/total
    if not actual_yield:
         return jsonify({"error": "Actual production is required"}), 400

    # Find the most recent prediction for this user? Or user selects one?
    # Simple logic: Update the latest prediction or just create a record.
    # If we want to "Mark prediction error", we should find the prediction.
    
    last_prediction = YieldPrediction.query.filter_by(farmer_id=current_user_id).order_by(YieldPrediction.prediction_date.desc()).first()
    
    if last_prediction:
        last_prediction.actual_yield = float(actual_yield)
        db.session.commit()
        return jsonify({"success": True, "message": "Feedback recorded, model will retrain."}), 200
    else:
        # Create a new record just for actuals? OR return error.
        return jsonify({"error": "No prior prediction found to validate against."}), 404
