import pickle
import os
import random
import numpy as np
import datetime


class DummyPriceModel:
    """Fallback dummy model for price forecasting."""
    def forecast(self, crop, mandi, days=90):
        base_price = random.uniform(2000, 5000)
        return [base_price + random.uniform(-100, 100) + (i * 5) for i in range(days)]


class _CustomUnpickler(pickle.Unpickler):
    """Handles models pickled in __main__ context."""
    def find_class(self, module, name):
        if name == 'DummyPriceModel':
            return DummyPriceModel
        return super().find_class(module, name)


class PriceService:
    _model = None

    @classmethod
    def load_model(cls):
        if cls._model is None:
            model_path = os.path.join(os.path.dirname(__file__), '../models/price_forecast_model.pkl')
            try:
                with open(model_path, 'rb') as f:
                    cls._model = _CustomUnpickler(f).load()
            except FileNotFoundError:
                print("Price model not found, using fallback")
                cls._model = DummyPriceModel()
            except Exception as e:
                print(f"Model load error: {e}, using fallback")
                cls._model = DummyPriceModel()

    @staticmethod
    def forecast_price(data):
        crop  = data.get('crop', '')
        mandi = data.get('mandi', '')
        state = data.get('state', '')

        # ── Karnataka-specific models (groundnut / coconut) ──
        try:
            from services.karnataka_predictor import KarnatakaForecaster
            if KarnatakaForecaster.is_supported(state, crop):
                ka_result = KarnatakaForecaster.get_forecast(
                    crop=crop,
                    market=mandi,
                    quantity=float(data.get('quantity', 10)),
                )
                if ka_result:
                    today = ka_result["today"]
                    fc7   = ka_result["forecast_7day"]
                    d30   = ka_result["day_30"]

                    # Trend based on 7-day endpoint vs today
                    trend = "Stable"
                    if ka_result["trend_7d_pct"] > 3:
                        trend = "Rising"
                    elif ka_result["trend_7d_pct"] < -3:
                        trend = "Falling"

                    # Build unified forecast list (7 days + day 30)
                    forecast_list = [
                        {"date": f["date"], "price": f["price"]}
                        for f in fc7
                    ]

                    # Peak among 7-day window
                    peak = max(fc7, key=lambda x: x["price"])

                    return {
                        'current_price'      : today["predicted_price"],
                        'trend'              : trend,
                        'peak_date'          : peak["date"],
                        'peak_price'         : peak["price"],
                        'volatility'         : round(np.std([f["price"] for f in fc7]) /
                                                     max(np.mean([f["price"] for f in fc7]), 1), 2),
                        'forecast'           : forecast_list,
                        'karnataka_forecast' : {
                            'today'             : today,
                            'forecast_7day'     : fc7,
                            'day_30'            : d30,
                            'trend_7d_pct'      : ka_result["trend_7d_pct"],
                            'best_day'          : ka_result["best_day"],
                            'model_info'        : ka_result["model_info"],
                            'available_markets' : ka_result["available_markets"],
                        },
                    }
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Karnataka model error: {e}")

        # ── Fallback: existing dummy model ────────────────────
        PriceService.load_model()
        if not PriceService._model:
            return None

        # Get 90 day forecast
        forecast_values = PriceService._model.forecast(crop, mandi, days=90)
        
        current_price = forecast_values[0]
        forecast_30 = forecast_values[29]
        forecast_60 = forecast_values[59]
        forecast_90 = forecast_values[89]

        # Determine trend
        trend = "Stable"
        if forecast_90 > current_price * 1.05:
            trend = "Rising"
        elif forecast_90 < current_price * 0.95:
            trend = "Falling"

        # Calculate volatility (mock standard deviation of forecast)
        volatility = round(np.std(forecast_values) / np.mean(forecast_values), 2)

        # Find peak
        peak_price = max(forecast_values)
        peak_day_idx = forecast_values.index(peak_price)
        peak_date = (datetime.date.today() + datetime.timedelta(days=peak_day_idx)).isoformat()

        # Format forecast list
        forecast_list = []
        start_date = datetime.date.today()
        for i, price in enumerate(forecast_values):
            date_str = (start_date + datetime.timedelta(days=i)).isoformat()
            forecast_list.append({"date": date_str, "price": round(price, 2)})

        return {
            'current_price': round(current_price, 2),
            'trend': trend,
            'peak_date': peak_date,
            'peak_price': round(peak_price, 2),
            'volatility': volatility,
            'forecast': forecast_list
        }
