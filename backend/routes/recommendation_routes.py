from flask import Blueprint, request, jsonify
from services.recommendation_service import RecommendationService

recommendation_bp = Blueprint('recommendation_bp', __name__)

@recommendation_bp.route('/recommendation', methods=['POST', 'GET'])
def get_recommendation():
    # User flow says GET /recommendation (which implies fetching for current user/context)
    # But usually recommendation needs input data (district, etc.)
    # If GET, we might need query params or use defaults from user profile (if logged in)
    # For now, let's support POST with data or GET with query params
    
    data = {}
    if request.method == 'POST':
        data = request.json
    else:
        # GET
        data = request.args.to_dict()
    
    # Needs at least some context
    # RecommendationService needs 'land_size', 'crop', etc. to run yield prediction internally?
    # Or strict recommendation based on existing prediction?
    # Service implementation:
    # yield_result = YieldService.predict_yield(data) -> needs data
    
    if not data:
         return jsonify({"error": "No input data provided"}), 400

    result = RecommendationService.get_recommendation(data)
    if result:
        return jsonify(result), 200
    return jsonify({"error": "Recommendation failed"}), 500
