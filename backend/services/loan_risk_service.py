"""
Loan & Credit Risk Assistant — standalone Financial Stress Simulator.

Consumes existing YieldService, PriceService, WeatherService without modifying them.
"""

from __future__ import annotations

from typing import Any, Dict, List

from services.price_service import PriceService
from services.weather_service import WeatherService
from services.yield_service import YieldService


def _clamp(val: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, val))


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _weather_severity_to_score(risk: Dict[str, Any]) -> float:
    """Map weather risk dict to 0–100 score. Does not modify weather logic."""
    order = {"LOW": 30, "MODERATE": 60, "HIGH": 80}
    best = 30
    for key in ("rain_risk", "heat_risk", "humidity_risk"):
        level = (risk.get(key) or "").strip().upper()
        best = max(best, order.get(level, 30))
    return float(best)


def _weather_is_high(risk: Dict[str, Any]) -> bool:
    return _weather_severity_to_score(risk) >= 70


def _volatility_to_score(volatility: float | None) -> float:
    """Map price volatility (e.g. 0.05–0.3) to 0–100. Deterministic."""
    if volatility is None:
        return 50.0
    return _clamp(volatility * 250.0)


def _is_volatility_high(volatility: float | None) -> bool:
    return (volatility or 0) >= 0.15


class LoanRiskService:
    """
    Loan & Credit Risk Assistant. Uses only existing services; no changes to them.
    """

    SEASON_LENGTH_MONTHS = 6

    @classmethod
    def analyze_loan(
        cls,
        farmer_profile: Dict[str, Any],
        crop: str,
        district: str,
        loan_amount: float,
        interest_rate_annual: float,
        tenure_months: int,
    ) -> Dict[str, Any]:
        """
        Run loan risk analysis using yield, price, and weather from existing services.
        """
        land_size = _safe_float(
            farmer_profile.get("landholding_hectares")
            or farmer_profile.get("land_size"),
            2.0,
        )
        mandi = farmer_profile.get("preferred_mandi") or "Pune"
        state = farmer_profile.get("state") or ""

        # ─── Fetch from existing services (read-only) ───
        yield_data = None
        try:
            yield_data = YieldService.predict_yield(
                {"district": district, "crop": crop, "land_size": land_size}
            )
        except Exception:
            pass

        price_data = None
        try:
            price_data = PriceService.forecast_price(
                {"crop": crop, "mandi": mandi, "state": state}
            )
        except Exception:
            pass

        weather_risk = {}
        try:
            weather_risk = WeatherService.calculate_weather_risk(district)
        except Exception:
            pass

        # ─── Predicted yield (quintals or tonnes; treat as same unit as price) ───
        predicted_yield = _safe_float(
            yield_data.get("total_expected_production")
            if yield_data else None,
            10.0,
        )
        predicted_avg_price = _safe_float(
            price_data.get("current_price") if price_data else None,
            2000.0,
        )

        # ─── Expected income (season) ───
        expected_income = predicted_yield * predicted_avg_price
        if expected_income <= 0:
            expected_income = 1.0

        season_months = cls.SEASON_LENGTH_MONTHS
        monthly_income_normal = expected_income / season_months

        # ─── EMI: P × r × (1+r)^n / ((1+r)^n - 1), r = annual_rate/12/100 ───
        r = (interest_rate_annual / 12.0) / 100.0
        n = max(1, int(tenure_months))
        P = max(0.0, float(loan_amount))
        if r <= 0:
            monthly_emi = P / n if n else 0.0
        else:
            factor = (1.0 + r) ** n
            monthly_emi = P * r * factor / (factor - 1.0) if (factor - 1.0) != 0 else P / n

        # ─── Repayment ratio: EMI / (expected_income / season_months) ───
        repayment_ratio = (
            monthly_emi / monthly_income_normal if monthly_income_normal > 0 else 0.0
        )

        # ─── Weather HIGH → reduce expected_income by 25% for worst case ───
        worst_case_income = expected_income
        if _weather_is_high(weather_risk):
            worst_case_income = expected_income * 0.75
        worst_case_monthly = worst_case_income / season_months
        worst_case_ratio = (
            monthly_emi / worst_case_monthly if worst_case_monthly > 0 else 0.0
        )

        # ─── Market volatility HIGH → 10% stress buffer on ratio ───
        volatility = price_data.get("volatility") if price_data else None
        if _is_volatility_high(volatility):
            repayment_ratio *= 1.10
            worst_case_ratio *= 1.10

        # ─── Scores (0–100) ───
        weather_risk_score = _weather_severity_to_score(weather_risk)
        market_volatility_score = _volatility_to_score(volatility)

        # Loan risk: weighted formula, then clamp
        loan_risk_numeric = (
            (repayment_ratio * 100.0 * 0.6)
            + (weather_risk_score * 0.2)
            + (market_volatility_score * 0.2)
        )
        loan_risk_numeric = _clamp(loan_risk_numeric)

        if loan_risk_numeric > 70:
            loan_risk_level = "HIGH"
        elif loan_risk_numeric >= 40:
            loan_risk_level = "MODERATE"
        else:
            loan_risk_level = "LOW"

        # ─── Recommendations ───
        recommendations: List[str] = []

        if loan_risk_level == "HIGH":
            recommendations.append(
                "Consider reducing loan amount by 20–30% to lower repayment stress."
            )
        if _weather_is_high(weather_risk):
            recommendations.append(
                "High weather risk. Consider PMFBY crop insurance to protect income."
            )
        if repayment_ratio > 0.6:
            recommendations.append(
                "Repayment ratio is high. Consider shorter tenure or smaller loan."
            )
        if loan_risk_level == "MODERATE":
            recommendations.append(
                "Monitor crop price trends and weather; plan for possible income dip."
            )
        if not recommendations:
            recommendations.append("Loan appears manageable under current assumptions.")

        return {
            "loan_risk_score": int(round(loan_risk_numeric)),
            "loan_risk_level": loan_risk_level,
            "repayment_ratio": round(repayment_ratio, 4),
            "worst_case_ratio": round(worst_case_ratio, 4),
            "expected_income": round(expected_income, 2),
            "monthly_emi": round(monthly_emi, 2),
            "recommendations": recommendations,
        }
