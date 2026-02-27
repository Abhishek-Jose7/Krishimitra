from flask import Blueprint, request, jsonify
from services.mandi_service import MandiService

mandi_bp = Blueprint('mandi_bp', __name__)

@mandi_bp.route('/mandi/prices', methods=['GET'])
def get_mandi_prices():
    crop = request.args.get('crop', 'Rice')
    district = request.args.get('district')
    state = request.args.get('state')
    prices = MandiService.get_nearby_prices(crop, district=district, state=state)
    return jsonify(prices), 200

@mandi_bp.route('/mandi/forecast', methods=['GET'])
def get_mandi_forecast():
    """GET /mandi/forecast?crop=Groundnut&state=Karnataka&mandi=Hubli"""
    crop = request.args.get('crop', 'Rice')
    state = request.args.get('state', '')
    mandi = request.args.get('mandi', '')
    forecast = MandiService.get_mandi_forecast(crop, state, mandi_name=mandi or None)
    if forecast:
        return jsonify(forecast), 200
    return jsonify({"error": "No forecast available for this crop"}), 404

@mandi_bp.route('/mandi/risk', methods=['GET'])
def get_market_risk():
    risk = MandiService.get_market_risk()
    return jsonify(risk), 200
