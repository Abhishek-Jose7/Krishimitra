from flask import Blueprint, request, jsonify
from services.farmer_service import FarmerService
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.price_service import PriceService
from database.models import Farmer, YieldPrediction
import datetime

farmer_bp = Blueprint('farmer_bp', __name__)

@farmer_bp.route('/farmer/register', methods=['POST'])
def register_farmer():
    data = request.json
    result = FarmerService.create_farmer(data)
    if not isinstance(result, dict) or "error" in result:
        return jsonify(result), 400
    return jsonify(result), 201

# Backward compatibility or alternate path
@farmer_bp.route('/farmer_profile', methods=['POST'])
def create_profile():
    return register_farmer()

@farmer_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard():
    current_user_id = get_jwt_identity()
    farmer = FarmerService.get_farmer(current_user_id)
    
    if not farmer:
        return jsonify({"error": "Farmer not found"}), 404
        
    # Get Market Summary
    crop = farmer.get('preferred_crop', 'Rice')
    mandi = farmer.get('preferred_mandi', 'Pune')
    
    # Ensure inputs are valid strings for the service
    if not crop: crop = 'Rice'
    if not mandi: mandi = 'Pune'

    price_data = PriceService.forecast_price({'crop': crop, 'mandi': mandi})
    
    # Get last yield prediction if exists
    last_prediction = YieldPrediction.query.filter_by(farmer_id=current_user_id).order_by(YieldPrediction.prediction_date.desc()).first()
    prediction_data = None
    if last_prediction:
        prediction_data = {
            "predicted_yield": last_prediction.predicted_yield,
            "date": last_prediction.prediction_date.isoformat()
        }

    return jsonify({
        "farmer": farmer,
        "market_summary": {
            "current_price": price_data['current_price'],
            "trend": price_data['trend'],
            "volatility": price_data.get('volatility', 0.1),
            "last_updated": datetime.date.today().isoformat()
        },
        "last_prediction": prediction_data
    })
    
@farmer_bp.route('/farmer/<int:id>', methods=['GET'])
def get_profile(id):
    result = FarmerService.get_farmer(id)
    if result:
        return jsonify(result), 200
    return jsonify({"error": "Farmer not found"}), 404
