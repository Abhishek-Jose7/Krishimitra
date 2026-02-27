import pickle
import os
import random

class DummyYieldModel:
    def predict(self, features):
        # crop, district, land_size, soil_type (encoded)
        # Dummy logic: return random yield between 10 and 50 quintals per acre
        return [random.uniform(10, 50)]

class DummyPriceModel:
    def forecast(self, crop, mandi, days=90):
        # Dummy logic: return a trend
        base_price = random.uniform(2000, 5000)
        trend = []
        for i in range(days):
            trend.append(base_price + random.uniform(-100, 100) + (i * 5)) # Slight upward trend
        return trend

def generate_models():
    models_dir = 'backend/models'
    if not os.path.exists(models_dir):
        os.makedirs(models_dir)

    yield_model = DummyYieldModel()
    price_model = DummyPriceModel()

    with open(os.path.join(models_dir, 'yield_model.pkl'), 'wb') as f:
        pickle.dump(yield_model, f)
    
    with open(os.path.join(models_dir, 'price_forecast_model.pkl'), 'wb') as f:
        pickle.dump(price_model, f)

    print("Dummy models generated successfully.")

if __name__ == "__main__":
    generate_models()
