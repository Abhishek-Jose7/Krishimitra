import requests
import json

url = "http://localhost:5000/price/forecast"
params = {
    "crop": "cabbage",
    "state": "maharashtra",
    "mandi": "Pune"
}

try:
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    
    print("Success! Received payload:")
    print(json.dumps(data, indent=2))
    
    # Check for maharashtra specific keys
    if "maharashtra_forecast" in data:
        print("\n✅ maharashtra_forecast key found in response.")
        
        mh_data = data["maharashtra_forecast"]
        
        expected_keys = ["today", "forecast_7day", "day_30", "trend_7d_pct", "best_day", "model_info", "available_markets"]
        missing_keys = [k for k in expected_keys if k not in mh_data]
        
        if missing_keys:
            print(f"❌ Missing keys in maharashtra_forecast: {missing_keys}")
        else:
            print("✅ All expected keys present in maharashtra_forecast.")
    else:
        print("❌ maharashtra_forecast key NOT found in response.")
        
except requests.exceptions.RequestException as e:
    print(f"Error making request: {e}")
