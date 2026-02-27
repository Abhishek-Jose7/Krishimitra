"""
Dashboard Intelligence Route

Returns a personalized dashboard payload:
  - Region-aware card ordering
  - Crop-type-specific alerts
  - MSP context
  - Sync recommendations

Now supports farm_crop_id for per-crop context loading.
"""

from flask import Blueprint, request, jsonify
from services.intelligence_engine import IntelligenceEngine
from services.weather_service import WeatherService
from services.mandi_service import MandiService
from services.recommendation_service import RecommendationService
from services.farmer_service import FarmerService

dashboard_bp = Blueprint('dashboard_bp', __name__)


@dashboard_bp.route('/dashboard/intelligent', methods=['POST'])
def get_intelligent_dashboard():
    """
    POST /dashboard/intelligent
    Body: { state, crop, district, land_size, storage_available, mandi }
      OR: { farm_crop_id }  ← crop-context-driven (preferred)

    When farm_crop_id is provided, all params are loaded from the DB.
    Falls back to flat params for backward compatibility.
    """
    data = request.json or {}

    # ── Load context from farm_crop_id if provided ──
    farm_crop_id = data.get('farm_crop_id')
    if farm_crop_id:
        ctx = FarmerService.get_crop_context(farm_crop_id)
        if ctx:
            state = ctx['state'] or data.get('state', 'Maharashtra')
            crop = ctx['crop']
            district = ctx['district'] or data.get('district', 'Pune')
            land_size = ctx['area_hectares'] or float(data.get('land_size', 2.0))
            storage = ctx['has_storage']
            mandi = ctx['preferred_mandi'] or f'{district} Mandi'
            soil_type = ctx.get('soil_type')
            irrigation_type = ctx.get('irrigation_type')
            sowing_date = ctx.get('sowing_date')
        else:
            # farm_crop_id not found — fall through to flat params
            farm_crop_id = None

    # ── Flat param fallback ──
    if not farm_crop_id:
        state = data.get('state', 'Maharashtra')
        crop = data.get('crop', 'Rice')
        district = data.get('district', 'Pune')
        land_size = float(data.get('land_size', 2.0))
        storage = data.get('storage_available', False)
        mandi = data.get('mandi', f'{district} Mandi')
        soil_type = data.get('soil_type')
        irrigation_type = data.get('irrigation_type')
        sowing_date = data.get('sowing_date')

    # Track which sections failed so the frontend can show "unavailable" UI
    unavailable = []

    # 1. Get intelligence strategy (core — has fallback default)
    intelligence = None
    try:
        intelligence = IntelligenceEngine.get_intelligence(
            state=state,
            crop=crop,
            district=district,
            land_size=land_size,
            storage_available=storage,
        )
    except Exception:
        unavailable.append('strategy')
        intelligence = {
            'region_focus': 'generic', 'region_label': state or 'India',
            'crop_type': 'grain', 'advice_style': 'balanced',
            'forecast_horizon': '7-day', 'card_priority': ['weather', 'price', 'recommendation'],
            'weights': {}, 'sync_interval_hours': 6,
            'region_alerts': [], 'crop_alerts': [],
            'msp': None, 'govt_schemes': {},
            'shelf_life_days': 180, 'storage_critical': False,
        }

    # 2. Fetch weather
    weather = None
    try:
        weather = WeatherService.get_weather(district)
    except Exception:
        unavailable.append('weather')
        weather = {'temp': 30, 'humidity': 60, 'rainfall': 0, 'condition': 'Unknown'}

    # 3. Fetch mandi prices
    mandi_prices = None
    try:
        mandi_prices = MandiService.get_nearby_prices(crop, district=district, state=state)
    except Exception:
        unavailable.append('mandi_prices')

    # 4. Market risk
    market_risk = None
    try:
        market_risk = MandiService.get_market_risk()
    except Exception:
        unavailable.append('market_risk')

    # 5. Recommendation (sell/hold)
    recommendation = None
    try:
        recommendation = RecommendationService.get_recommendation({
            'crop': crop,
            'district': district,
            'land_size': land_size,
            'mandi': mandi,
            'state': state,
            'storage_available': storage,
            'soil_type': soil_type,
            'irrigation_type': irrigation_type,
            'farm_crop_id': farm_crop_id,
        })
    except Exception:
        unavailable.append('recommendation')

    # 6. Feature data (for transparency)
    features = None
    try:
        from services.feature_engine import FeatureEngine
        features = FeatureEngine.compute_all_features(crop, district, mandi)
    except Exception:
        unavailable.append('features')

    # 7. Crop calendar context
    season_context = None
    try:
        from services.crop_calendar import CropCalendar
        season_context = CropCalendar.get_current_phase(crop, state)
    except Exception:
        unavailable.append('season_context')

    # 8. Karnataka-specific forecast (only if applicable)
    karnataka_forecast = None
    try:
        from services.karnataka_predictor import KarnatakaForecaster
        if KarnatakaForecaster.is_supported(state, crop):
            karnataka_forecast = KarnatakaForecaster.get_forecast(
                crop=crop,
                market=mandi,
                quantity=land_size * 10,
            )
    except Exception:
        unavailable.append('karnataka_forecast')

    # 9. Assemble response — every section present even if None
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

        # Alerts
        'alerts': intelligence['region_alerts'] + intelligence['crop_alerts'],

        # MSP context
        'msp': intelligence['msp'],

        # Govt schemes
        'govt_schemes': intelligence.get('govt_schemes', {}),

        # Storage context
        'storage': {
            'shelf_life_days': intelligence['shelf_life_days'],
            'storage_critical': intelligence['storage_critical'],
            'has_storage': storage,
        },

        # Crop context metadata (so frontend knows what context was used)
        'crop_context': {
            'farm_crop_id': farm_crop_id,
            'crop': crop,
            'land_size': land_size,
            'mandi': mandi,
            'state': state,
            'district': district,
            'sowing_date': sowing_date,
        },

        # Data payloads — each is None if the service failed
        'weather': weather,
        'mandi_prices': mandi_prices,
        'market_risk': market_risk,
        'recommendation': recommendation,

        # Production fields
        'features': features,
        'season_context': season_context,
        'trust': recommendation.get('trust') if recommendation else None,

        # Karnataka XGBoost forecasts
        'karnataka_forecast': karnataka_forecast,

        # Sections that failed — frontend can show "unavailable" UI
        'unavailable': unavailable,
    }

    return jsonify(response), 200


@dashboard_bp.route('/dashboard/strategy', methods=['GET'])
def get_strategy_only():
    """
    GET /dashboard/strategy?state=Kerala&crop=Rice

    Lightweight — returns ONLY the strategy without data payloads.
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
