import requests
import os
import random

class WeatherService:
    API_KEY = os.environ.get('OPENWEATHER_API_KEY')
    BASE_URL = "http://api.openweathermap.org/data/2.5/weather"

    @staticmethod
    def get_weather(district, season=None, sowing_date=None):
        """
        Fetches weather data for a district.

        `season` and `sowing_date` are accepted for future extensions where we might
        fetch season-aware or growth-stage-specific weather summaries. For now they
        are not used directly but keep the interface aligned with agronomy needs.

        Falls back to mock data if API key is missing or request fails.
        """
        if WeatherService.API_KEY:
            try:
                params = {
                    'q': f"{district},IN",
                    'appid': WeatherService.API_KEY,
                    'units': 'metric'
                }
                response = requests.get(WeatherService.BASE_URL, params=params)
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'temp': data['main']['temp'],
                        'humidity': data['main']['humidity'],
                        'rainfall': random.uniform(0, 100), # Rainfall often needs specialized API, mocking for now
                        'condition': data['weather'][0]['description']
                    }
            except Exception as e:
                print(f"Weather API failed: {e}")
        
        # Fallback Mock Data
        return {
            'temp': random.uniform(25, 35),
            'humidity': random.uniform(40, 80),
            'rainfall': random.uniform(0, 10),
            'condition': 'Sunny (Simulated)'
        }
