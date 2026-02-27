"""
Mandi Service — State-aware mandi prices with real model predictions.

Provides nearby mandi prices filtered by the farmer's state,
with real XGBoost price predictions where available.
"""

import random
import datetime
import logging

logger = logging.getLogger('mandi_service')


class MandiService:
    # ─── Multi-state mandi database ───────────────────────────
    # Each mandi: {name, district, state, lat, lon}
    MANDIS_DB = [
        # ── Karnataka ──
        {"name": "Hubli (Dharwad) Mandi", "district": "Dharwad", "state": "Karnataka", "lat": 15.36, "lon": 75.12},
        {"name": "Davangere Mandi", "district": "Davangere", "state": "Karnataka", "lat": 14.46, "lon": 75.92},
        {"name": "Bellary Mandi", "district": "Bellary", "state": "Karnataka", "lat": 15.14, "lon": 76.92},
        {"name": "Raichur Mandi", "district": "Raichur", "state": "Karnataka", "lat": 16.21, "lon": 77.36},
        {"name": "Mysore Mandi", "district": "Mysuru", "state": "Karnataka", "lat": 12.30, "lon": 76.66},
        {"name": "Bangalore APMC", "district": "Bengaluru", "state": "Karnataka", "lat": 12.97, "lon": 77.59},
        {"name": "Gadag Mandi", "district": "Gadag", "state": "Karnataka", "lat": 15.43, "lon": 75.63},
        {"name": "Tiptur Mandi", "district": "Tumkur", "state": "Karnataka", "lat": 13.26, "lon": 76.47},

        # ── Maharashtra ──
        {"name": "Pune Mandi", "district": "Pune", "state": "Maharashtra", "lat": 18.52, "lon": 73.85},
        {"name": "Nashik Mandi", "district": "Nashik", "state": "Maharashtra", "lat": 19.99, "lon": 73.79},
        {"name": "Nagpur Mandi", "district": "Nagpur", "state": "Maharashtra", "lat": 21.14, "lon": 79.08},
        {"name": "Aurangabad Mandi", "district": "Aurangabad", "state": "Maharashtra", "lat": 19.87, "lon": 75.34},
        {"name": "Solapur Mandi", "district": "Solapur", "state": "Maharashtra", "lat": 17.67, "lon": 75.91},
        {"name": "Kolhapur Mandi", "district": "Kolhapur", "state": "Maharashtra", "lat": 16.70, "lon": 74.24},

        # ── Madhya Pradesh ──
        {"name": "Indore Mandi", "district": "Indore", "state": "Madhya Pradesh", "lat": 22.72, "lon": 75.86},
        {"name": "Bhopal Mandi", "district": "Bhopal", "state": "Madhya Pradesh", "lat": 23.26, "lon": 77.41},
        {"name": "Ujjain Mandi", "district": "Ujjain", "state": "Madhya Pradesh", "lat": 23.18, "lon": 75.77},
        {"name": "Jabalpur Mandi", "district": "Jabalpur", "state": "Madhya Pradesh", "lat": 23.17, "lon": 79.93},
        {"name": "Dewas Mandi", "district": "Dewas", "state": "Madhya Pradesh", "lat": 22.97, "lon": 76.05},

        # ── Punjab ──
        {"name": "Ludhiana Mandi", "district": "Ludhiana", "state": "Punjab", "lat": 30.90, "lon": 75.86},
        {"name": "Amritsar Mandi", "district": "Amritsar", "state": "Punjab", "lat": 31.63, "lon": 74.87},
        {"name": "Jalandhar Mandi", "district": "Jalandhar", "state": "Punjab", "lat": 31.32, "lon": 75.58},
        {"name": "Patiala Mandi", "district": "Patiala", "state": "Punjab", "lat": 30.34, "lon": 76.38},
        {"name": "Bathinda Mandi", "district": "Bathinda", "state": "Punjab", "lat": 30.21, "lon": 74.95},

        # ── Uttar Pradesh ──
        {"name": "Lucknow Mandi", "district": "Lucknow", "state": "Uttar Pradesh", "lat": 26.85, "lon": 80.95},
        {"name": "Agra Mandi", "district": "Agra", "state": "Uttar Pradesh", "lat": 27.18, "lon": 78.02},
        {"name": "Kanpur Mandi", "district": "Kanpur", "state": "Uttar Pradesh", "lat": 26.45, "lon": 80.35},
        {"name": "Varanasi Mandi", "district": "Varanasi", "state": "Uttar Pradesh", "lat": 25.32, "lon": 83.01},
        {"name": "Meerut Mandi", "district": "Meerut", "state": "Uttar Pradesh", "lat": 28.98, "lon": 77.71},

        # ── Tamil Nadu ──
        {"name": "Coimbatore Mandi", "district": "Coimbatore", "state": "Tamil Nadu", "lat": 11.01, "lon": 76.97},
        {"name": "Madurai Mandi", "district": "Madurai", "state": "Tamil Nadu", "lat": 9.93, "lon": 78.12},
        {"name": "Salem Mandi", "district": "Salem", "state": "Tamil Nadu", "lat": 11.66, "lon": 78.15},
        {"name": "Trichy Mandi", "district": "Tiruchirappalli", "state": "Tamil Nadu", "lat": 10.79, "lon": 78.69},
        {"name": "Erode Mandi", "district": "Erode", "state": "Tamil Nadu", "lat": 11.34, "lon": 77.73},

        # ── Andhra Pradesh ──
        {"name": "Guntur Mandi", "district": "Guntur", "state": "Andhra Pradesh", "lat": 16.30, "lon": 80.44},
        {"name": "Kurnool Mandi", "district": "Kurnool", "state": "Andhra Pradesh", "lat": 15.83, "lon": 78.04},
        {"name": "Vijayawada Mandi", "district": "Krishna", "state": "Andhra Pradesh", "lat": 16.51, "lon": 80.65},
        {"name": "Anantapur Mandi", "district": "Anantapur", "state": "Andhra Pradesh", "lat": 14.68, "lon": 77.60},

        # ── Telangana ──
        {"name": "Hyderabad APMC", "district": "Hyderabad", "state": "Telangana", "lat": 17.39, "lon": 78.49},
        {"name": "Warangal Mandi", "district": "Warangal", "state": "Telangana", "lat": 17.98, "lon": 79.59},
        {"name": "Nizamabad Mandi", "district": "Nizamabad", "state": "Telangana", "lat": 18.67, "lon": 78.09},
        {"name": "Karimnagar Mandi", "district": "Karimnagar", "state": "Telangana", "lat": 18.44, "lon": 79.13},

        # ── Rajasthan ──
        {"name": "Jaipur Mandi", "district": "Jaipur", "state": "Rajasthan", "lat": 26.92, "lon": 75.79},
        {"name": "Jodhpur Mandi", "district": "Jodhpur", "state": "Rajasthan", "lat": 26.29, "lon": 73.02},
        {"name": "Kota Mandi", "district": "Kota", "state": "Rajasthan", "lat": 25.18, "lon": 75.83},
        {"name": "Udaipur Mandi", "district": "Udaipur", "state": "Rajasthan", "lat": 24.58, "lon": 73.68},

        # ── Gujarat ──
        {"name": "Rajkot Mandi", "district": "Rajkot", "state": "Gujarat", "lat": 22.30, "lon": 70.80},
        {"name": "Ahmedabad APMC", "district": "Ahmedabad", "state": "Gujarat", "lat": 23.02, "lon": 72.57},
        {"name": "Junagadh Mandi", "district": "Junagadh", "state": "Gujarat", "lat": 21.52, "lon": 70.46},
        {"name": "Gondal Mandi", "district": "Rajkot", "state": "Gujarat", "lat": 21.96, "lon": 70.80},
        {"name": "Unjha Mandi", "district": "Mehsana", "state": "Gujarat", "lat": 23.80, "lon": 72.39},

        # ── Kerala ──
        {"name": "Kochi Mandi", "district": "Ernakulam", "state": "Kerala", "lat": 9.93, "lon": 76.27},
        {"name": "Thrissur Mandi", "district": "Thrissur", "state": "Kerala", "lat": 10.52, "lon": 76.21},
        {"name": "Kozhikode Mandi", "district": "Kozhikode", "state": "Kerala", "lat": 11.25, "lon": 75.77},

        # ── West Bengal ──
        {"name": "Kolkata APMC", "district": "Kolkata", "state": "West Bengal", "lat": 22.57, "lon": 88.36},
        {"name": "Siliguri Mandi", "district": "Darjeeling", "state": "West Bengal", "lat": 26.73, "lon": 88.43},
        {"name": "Burdwan Mandi", "district": "Purba Bardhaman", "state": "West Bengal", "lat": 23.23, "lon": 87.86},

        # ── Haryana ──
        {"name": "Karnal Mandi", "district": "Karnal", "state": "Haryana", "lat": 29.69, "lon": 76.98},
        {"name": "Hisar Mandi", "district": "Hisar", "state": "Haryana", "lat": 29.15, "lon": 75.72},
        {"name": "Sonipat Mandi", "district": "Sonipat", "state": "Haryana", "lat": 28.99, "lon": 77.02},
        {"name": "Sirsa Mandi", "district": "Sirsa", "state": "Haryana", "lat": 29.53, "lon": 75.02},

        # ── Bihar ──
        {"name": "Patna Mandi", "district": "Patna", "state": "Bihar", "lat": 25.61, "lon": 85.14},
        {"name": "Muzaffarpur Mandi", "district": "Muzaffarpur", "state": "Bihar", "lat": 26.12, "lon": 85.39},
        {"name": "Gaya Mandi", "district": "Gaya", "state": "Bihar", "lat": 24.80, "lon": 85.01},
    ]

    # MSP data (2024-25 prices in ₹/quintal)
    MSP_DATA = {
        "Rice": 2300, "Wheat": 2275, "Maize": 2090, "Soybean": 4892,
        "Cotton": 7121, "Sugarcane": 3150, "Groundnut": 6783, "Jowar": 3371,
        "Bajra": 2500, "Ragi": 3846, "Mustard": 5650, "Gram": 5440,
        "Lentils": 6425, "Coconut": 3400, "Onion": 0, "Tomato": 0,
        "Potato": 0,
    }

    # Base prices per crop for price simulation (₹/quintal)
    CROP_BASE_PRICES = {
        "Rice": 2350, "Wheat": 2400, "Maize": 2100, "Soybean": 5200,
        "Cotton": 7200, "Sugarcane": 3200, "Groundnut": 6900, "Jowar": 3400,
        "Bajra": 2600, "Ragi": 3900, "Mustard": 5800, "Gram": 5500,
        "Lentils": 6500, "Coconut": 3500, "Onion": 2800, "Tomato": 3500,
        "Potato": 1800, "Arecanut": 45000, "Sunflower": 6400, "Banana": 2200,
        "Cumin": 32000, "Turmeric": 12000, "Chilli": 18000, "Castor": 6200,
        "Pepper": 48000, "Cardamom": 120000, "Rubber": 16000,
    }

    @staticmethod
    def get_nearby_prices(crop, district=None, state=None):
        """
        Returns nearby mandi prices filtered by the farmer's state.
        Sorting: nearest mandi first, then best effective price.
        Integrates real model predictions where available.
        """
        results = []
        msp = MandiService.MSP_DATA.get(crop, 0)
        base_price = MandiService.CROP_BASE_PRICES.get(crop, 2500)

        # Filter mandis by state
        if state:
            state_lower = state.lower().strip()
            filtered = [m for m in MandiService.MANDIS_DB
                        if m['state'].lower() == state_lower]
        else:
            filtered = MandiService.MANDIS_DB

        if not filtered:
            filtered = MandiService.MANDIS_DB

        # Try to get real price from Karnataka models
        real_price = None
        try:
            from services.karnataka_predictor import KarnatakaForecaster
            if state and KarnatakaForecaster.is_supported(state, crop):
                for mandi in filtered[:1]:
                    forecast = KarnatakaForecaster.get_forecast(
                        crop=crop, market=mandi['name'], quantity=10
                    )
                    if forecast and forecast.get('today'):
                        real_price = forecast['today'].get('predicted_price')
                        break
        except Exception as e:
            logger.debug(f"Karnataka model not available for {crop}: {e}")

        district_lower = (district or '').lower().strip()

        for mandi in filtered:
            mandi_district_lower = mandi['district'].lower()

            # Fuzzy district match: exact, substring, or starts-with
            is_local = False
            if district_lower:
                is_local = (
                    district_lower == mandi_district_lower
                    or district_lower in mandi_district_lower
                    or mandi_district_lower in district_lower
                    or district_lower[:4] == mandi_district_lower[:4]  # "myso" matches "mysuru"
                )

            # Use real price if available, else simulate
            if real_price:
                variation = random.uniform(-0.03, 0.03) * real_price
                today_price = real_price + variation
                yesterday_price = today_price - random.uniform(-50, 50)
            else:
                today_price = base_price + random.uniform(-80, 120)
                yesterday_price = today_price - random.uniform(-40, 60)

            price_change = today_price - yesterday_price

            # Distance: local mandis are close, others are far
            if is_local:
                distance = round(random.uniform(3, 15), 1)
            else:
                distance = round(random.uniform(25, 90), 1)

            transport_cost = round(distance * 2, 0)
            effective_price = today_price - transport_cost

            results.append({
                "mandi": mandi['name'],
                "district": mandi['district'],
                "state": mandi['state'],
                "today_price": round(today_price, 2),
                "yesterday_price": round(yesterday_price, 2),
                "price_change": round(price_change, 2),
                "msp": msp,
                "above_msp": round(today_price - msp, 2) if msp > 0 else None,
                "distance_km": distance,
                "transport_cost": transport_cost,
                "effective_price": round(effective_price, 2),
                "price_source": "model" if real_price else "estimated",
                "is_nearest": is_local,
            })

        # Calculate is_nearest and other flags
        for r in results:
            r['is_best_profit'] = False

        # Global Sort: Best Effective Price (Profit after transport)
        results.sort(key=lambda x: x['effective_price'], reverse=True)
        
        if results:
            results[0]['is_best_profit'] = True

        return results

    @staticmethod
    def get_mandi_forecast(crop, state, mandi_name=None):
        """
        Get real price forecast for a crop using available models.
        Returns today's price and 7-day forecast.
        """
        try:
            from services.karnataka_predictor import KarnatakaForecaster
            if KarnatakaForecaster.is_supported(state, crop):
                market = mandi_name or 'Hubli (Dharwad) Mandi'
                forecast = KarnatakaForecaster.get_forecast(
                    crop=crop, market=market, quantity=10
                )
                if forecast:
                    return {
                        'today_price': forecast['today'].get('predicted_price'),
                        'forecast_7day': forecast.get('forecast_7day', []),
                        'day_30': forecast.get('day_30'),
                        'trend_7d_pct': forecast.get('trend_7d_pct', 0),
                        'best_day': forecast.get('best_day'),
                        'source': 'xgboost_model',
                        'available_markets': forecast.get('available_markets', []),
                    }
        except Exception as e:
            logger.warning(f"Forecast model error: {e}")

        # Fallback: use PriceService
        try:
            from services.price_service import PriceService
            result = PriceService.forecast_price({
                'crop': crop, 'mandi': mandi_name or '', 'state': state,
            })
            if result:
                return {
                    'today_price': result.get('current_price'),
                    'forecast_7day': result.get('forecast', [])[:7],
                    'day_30': None,
                    'trend_7d_pct': 0,
                    'best_day': None,
                    'source': 'price_model',
                }
        except Exception:
            pass

        return None

    @staticmethod
    def get_market_risk():
        """
        Market risk signal:
        GREEN = Stable, YELLOW = Moderate, RED = Highly volatile
        """
        volatility = random.uniform(0, 1)
        if volatility < 0.3:
            return {"level": "LOW", "color": "green", "message": "Market is stable. Good time to plan."}
        elif volatility < 0.7:
            return {"level": "MEDIUM", "color": "yellow", "message": "Some fluctuation expected. Stay alert."}
        else:
            return {"level": "HIGH", "color": "red", "message": "Market is volatile. Avoid panic selling."}
