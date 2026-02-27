import requests
import os
import random

class WeatherService:
    API_KEY = os.environ.get("OPENWEATHER_API_KEY")
    CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
    FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

    @staticmethod
    def get_weather(district, season=None, sowing_date=None):
        """Fetch current weather (lightweight use). Extra params reserved for future use."""
        if WeatherService.API_KEY:
            try:
                params = {
                    'q': f"{district},IN",
                    'appid': WeatherService.API_KEY,
                    'units': 'metric'
                }
                response = requests.get(WeatherService.CURRENT_URL, params=params)
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'temp': data['main']['temp'],
                        'humidity': data['main']['humidity'],
                        'condition': data['weather'][0]['description']
                    }
            except Exception as e:
                print(f"Weather API failed: {e}")

        # Fallback
        return {
            'temp': random.uniform(25, 35),
            'humidity': random.uniform(50, 85),
            'condition': 'Sunny (Simulated)'
        }

    @staticmethod
    def get_forecast(district):
        """Fetch 5-day forecast (required for risk analysis)"""
        if WeatherService.API_KEY:
            try:
                params = {
                    'q': f"{district},IN",
                    'appid': WeatherService.API_KEY,
                    'units': 'metric'
                }
                response = requests.get(WeatherService.FORECAST_URL, params=params)
                if response.status_code == 200:
                    return response.json()
            except Exception as e:
                print(f"Forecast API failed: {e}")
        return None

    @staticmethod
    def calculate_weather_risk(district):
        """
        Calculate rain, heat, and humidity risk using forecast data.
        """
        forecast_data = WeatherService.get_forecast(district)

        # Default risk
        risk = {
            "rain_risk": "LOW",
            "heat_risk": "LOW",
            "humidity_risk": "LOW"
        }

        if not forecast_data:
            return risk

        forecast_list = forecast_data.get("list", [])[:15]  # next ~48 hours

        total_rain = 0
        high_temp_blocks = 0
        high_humidity_blocks = 0

        for block in forecast_list:
            main = block.get("main", {})
            temp = main.get("temp", 0)
            humidity = main.get("humidity", 0)
            rain = block.get("rain", {}).get("3h", 0)

            total_rain += rain

            if temp >= 35:
                high_temp_blocks += 1

            if humidity >= 80:
                high_humidity_blocks += 1

        # Rain risk logic
        if total_rain > 30:
            risk["rain_risk"] = "HIGH"
        elif total_rain > 10:
            risk["rain_risk"] = "MODERATE"

        # Heat risk logic
        if high_temp_blocks >= 3:
            risk["heat_risk"] = "HIGH"
        elif high_temp_blocks >= 1:
            risk["heat_risk"] = "MODERATE"

        # Humidity risk logic
        if high_humidity_blocks >= 3:
            risk["humidity_risk"] = "HIGH"
        elif high_humidity_blocks >= 1:
            risk["humidity_risk"] = "MODERATE"

        return risk
