from flask import Blueprint, request, jsonify
from services.recommendation_service import RecommendationService
from services.farmer_service import FarmerService

recommendation_bp = Blueprint('recommendation_bp', __name__)

@recommendation_bp.route('/recommendation', methods=['POST', 'GET'])
def get_recommendation():
    if request.method == 'POST':
        data = request.json or {}
    else:
        data = {
            'crop': request.args.get('crop', 'Rice'),
            'district': request.args.get('district', 'Pune'),
            'land_size': float(request.args.get('land_size', 2.0)),
            'mandi': request.args.get('mandi'),
            'state': request.args.get('state', 'Maharashtra'),
            'farm_crop_id': request.args.get('farm_crop_id'),
        }

    # ── Load context from farm_crop_id if provided ──
    farm_crop_id = data.get('farm_crop_id')
    if farm_crop_id:
        ctx = FarmerService.get_crop_context(farm_crop_id)
        if ctx:
            # Use DB context, allow request data to override
            for key in ['crop', 'district', 'state', 'land_size', 'mandi',
                        'storage_available', 'soil_type', 'irrigation_type']:
                if key not in data or data[key] is None:
                    if key == 'mandi':
                        data[key] = ctx.get('preferred_mandi')
                    else:
                        data[key] = ctx.get(key)
            data['farm_crop_id'] = farm_crop_id

    result = RecommendationService.get_recommendation(data)
    if result:
        return jsonify(result), 200
    return jsonify({"error": "Recommendation generation failed"}), 500
