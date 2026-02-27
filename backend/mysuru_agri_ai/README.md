Mysuru Smart Yield Simulation & Optimization Engine
===================================================

This project is a production-oriented precision agriculture AI system for Mysuru district, Karnataka. It provides:

- Yield prediction models trained on historical weather, management, and soil nutrient data.
- A scenario simulation engine that generates all valid crop–season–soil–irrigation–area combinations.
- Batch yield prediction, ranking, and optimization across scenarios.
- A professional advisory engine that produces human-readable farming recommendations.
- A FastAPI backend exposing a `/simulate` endpoint that returns plain-text advisory output.

## Project layout

- `data/`: CSV inputs such as `mysore2021-.csv`, `data_season.csv`, `Crop_recommendation.csv`.
- `models/`: Persisted artifacts (`yield_model.pkl`, `preprocessor.pkl`, `scaler.pkl`, `encoders.pkl`, `metadata.json`).
- `pipeline/`: Data loading, preprocessing, model training, and batch prediction utilities.
- `simulation/`: Option extraction, permutation generation, batch prediction, and ranking logic.
- `advisory/`: Text advisory generation from ranked scenarios, confidence, and risk.
- `app/`: FastAPI application exposing the simulation API.

## Quickstart

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Place the raw CSV files in `data/`:

- `data/mysore2021-.csv`
- `data/data_season.csv`
- `data/Crop_recommendation.csv`

4. Train the model:

```bash
python -m mysuru_agri_ai.pipeline.train
```

This will produce model artifacts and evaluation plots under `models/`.

5. Run the API:

```bash
uvicorn mysuru_agri_ai.app.main:app --host 0.0.0.0 --port 8000
```

6. Call the simulation endpoint:

```bash
curl -X POST "http://localhost:8000/simulate" ^
  -H "Content-Type: application/json" ^
  -d "{\"crop\":[\"Coconut\",\"Arecanut\"],\"season\":[\"Kharif\",\"Rabi\"],\"soil_type\":[\"Red\",\"Laterite\"],\"irrigation\":[\"Drip\",\"Sprinkler\"],\"area\":[1,2]}"
```

The response is a human-readable advisory report rather than JSON.

## Docker usage

Build and run the container:

```bash
docker build -t mysuru-agri-ai .
docker run -p 8000:8000 mysuru-agri-ai
```

## Extending to other districts

The data pipeline and simulation logic accept a `district` parameter, so additional Karnataka districts can be supported by:

- Ingesting district-specific weather and management data into `data/`.
- Training new model versions.
- Deploying updated artifacts alongside existing ones using model version metadata.

