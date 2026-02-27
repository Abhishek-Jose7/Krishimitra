from flask import Blueprint, request, jsonify
from services.weather_service import WeatherService

weather_bp = Blueprint('weather_bp', __name__)

@weather_bp.route('/weather', methods=['GET'])
def get_weather():
    district = request.args.get('district', 'Pune')
    result = WeatherService.get_weather(district)
    if result:
        return jsonify(result), 200
    return jsonify({"error": "Weather data unavailable"}), 500
