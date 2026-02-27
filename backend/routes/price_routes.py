from flask import Blueprint, request, jsonify
from services.price_service import PriceService

price_bp = Blueprint('price_bp', __name__)

@price_bp.route('/price/forecast', methods=['GET'])
def get_price_forecast():
    crop     = request.args.get('crop')
    mandi    = request.args.get('mandi')
    state    = request.args.get('state', '')
    quantity = request.args.get('quantity', '10')

    if not crop:
        return jsonify({"error": "Crop parameter is required"}), 400
    if not mandi:
        mandi = "Pune"

    result = PriceService.forecast_price({
        'crop'    : crop,
        'mandi'   : mandi,
        'state'   : state,
        'quantity' : quantity,
    })
    if result:
        return jsonify(result), 200
    return jsonify({"error": "Forecast failed"}), 500

