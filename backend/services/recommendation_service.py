from services.yield_service import YieldService
from services.price_service import PriceService
from services.mandi_service import MandiService
from services.weather_service import WeatherService
import datetime
import math


class RecommendationService:
    # Storage advice per crop (original)
    STORAGE_ADVICE = {
        "Rice": {
            "max_days": 60,
            "method": "Store in dry, well-ventilated bags. Keep moisture below 14%.",
            "risk": "Quality drops after 2 months if moisture is high.",
        },
        "Wheat": {
            "max_days": 90,
            "method": "Use airtight containers or PUSA bins. Keep dry.",
            "risk": "Weevil infestation possible after 3 months without treatment.",
        },
        "Maize": {
            "max_days": 45,
            "method": "Dry cobs fully before storage. Use metallic bins.",
            "risk": "Fungal growth if moisture > 12%.",
        },
        "Soybean": {
            "max_days": 30,
            "method": "Store in cool, dry place. Avoid stacking too high.",
            "risk": "Oil content changes affect quality quickly.",
        },
        "Cotton": {
            "max_days": 180,
            "method": "Store in covered, dry warehouse. Keep bales off ground.",
            "risk": "Moisture causes discoloration and strength loss.",
        },
        "Onion": {
            "max_days": 14,
            "method": "Store in ventilated structures. Avoid stacking.",
            "risk": "Rotting is rapid. Sort daily and remove damaged onions.",
        },
        "Sugarcane": {
            "max_days": 3,
            "method": "Transport to mill immediately. Cannot be stored long.",
            "risk": "Sugar content drops 1-2% per day after cutting.",
        },
        "Groundnut": {
            "max_days": 60,
            "method": "Dry to 8% moisture. Store in gunny bags in cool place.",
            "risk": "Aflatoxin contamination if moisture not controlled.",
        },
    }

    # ══════════════════════════════════════════════
    # NEW: Storage Cost Modeling
    # ══════════════════════════════════════════════
    STORAGE_COSTS = {
        "Rice":       {"cost_per_day_per_quintal": 2.0,  "degradation_rate_per_day": 0.05, "spoilage_base": 0.001},
        "Wheat":      {"cost_per_day_per_quintal": 1.5,  "degradation_rate_per_day": 0.03, "spoilage_base": 0.0005},
        "Maize":      {"cost_per_day_per_quintal": 2.0,  "degradation_rate_per_day": 0.08, "spoilage_base": 0.002},
        "Soybean":    {"cost_per_day_per_quintal": 2.5,  "degradation_rate_per_day": 0.10, "spoilage_base": 0.005},
        "Cotton":     {"cost_per_day_per_quintal": 1.0,  "degradation_rate_per_day": 0.02, "spoilage_base": 0.0003},
        "Onion":      {"cost_per_day_per_quintal": 5.0,  "degradation_rate_per_day": 0.50, "spoilage_base": 0.03},
        "Sugarcane":  {"cost_per_day_per_quintal": 10.0, "degradation_rate_per_day": 2.00, "spoilage_base": 0.15},
        "Groundnut":  {"cost_per_day_per_quintal": 2.0,  "degradation_rate_per_day": 0.06, "spoilage_base": 0.001},
    }

    @staticmethod
    def get_recommendation(data):
        """
        Returns farmer-friendly sell/hold advice with:
        - Revenue comparison (sell now vs wait) in TOTAL RUPEES
        - Risk level (Low/Medium/High)
        - Uncertainty quantification (optimistic/pessimistic/risk-adjusted)
        - Storage cost modeling (cost per day, degradation, spoilage)
        - Simple explanation
        - Storage advice if HOLD
        """
        crop = data.get('crop', 'Rice')
        district = data.get('district', 'Pune')
        land_size = float(data.get('land_size', 2))
        mandi = data.get('mandi', 'Pune Mandi')

        # 1. Get yield prediction
        yield_data = {
            'crop': crop,
            'district': district,
            'land_size': land_size,
            'soil_type': data.get('soil_type', 'Black'),
        }
        yield_result = YieldService.predict_yield(yield_data)
        if not yield_result:
            return None
        total_production = yield_result['total_expected_production']  # in tons
        total_quintals = total_production * 10  # 1 ton = 10 quintals

        # 2. Get current price forecast
        price_result = PriceService.forecast_price({'crop': crop, 'mandi': mandi})
        if not price_result:
            return None

        current_price = price_result['current_price']  # per quintal
        peak_price = price_result['peak_price']
        peak_date_str = price_result['peak_date']
        volatility = price_result.get('volatility', 0.1)
        forecast = price_result.get('forecast', [])

        # NEW: Weather-aware intelligence
        weather_risk = WeatherService.calculate_weather_risk(district)

        # 3. Calculate revenues in TOTAL RUPEES
        sell_now_revenue = total_quintals * current_price
        sell_peak_revenue = total_quintals * peak_price
        extra_profit = sell_peak_revenue - sell_now_revenue

        # 4. Input cost estimation
        seed_cost = float(data.get('seed_cost', 0))
        fertilizer_cost = float(data.get('fertilizer_cost', 0))
        labour_cost = float(data.get('labour_cost', 0))
        irrigation_cost = float(data.get('irrigation_cost', 0))
        total_input_cost = seed_cost + fertilizer_cost + labour_cost + irrigation_cost

        profit_now = sell_now_revenue - total_input_cost
        profit_peak = sell_peak_revenue - total_input_cost

        # 5. Calculate wait days
        try:
            peak_date = datetime.datetime.fromisoformat(peak_date_str).date()
            wait_days = (peak_date - datetime.date.today()).days
        except Exception:
            wait_days = 0

        # 6. Determine risk level
        if volatility < 0.1:
            risk_level = "LOW"
            risk_emoji = "🟢"
            risk_message = "Market is stable. Forecast is reliable."
        elif volatility < 0.2:
            risk_level = "MEDIUM"
            risk_emoji = "🟡"
            risk_message = "Some price fluctuation expected. Plan accordingly."
        else:
            risk_level = "HIGH"
            risk_emoji = "🔴"
            risk_message = "Market is volatile. Selling now may be safer."

        # ══════════════════════════════════════════════
        # NEW: Uncertainty Quantification
        # ══════════════════════════════════════════════
        confidence_margin = volatility  # use volatility as proxy for uncertainty
        trough_price = min(p['price'] for p in forecast) if forecast else current_price * 0.9

        optimistic_revenue = total_quintals * peak_price * (1 + confidence_margin * 0.5)
        pessimistic_revenue = total_quintals * trough_price * (1 - confidence_margin * 0.5)
        expected_revenue = sell_peak_revenue
        risk_adjusted_revenue = (0.50 * expected_revenue + 0.30 * pessimistic_revenue + 0.20 * optimistic_revenue)

        confidence_band = {
            'lower': round(pessimistic_revenue, 0),
            'upper': round(optimistic_revenue, 0),
            'expected': round(expected_revenue, 0),
            'risk_adjusted': round(risk_adjusted_revenue, 0),
            'confidence_pct': max(20, min(90, int(80 - volatility * 200))),
        }

        # ══════════════════════════════════════════════
        # NEW: Storage Cost Modeling
        # ══════════════════════════════════════════════
        storage_cost_data = RecommendationService.STORAGE_COSTS.get(crop, {
            "cost_per_day_per_quintal": 2.0, "degradation_rate_per_day": 0.05, "spoilage_base": 0.001,
        })

        storage_cost_per_day = storage_cost_data['cost_per_day_per_quintal'] * total_quintals
        total_storage_cost = storage_cost_per_day * max(wait_days, 1)

        # Degradation: % value lost per day
        degradation_pct = storage_cost_data['degradation_rate_per_day'] * max(wait_days, 1)
        degradation_value = sell_peak_revenue * (degradation_pct / 100)

        # Spoilage: exponential probability increase
        spoilage_prob = 1 - math.exp(-storage_cost_data['spoilage_base'] * max(wait_days, 1))
        spoilage_risk_value = sell_peak_revenue * spoilage_prob

        total_hold_cost = total_storage_cost + degradation_value + spoilage_risk_value
        net_hold_benefit = extra_profit - total_hold_cost

        storage_cost_breakdown = {
            'storage_cost': round(total_storage_cost, 0),
            'storage_cost_per_day': round(storage_cost_per_day, 0),
            'degradation_value': round(degradation_value, 0),
            'degradation_pct': round(degradation_pct, 2),
            'spoilage_probability': round(spoilage_prob * 100, 1),
            'spoilage_risk_value': round(spoilage_risk_value, 0),
            'total_hold_cost': round(total_hold_cost, 0),
            'net_hold_benefit': round(net_hold_benefit, 0),
            'hold_worthwhile': net_hold_benefit > 0,
        }

        # 7. Decision logic — enhanced with storage costs
        recommendation = "HOLD"
        if wait_days < 5 or extra_profit < 500 or risk_level == "HIGH":
            recommendation = "SELL NOW"
        # NEW: Override to SELL if holding costs exceed benefit
        if net_hold_benefit < 0:
            recommendation = "SELL NOW"
        # NEW: Override to SELL if spoilage risk > 30%
        if spoilage_prob > 0.3:
            recommendation = "SELL NOW"

        # 8. Simple explanation with weather-aware context
        if recommendation == "HOLD":
            explanation = f"Prices usually rise after harvest season. Wait ~{wait_days} days for better rate."
            if net_hold_benefit > 0:
                explanation += f" Net benefit after storage costs: ₹{net_hold_benefit:,.0f}."
        else:
            if risk_level == "HIGH":
                explanation = "Market is unstable right now. Selling today reduces your risk."
            elif spoilage_prob > 0.3:
                explanation = f"High spoilage risk ({spoilage_prob*100:.0f}%) for {crop}. Sell before quality degrades."
            elif net_hold_benefit < 0:
                explanation = "Storage costs exceed the price benefit of waiting. Sell now."
            else:
                explanation = "Current price is near peak. Good time to sell."

        # Append weather-based advisory to recommendation text
        if isinstance(weather_risk, dict):
            rain_risk = weather_risk.get("rain_risk")
            heat_risk = weather_risk.get("heat_risk")
            humidity_risk = weather_risk.get("humidity_risk")

            if rain_risk == "HIGH":
                recommendation += " Heavy rainfall expected in coming days. Consider early harvesting or protective storage."
            elif rain_risk == "MODERATE":
                recommendation += " Moderate rainfall forecasted. Monitor crop drying and transport plans."

            if heat_risk == "HIGH":
                recommendation += " Extreme heat risk detected. Ensure adequate irrigation."
            elif heat_risk == "MODERATE":
                recommendation += " Rising temperatures expected. Review water management strategy."

            if humidity_risk == "HIGH":
                recommendation += " High humidity may increase fungal infection risk."

        # 9. Storage advice (only if HOLD)
        storage = None
        if recommendation == "HOLD":
            crop_storage = RecommendationService.STORAGE_ADVICE.get(crop, {
                "max_days": 30,
                "method": "Store in a dry, cool place.",
                "risk": "Quality may reduce over time.",
            })
            storage = {
                "safe_days": min(wait_days, crop_storage['max_days']),
                "method": crop_storage['method'],
                "quality_risk": crop_storage['risk'],
                "can_safely_hold": wait_days <= crop_storage['max_days'],
            }

        result = {
            "recommendation": recommendation,
            "sell_now_revenue": round(sell_now_revenue, 0),
            "sell_peak_revenue": round(sell_peak_revenue, 0),
            "extra_profit": round(extra_profit, 0),
            "current_price_per_quintal": round(current_price, 2),
            "peak_price_per_quintal": round(peak_price, 2),
            "total_production_quintals": round(total_quintals, 1),
            "wait_days": wait_days,
            "risk_level": risk_level,
            "risk_emoji": risk_emoji,
            "risk_message": risk_message,
            "explanation": explanation,
            "input_cost": {
                "seed": seed_cost,
                "fertilizer": fertilizer_cost,
                "labour": labour_cost,
                "irrigation": irrigation_cost,
                "total": total_input_cost,
            },
            "profit_if_sell_now": round(profit_now, 0),
            "profit_if_hold": round(profit_peak, 0),
            # NEW fields
            "confidence_band": confidence_band,
            "storage_cost": storage_cost_breakdown,
            "crop": crop,
            "mandi": mandi,
            "weather_risk": weather_risk,
        }

        if storage:
            result["storage_advice"] = storage

        # NEW: Add trust context
        try:
            from services.feature_engine import FeatureEngine
            from services.trust_engine import TrustEngine
            features = FeatureEngine.compute_all_features(crop, district, mandi)
            trust = TrustEngine.build_trust_context(result, features)
            result['trust'] = trust
            result['features'] = features
        except Exception:
            features = None
            result['trust'] = {'confidence_score': 30, 'confidence_label': 'Low — Feature computation unavailable'}

        # NEW: Add crop calendar context
        try:
            from services.crop_calendar import CropCalendar
            state = data.get('state', 'Maharashtra')
            result = CropCalendar.adjust_recommendation(result, crop, state)
        except Exception:
            pass

        # ══════════════════════════════════════════════
        # AI OVERSEER — Meta-layer validation
        # Models → Overseer → Final Advice
        # ══════════════════════════════════════════════
        try:
            from services.overseer_service import Overseer
            from services.groq_explainer import explain_overseer_decision

            # Run all 6 oversight checks (with farmer_id for audit trail)
            oversight = Overseer.evaluate(
                recommendation_data=result,
                forecast_data=price_result,
                features=features,
                farmer_id=data.get('farmer_id'),
            )

            # Apply overrides (recommendation AND wait_days)
            for override in oversight.get('overrides', []):
                if override['field'] == 'recommendation':
                    result['recommendation'] = override['new_value']
                    result['explanation'] = override['reason']
                    result['overseer_overridden'] = True
                elif override['field'] == 'wait_days':
                    result['wait_days'] = override['new_value']
                    result['original_wait_days'] = override['old_value']

            # Propagate risk language labels
            result['confidence_risk_label'] = oversight.get('confidence_risk_label', '')
            result['confidence_risk_message'] = oversight.get('confidence_risk_message', '')

            # Generate natural language explanation via Groq (2s timeout) or template fallback
            ai_explanation = explain_overseer_decision(result, oversight)

            result['overseer'] = oversight
            result['ai_explanation'] = ai_explanation

        except Exception as e:
            result['overseer'] = {
                'verdict': 'UNAVAILABLE',
                'error': str(e),
            }

        return result


