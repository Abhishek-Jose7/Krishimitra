from flask import Blueprint, request, jsonify
from services.mandi_service import MandiService

mandi_bp = Blueprint('mandi_bp', __name__)

@mandi_bp.route('/mandi/prices', methods=['GET'])
def get_mandi_prices():
    crop = request.args.get('crop', 'Rice')
    district = request.args.get('district')
    prices = MandiService.get_nearby_prices(crop, district)
    return jsonify(prices), 200

@mandi_bp.route('/mandi/risk', methods=['GET'])
def get_market_risk():
    risk = MandiService.get_market_risk()
    return jsonify(risk), 200
