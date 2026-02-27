"""
Dashboard Intelligence Route

Returns a personalized dashboard payload:
  - Region-aware card ordering
  - Crop-type-specific alerts
  - MSP context
  - Sync recommendations

Called by the Flutter app on every dashboard load.
"""

from flask import Blueprint, request, jsonify
from services.intelligence_engine import IntelligenceEngine
from services.weather_service import WeatherService
from services.mandi_service import MandiService
from services.recommendation_service import RecommendationService

dashboard_bp = Blueprint('dashboard_bp', __name__)


@dashboard_bp.route('/dashboard/intelligent', methods=['POST'])
def get_intelligent_dashboard():
    """
    POST /dashboard/intelligent
    Body: { state, crop, district, land_size, storage_available, mandi }

    Returns everything the dashboard needs in ONE call — no 5 separate requests.
    """
    data = request.json or {}

    state = data.get('state', 'Maharashtra')
    crop = data.get('crop', 'Rice')
    district = data.get('district', 'Pune')
    land_size = float(data.get('land_size', 2.0))
    storage = data.get('storage_available', False)
    mandi = data.get('mandi', f'{district} Mandi')

    # 1. Get intelligence strategy
    intelligence = IntelligenceEngine.get_intelligence(
        state=state,
        crop=crop,
        district=district,
        land_size=land_size,
        storage_available=storage,
    )

    # 2. Fetch weather (weight decides prominence)
    weather = None
    try:
        weather = WeatherService.get_weather(district)
    except Exception:
        weather = {'temp': 30, 'humidity': 60, 'rainfall': 0, 'condition': 'Unknown'}

    # 3. Fetch mandi prices
    mandi_prices = None
    try:
        mandi_prices = MandiService.get_nearby_prices(crop, district=district)
    except Exception:
        pass

    # 4. Market risk
    market_risk = None
    try:
        market_risk = MandiService.get_market_risk()
    except Exception:
        pass

    # 5. Recommendation (sell/hold) — now includes trust, features, season context
    recommendation = None
    try:
        recommendation = RecommendationService.get_recommendation({
            'crop': crop,
            'district': district,
            'land_size': land_size,
            'mandi': mandi,
            'state': state,
        })
    except Exception:
        pass

    # 6. Feature data (for transparency)
    features = None
    try:
        from services.feature_engine import FeatureEngine
        features = FeatureEngine.compute_all_features(crop, district, mandi)
    except Exception:
        pass

    # 7. Crop calendar context
    season_context = None
    try:
        from services.crop_calendar import CropCalendar
        season_context = CropCalendar.get_current_phase(crop, state)
    except Exception:
        pass

    # 8. Karnataka-specific forecast (if applicable)
    karnataka_forecast = None
    try:
        from services.karnataka_predictor import KarnatakaForecaster
        if KarnatakaForecaster.is_supported(state, crop):
            karnataka_forecast = KarnatakaForecaster.get_forecast(
                crop=crop,
                market=mandi,
                quantity=land_size * 10,  # rough quintals estimate
            )
    except Exception:
        pass

    # 9. Assemble response — card ordering from intelligence
    response = {
        # Strategy metadata
        'strategy': {
            'region_focus': intelligence['region_focus'],
            'region_label': intelligence['region_label'],
            'crop_type': intelligence['crop_type'],
            'advice_style': intelligence['advice_style'],
            'forecast_horizon': intelligence['forecast_horizon'],
            'card_priority': intelligence['card_priority'],
            'weights': intelligence['weights'],
            'sync_interval_hours': intelligence['sync_interval_hours'],
        },

        # Alerts (region + crop)
        'alerts': intelligence['region_alerts'] + intelligence['crop_alerts'],

        # MSP context
        'msp': intelligence['msp'],

        # Govt schemes (region-specific)
        'govt_schemes': intelligence.get('govt_schemes', {}),

        # Storage context
        'storage': {
            'shelf_life_days': intelligence['shelf_life_days'],
            'storage_critical': intelligence['storage_critical'],
            'has_storage': storage,
        },

        # Data payloads
        'weather': weather,
        'mandi_prices': mandi_prices,
        'market_risk': market_risk,
        'recommendation': recommendation,

        # NEW: Production-readiness fields
        'features': features,
        'season_context': season_context,
        'trust': recommendation.get('trust') if recommendation else None,

        # Karnataka XGBoost forecasts (if applicable)
        'karnataka_forecast': karnataka_forecast,
    }

    return jsonify(response), 200


@dashboard_bp.route('/dashboard/strategy', methods=['GET'])
def get_strategy_only():
    """
    GET /dashboard/strategy?state=Kerala&crop=Rice

    Lightweight endpoint — returns ONLY the strategy (card order, alerts, weights)
    without fetching weather/mandi/recommendation data.
    Used by the app to configure UI layout before data loads.
    """
    state = request.args.get('state', 'Maharashtra')
    crop = request.args.get('crop', 'Rice')
    district = request.args.get('district')
    storage = request.args.get('storage_available', 'false').lower() == 'true'

    intelligence = IntelligenceEngine.get_intelligence(
        state=state,
        crop=crop,
        district=district,
        storage_available=storage,
    )

    return jsonify(intelligence), 200
