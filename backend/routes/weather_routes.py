from flask import Blueprint, request, jsonify
from services.weather_service import WeatherService

weather_bp = Blueprint("weather_bp", __name__)

@weather_bp.route("/weather-risk", methods=["GET"])
def weather_risk():
    district = request.args.get("district")

    if not district:
        return jsonify({"error": "district parameter required"}), 400

    risk = WeatherService.calculate_weather_risk(district)

    return jsonify({
        "district": district,
        "risk": risk
    })
