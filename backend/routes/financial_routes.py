from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from services.farmer_service import FarmerService
from services.financial_advisor_service import FinancialAdvisorService
from services.price_service import PriceService
from services.weather_service import WeatherService
from services.yield_service import YieldService


financial_bp = Blueprint("financial_bp", __name__)


def _sum_land_hectares(farms_payload) -> float | None:
    try:
        if not farms_payload:
            return None
        total = 0.0
        found = False
        for f in farms_payload:
            ha = f.get("total_land_hectares")
            if ha is None:
                continue
            total += float(ha)
            found = True
        return total if found else None
    except Exception:
        return None


@financial_bp.route("/financial-protection", methods=["GET"])
@jwt_required(optional=True)
def financial_protection():
    crop = request.args.get("crop", "Rice")
    district = request.args.get("district")
    if not district:
        return jsonify({"error": "district parameter required"}), 400

    # 1) Fetch farmer profile (optional)
    current_user_id = None
    try:
        current_user_id = get_jwt_identity()
    except Exception:
        current_user_id = None

    farmer_profile = {}
    land_hectares = None
    mandi = None

    if current_user_id:
        fp = FarmerService.get_farmer(current_user_id) or {}
        farmer_profile.update(fp)
        farms = FarmerService.get_user_farms(current_user_id)
        land_hectares = _sum_land_hectares(farms)

        default_crop = FarmerService.get_default_crop(current_user_id)
        if default_crop:
            mandi = default_crop.preferred_mandi
            # prefer crop from query param, but if empty use default
            if not crop:
                crop = default_crop.crop_name
            if not district:
                district = farmer_profile.get("district") or district

    # Fallback landholding if unknown (keeps endpoint useful without auth)
    if land_hectares is None:
        land_hectares = 2.0

    farmer_profile.setdefault("district", district)
    farmer_profile.setdefault("landholding_hectares", land_hectares)
    farmer_profile.setdefault("landholding_acres", float(land_hectares) * 2.47105)

    if not mandi:
        mandi = request.args.get("mandi") or "Pune"

    # 2) Fetch weather risk (existing logic)
    weather_risk = WeatherService.calculate_weather_risk(district)

    # 3) Fetch yield prediction (existing logic)
    yield_prediction_data = None
    try:
        yield_prediction_data = YieldService.predict_yield(
            {
                "district": district,
                "crop": crop,
                "land_size": land_hectares,
            }
        )
    except Exception:
        yield_prediction_data = None

    # 4) Fetch price forecast (existing logic)
    price_forecast_data = None
    try:
        price_forecast_data = PriceService.forecast_price(
            {"crop": crop, "mandi": mandi, "state": farmer_profile.get("state", "")}
        )
    except Exception:
        price_forecast_data = None

    # 5) Call FinancialAdvisorService
    result = FinancialAdvisorService.analyze(
        farmer_profile=farmer_profile,
        crop=crop,
        district=district,
        weather_risk=weather_risk,
        price_forecast_data=price_forecast_data,
        yield_prediction_data=yield_prediction_data,
    )

    # 6) Return structured JSON
    return jsonify(result), 200

