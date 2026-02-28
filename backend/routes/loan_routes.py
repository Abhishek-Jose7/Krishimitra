"""
Loan & Credit Risk Assistant — standalone route. Does not modify existing routes.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from services.farmer_service import FarmerService
from services.loan_risk_service import LoanRiskService


loan_bp = Blueprint("loan_bp", __name__)


def _safe_float(val, default: float = 0.0) -> float:
    try:
        if val is None:
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


@loan_bp.route("/loan-risk", methods=["GET"])
@jwt_required(optional=True)
def loan_risk():
    crop = request.args.get("crop", "Rice")
    district = request.args.get("district")
    loan_amount = _safe_float(request.args.get("loan_amount"), 100000.0)
    interest_rate = _safe_float(request.args.get("interest_rate"), 12.0)
    tenure_months = int(_safe_float(request.args.get("tenure_months"), 12))

    if not district:
        return jsonify({"error": "district parameter required"}), 400

    farmer_profile = {}
    land_hectares = None
    try:
        user_id = get_jwt_identity()
        if user_id:
            fp = FarmerService.get_farmer(user_id) or {}
            farmer_profile.update(fp)
            farms = FarmerService.get_user_farms(user_id)
            if farms:
                total = 0.0
                for f in farms:
                    ha = f.get("total_land_hectares")
                    if ha is not None:
                        total += float(ha)
                if total > 0:
                    land_hectares = total
            default_crop = FarmerService.get_default_crop(user_id)
            if default_crop and default_crop.preferred_mandi:
                farmer_profile.setdefault("preferred_mandi", default_crop.preferred_mandi)
    except Exception:
        pass

    if land_hectares is None:
        land_hectares = 2.0
    farmer_profile.setdefault("district", district)
    farmer_profile.setdefault("state", "")
    farmer_profile.setdefault("preferred_mandi", "Pune")
    farmer_profile.setdefault("landholding_hectares", land_hectares)

    result = LoanRiskService.analyze_loan(
        farmer_profile=farmer_profile,
        crop=crop,
        district=district,
        loan_amount=loan_amount,
        interest_rate_annual=interest_rate,
        tenure_months=max(1, tenure_months),
    )
    return jsonify(result), 200
