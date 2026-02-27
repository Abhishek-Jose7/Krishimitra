import random
import datetime

class MandiService:
    # Simulated database of mandis with more farmer-relevant data
    MANDIS_DB = [
        {"name": "Pune Mandi", "district": "Pune", "lat": 18.52, "lon": 73.85, "base_price": 2120, "yesterday_price": 2050},
        {"name": "Nashik Mandi", "district": "Nashik", "lat": 19.99, "lon": 73.79, "base_price": 2080, "yesterday_price": 2060},
        {"name": "Nagpur Mandi", "district": "Nagpur", "lat": 21.14, "lon": 79.08, "base_price": 2150, "yesterday_price": 2100},
        {"name": "Aurangabad Mandi", "district": "Aurangabad", "lat": 19.87, "lon": 75.34, "base_price": 2090, "yesterday_price": 2070},
        {"name": "Solapur Mandi", "district": "Solapur", "lat": 17.67, "lon": 75.91, "base_price": 2060, "yesterday_price": 2040},
    ]

    # MSP data (Minimum Support Price) for common crops
    MSP_DATA = {
        "Rice": 2040,
        "Wheat": 2275,
        "Maize": 1962,
        "Soybean": 4600,
        "Cotton": 6620,
    }

    @staticmethod
    def get_nearby_prices(crop, district=None):
        """
        Returns nearby mandi prices with context a farmer actually cares about:
        - Today's price
        - Yesterday's price
        - Price change
        - MSP comparison
        - Distance
        - Transport cost impact
        """
        results = []
        msp = MandiService.MSP_DATA.get(crop, 2040)

        for mandi in MandiService.MANDIS_DB:
            # Simulate daily fluctuation
            today_price = mandi['base_price'] + random.uniform(-50, 80)
            yesterday_price = mandi['yesterday_price'] + random.uniform(-30, 30)
            price_change = today_price - yesterday_price

            # Mock distance based on district
            if district and district == mandi['district']:
                distance = round(random.uniform(3, 15), 1)
            else:
                distance = round(random.uniform(15, 80), 1)

            # Transport cost ~ ₹2/km/quintal (rough estimate)
            transport_cost_per_quintal = round(distance * 2, 0)
            effective_price = today_price - transport_cost_per_quintal

            results.append({
                "mandi": mandi['name'],
                "district": mandi['district'],
                "today_price": round(today_price, 2),
                "yesterday_price": round(yesterday_price, 2),
                "price_change": round(price_change, 2),
                "msp": msp,
                "above_msp": round(today_price - msp, 2),
                "distance_km": distance,
                "transport_cost": transport_cost_per_quintal,
                "effective_price": round(effective_price, 2),
            })

        # Sort by effective price (highest real earning first)
        results.sort(key=lambda x: x['effective_price'], reverse=True)
        return results

    @staticmethod
    def get_market_risk():
        """
        Simple market risk signal:
        GREEN = Stable, YELLOW = Moderate fluctuation, RED = Highly volatile
        """
        # In real app, compute from actual price variance
        volatility = random.uniform(0, 1)
        if volatility < 0.3:
            return {"level": "LOW", "color": "green", "message": "Market is stable. Good time to plan."}
        elif volatility < 0.7:
            return {"level": "MEDIUM", "color": "yellow", "message": "Some fluctuation expected. Stay alert."}
        else:
            return {"level": "HIGH", "color": "red", "message": "Market is volatile. Avoid panic selling."}
