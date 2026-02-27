from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


def _clamp(val: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, val))


def _risk_label_from_score(score: float) -> str:
    if score > 70:
        return "HIGH"
    if score >= 40:
        return "MODERATE"
    return "LOW"


def _severity_to_score(level: str | None) -> int:
    lvl = (level or "").strip().upper()
    if lvl == "HIGH":
        return 80
    if lvl == "MODERATE":
        return 60
    return 30


def _max_severity(*levels: str | None) -> str:
    order = {"LOW": 0, "MODERATE": 1, "HIGH": 2}
    best = "LOW"
    best_v = -1
    for l in levels:
        key = (l or "").strip().upper()
        if key not in order:
            continue
        if order[key] > best_v:
            best = key
            best_v = order[key]
    return best


def _safe_float(v: Any, default: float | None = None) -> float | None:
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default


@dataclass(frozen=True)
class ProtectionAction:
    type: str
    scheme_name: str
    urgency: str
    reason: str
    apply_link: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "scheme_name": self.scheme_name,
            "urgency": self.urgency,
            "reason": self.reason,
            "apply_link": self.apply_link,
        }


class FinancialAdvisorService:
    """
    Farm Financial Protection Center — independent risk & protection engine.

    This service is intentionally self-contained and does not modify any
    existing recommendation/weather logic; it only consumes their outputs.
    """

    PMFBY_LINK = "https://pmfby.gov.in"
    PM_KISAN_LINK = "https://pmkisan.gov.in"
    MSP_INFO_LINK = "https://dfpd.gov.in/Price-Support.htm"

    MSP_CROPS = {
        "RICE",
        "PADDY",
        "WHEAT",
        "MAIZE",
        "JOWAR",
        "BAJRA",
        "RAGI",
        "GRAM",
        "TUR",
        "MOONG",
        "URAD",
        "LENTIL",
        "GROUNDNUT",
        "SOYBEAN",
        "SUNFLOWER",
        "SESAMUM",
        "COTTON",
        "SUGARCANE",
        "ONION",
        "POTATO",
    }

    @classmethod
    def analyze(
        cls,
        *,
        farmer_profile: Dict[str, Any],
        crop: str,
        district: str,
        weather_risk: Dict[str, Any] | Any,
        price_forecast_data: Optional[Dict[str, Any]],
        yield_prediction_data: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        weather_risk_score, weather_level, weather_reason = cls._compute_weather_score(
            weather_risk
        )
        market_risk_score, market_trend, market_reason = cls._compute_market_score(
            price_forecast_data
        )
        yield_risk_score, yield_reason = cls._compute_yield_score(yield_prediction_data)

        financial_risk_score = float(
            (weather_risk_score + market_risk_score + yield_risk_score) / 3.0
        )
        risk_level = _risk_label_from_score(financial_risk_score)

        recommended_actions: List[ProtectionAction] = []
        protection_gap = cls._build_protection_gap(
            farmer_profile=farmer_profile,
            weather_level=weather_level,
            market_trend=market_trend,
            weather_reason=weather_reason,
            market_reason=market_reason,
            yield_reason=yield_reason,
        )

        recommended_actions.extend(
            cls._scheme_engine(
                farmer_profile=farmer_profile,
                crop=crop,
                district=district,
                weather_level=weather_level,
                market_trend=market_trend,
                price_forecast_data=price_forecast_data,
            )
        )

        return {
            "financial_health_score": int(round(_clamp(100.0 - financial_risk_score))),
            "risk_level": risk_level,
            "risk_breakdown": {
                "weather_risk_score": int(round(_clamp(weather_risk_score))),
                "market_risk_score": int(round(_clamp(market_risk_score))),
                "yield_risk_score": int(round(_clamp(yield_risk_score))),
            },
            "protection_gap": protection_gap,
            "recommended_protection_actions": [a.to_dict() for a in recommended_actions],
        }

    # ──────────────────────────────────────────
    # Scoring
    # ──────────────────────────────────────────

    @classmethod
    def _compute_weather_score(
        cls, weather_risk: Dict[str, Any] | Any
    ) -> Tuple[int, str, str]:
        if isinstance(weather_risk, dict):
            rain = weather_risk.get("rain_risk")
            heat = weather_risk.get("heat_risk")
            humidity = weather_risk.get("humidity_risk")
        else:
            rain = getattr(weather_risk, "rain_risk", None)
            heat = getattr(weather_risk, "heat_risk", None)
            humidity = getattr(weather_risk, "humidity_risk", None)

        overall = _max_severity(rain, heat, humidity)
        score = _severity_to_score(overall)

        reasons = []
        if (rain or "").upper() == "HIGH":
            reasons.append("high rainfall exposure")
        if (heat or "").upper() == "HIGH":
            reasons.append("heat stress risk")
        if (humidity or "").upper() == "HIGH":
            reasons.append("high humidity risk")
        reason = ", ".join(reasons) if reasons else "no major weather red flags detected"
        return score, overall, reason

    @classmethod
    def _compute_market_score(
        cls, price_forecast_data: Optional[Dict[str, Any]]
    ) -> Tuple[int, str, str]:
        if not price_forecast_data:
            # Simulated market score when forecast unavailable
            return 55, "UNKNOWN", "price forecast unavailable (simulated market risk)"

        volatility = _safe_float(price_forecast_data.get("volatility"))
        trend = (price_forecast_data.get("trend") or "").strip()

        # If volatility exists, map it to a 0–100 risk score.
        # Typical model volatility in this codebase is ~0.05–0.30.
        if volatility is not None:
            market_score = int(round(_clamp(volatility * 250.0)))  # 0.4 -> 100
            reason = f"forecast volatility {volatility:.2f}"
        else:
            # Fallback: infer from forecast variance (std/mean) if list present
            fc = price_forecast_data.get("forecast") or []
            prices = []
            for p in fc:
                if isinstance(p, dict) and "price" in p:
                    val = _safe_float(p.get("price"))
                    if val is not None:
                        prices.append(val)
            if len(prices) >= 5:
                mean = sum(prices) / len(prices)
                var = sum((x - mean) ** 2 for x in prices) / max(len(prices), 1)
                std = var**0.5
                rel = std / max(mean, 1.0)
                market_score = int(round(_clamp(rel * 250.0)))
                reason = "forecast variance indicates volatility"
            else:
                market_score = 55
                reason = "limited price forecast info (simulated market risk)"

        # Trend adjustment nudges score (non-destructive)
        if trend.lower() == "falling":
            market_score = int(round(_clamp(market_score + 10)))
        elif trend.lower() == "rising":
            market_score = int(round(_clamp(market_score - 5)))

        trend_norm = trend if trend else "UNKNOWN"
        return market_score, trend_norm, reason

    @classmethod
    def _compute_yield_score(
        cls, yield_prediction_data: Optional[Dict[str, Any]]
    ) -> Tuple[int, str]:
        if not yield_prediction_data:
            return 50, "yield prediction unavailable (simulated yield risk)"

        confidence = _safe_float(yield_prediction_data.get("confidence"))
        if confidence is None:
            # Mysuru simulation uses "confidence_adjusted"
            confidence = _safe_float(yield_prediction_data.get("confidence_adjusted"))

        if confidence is None:
            return 50, "yield confidence unavailable (simulated yield risk)"

        # Per spec: yield risk based on confidence (lower confidence = higher risk)
        score = int(round(_clamp(100.0 - confidence)))
        return score, f"yield confidence {confidence:.1f}%"

    # ──────────────────────────────────────────
    # Protection gap + scheme engine
    # ──────────────────────────────────────────

    @classmethod
    def _detect_landholding_acres(cls, farmer_profile: Dict[str, Any]) -> float | None:
        acres = _safe_float(farmer_profile.get("landholding_acres"))
        if acres is not None:
            return acres
        # Some app contexts store hectares
        ha = _safe_float(farmer_profile.get("landholding_hectares"))
        if ha is not None:
            return ha * 2.47105
        return None

    @classmethod
    def _detect_insurance_active(cls, farmer_profile: Dict[str, Any]) -> bool:
        for key in ("has_insurance", "insurance_active", "pmfby_active", "active_insurance"):
            v = farmer_profile.get(key)
            if isinstance(v, bool):
                return v
            if isinstance(v, str) and v.strip().lower() in ("yes", "true", "1"):
                return True
        return False

    @classmethod
    def _build_protection_gap(
        cls,
        *,
        farmer_profile: Dict[str, Any],
        weather_level: str,
        market_trend: str,
        weather_reason: str,
        market_reason: str,
        yield_reason: str,
    ) -> str:
        insurance_active = cls._detect_insurance_active(farmer_profile)
        parts: List[str] = []

        if weather_level == "HIGH" and not insurance_active:
            parts.append("High weather exposure and no active insurance detected.")
        elif weather_level == "HIGH":
            parts.append("High weather exposure detected; insurance coverage looks present.")

        if market_trend.upper() == "FALLING":
            parts.append("Prices are trending down; income protection and MSP options become important.")

        if not parts:
            parts.append("No major protection gaps detected, but keep coverage active and review market risks weekly.")

        # Add a short evidence tail (kept human-readable)
        evidence_bits = [weather_reason, market_reason, yield_reason]
        evidence = "; ".join([b for b in evidence_bits if b])
        if evidence:
            return f"{' '.join(parts)} Evidence: {evidence}."
        return " ".join(parts)

    @classmethod
    def _scheme_engine(
        cls,
        *,
        farmer_profile: Dict[str, Any],
        crop: str,
        district: str,
        weather_level: str,
        market_trend: str,
        price_forecast_data: Optional[Dict[str, Any]],
    ) -> List[ProtectionAction]:
        actions: List[ProtectionAction] = []

        # 1) Weather risk HIGH → PMFBY insurance
        if weather_level == "HIGH":
            actions.append(
                ProtectionAction(
                    type="Insurance",
                    scheme_name="PMFBY",
                    urgency="HIGH",
                    reason="High weather risk detected; insurance reduces shock losses.",
                    apply_link=cls.PMFBY_LINK,
                )
            )

        # 2) Landholding <= 2 acres → PM-KISAN income support
        acres = cls._detect_landholding_acres(farmer_profile)
        if acres is not None and acres <= 2.0:
            actions.append(
                ProtectionAction(
                    type="Income Support",
                    scheme_name="PM-KISAN",
                    urgency="MEDIUM",
                    reason=f"Small landholding detected (~{acres:.1f} acres).",
                    apply_link=cls.PM_KISAN_LINK,
                )
            )

        crop_norm = (crop or "").strip().upper()
        crop_is_msp = crop_norm in cls.MSP_CROPS

        # 3) Crop under MSP → suggest procurement
        if crop_is_msp:
            actions.append(
                ProtectionAction(
                    type="MSP Procurement",
                    scheme_name="MSP",
                    urgency="MEDIUM" if market_trend.upper() != "FALLING" else "HIGH",
                    reason=f"{crop} is typically covered under MSP procurement channels.",
                    apply_link=cls.MSP_INFO_LINK,
                )
            )

        # 4) Price forecast decreasing → suggest MSP or delayed selling
        if market_trend.upper() == "FALLING" or cls._forecast_is_decreasing(price_forecast_data):
            actions.append(
                ProtectionAction(
                    type="Price Strategy",
                    scheme_name="Delayed Selling",
                    urgency="HIGH" if crop_is_msp else "MEDIUM",
                    reason="Forecast indicates weakening prices; consider MSP procurement or delaying sale if storage allows.",
                    apply_link=cls.MSP_INFO_LINK if crop_is_msp else cls.MSP_INFO_LINK,
                )
            )

        # De-duplicate by (type, scheme_name)
        seen = set()
        deduped: List[ProtectionAction] = []
        for a in actions:
            key = (a.type, a.scheme_name)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(a)
        return deduped

    @staticmethod
    def _forecast_is_decreasing(price_forecast_data: Optional[Dict[str, Any]]) -> bool:
        if not price_forecast_data:
            return False
        fc = price_forecast_data.get("forecast") or []
        prices: List[float] = []
        for row in fc:
            if isinstance(row, dict) and "price" in row:
                v = _safe_float(row.get("price"))
                if v is not None:
                    prices.append(v)
        if len(prices) < 7:
            return False
        return prices[-1] < prices[0] * 0.98

