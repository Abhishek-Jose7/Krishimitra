# KrishiMitra AI

**AI-powered decision support system for Indian farmers.** KrishiMitra helps farmers with yield estimation, price forecasting, sell/hold recommendations, mandi price comparison, pest identification, financial protection insights, loan risk simulation, and personalized dashboards—all through a single Flutter app backed by a Flask API and ML pipeline.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Setup Instructions](#setup-instructions)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Mobile App](#mobile-app)
- [ML Pipeline (Yield)](#ml-pipeline-yield)
- [Related Documentation](#related-documentation)

---

## Features

| Feature | Description |
|--------|-------------|
| **Yield Estimation** | Predict crop output (tons/acre and total) from district, crop, season, soil, irrigation, and area. Uses ML models in `mysuru_agri_ai`; falls back to indicative estimates when data is limited. No errors shown—always returns an advisory. |
| **Price Forecasting** | Short- and long-term price trends for crops and mandis. |
| **Sell/Hold Advice** | Recommendations on when to sell or hold inventory for better returns. |
| **Mandi Prices** | Compare nearby market rates. |
| **Intelligent Dashboard** | Region- and crop-aware dashboard: weather, mandi prices, recommendation, Karnataka-specific forecasts, saved yield advisory. |
| **Pest / Leaf Scan** | Identify crop issues via image (pest vision). |
| **Financial Protection** | Risk assessment (weather, market, yield) and recommended schemes/insurance. |
| **Loan & Credit Risk Assistant** | Financial stress simulator: loan amount, tenure, interest → risk score, repayment ratio, worst-case scenario, and recommendations (PMFBY, tenure, etc.). |
| **Farmer Profile & Onboarding** | Multi-crop farm setup, soil/irrigation, preferred mandi. Optional: yield runs automatically after onboarding and is stored for the dashboard. |
| **Notifications** | Price alerts and alerts management. |
| **Auth** | OTP-based and password-based auth; JWT. |

---

## Architecture

- **Backend:** Flask (Python). Handles HTTP only; no ML logic in routes. Uses services for business logic and ML invocation.
- **ML:** Isolated in `backend/mysuru_agri_ai/` (pipeline: preprocess → train → predict; simulation: permutation engine, ranking, advisory). Flask calls `yield_service.get_yield_advisory()` etc.; the FastAPI app in `mysuru_agri_ai` is optional and not required for the Flutter app.
- **Mobile:** Flutter (Dart). Connects to Flask at `localhost:5000` (Windows) or `10.0.2.2:5000` (Android emulator).
- **Database:** PostgreSQL (recommended) or SQLite (dev). Config via `DATABASE_URL`.

---

## Project Structure

```
Krishimitra/
├── backend/
│   ├── app.py                 # Flask app factory, blueprint registration, DB migration stubs
│   ├── config.py              # Config from env (DATABASE_URL, GROQ_API_KEY, etc.)
│   ├── requirements.txt       # Python dependencies
│   ├── .env                   # Local env (do not commit secrets)
│   ├── routes/                # HTTP layer only
│   │   ├── auth_routes.py     # /auth/send-otp, verify-otp, update-profile, register, login
│   │   ├── farmer_routes.py   # /farmer/register, /dashboard, /farmer/<id>
│   │   ├── yield_routes.py    # /yield/predict, /yield/simulate, /yield/options, /yield/actual
│   │   ├── price_routes.py    # /price/forecast
│   │   ├── mandi_routes.py    # /mandi/prices, /mandi/forecast, /mandi/risk
│   │   ├── recommendation_routes.py  # /api/recommendation
│   │   ├── dashboard_routes.py      # /dashboard/intelligent, /dashboard/strategy
│   │   ├── farm_routes.py     # /farms, /crops/suggest, /farm/analyze-pest
│   │   ├── weather_routes.py  # /weather-risk
│   │   ├── financial_routes.py    # /financial-protection
│   │   ├── loan_routes.py         # /loan-risk
│   │   ├── notification_routes.py  # /notifications/alert, /alerts/...
│   │   └── evaluation_routes.py    # /metrics/evaluation, accuracy, track
│   ├── services/             # Business logic + ML invocation
│   │   ├── yield_service.py  # get_yield_advisory, get_yield_options, _fallback_yield_advisory
│   │   ├── farmer_service.py
│   │   ├── recommendation_service.py
│   │   ├── mandi_service.py
│   │   ├── financial_advisor_service.py
│   │   ├── loan_risk_service.py   # Loan & Credit Risk Assistant
│   │   └── ...
│   ├── database/
│   │   ├── db.py
│   │   └── models.py         # User, Farm, FarmCrop, YieldPrediction, PriceAlert, etc.
│   ├── models/               # Legacy pickle models (e.g. yield_model.pkl)
│   └── mysuru_agri_ai/        # ML module (yield pipeline)
│       ├── pipeline/        # train.py, predict.py, preprocess.py
│       ├── simulation/      # permutation_engine.py, ranking_engine.py
│       ├── advisory/        # advisory_engine.py
│       ├── data/            # CSVs (data_season, weather, etc.)
│       └── models/           # yield_model.pkl, preprocessor.pkl, metadata.json
├── mobile_app/
│   └── lib/
│       ├── main.dart
│       ├── screens/          # dashboard_screen, yield_screen, mandi_screen, etc.
│       ├── providers/        # FarmerProfile, Localization
│       ├── services/         # ApiService
│       └── widgets/
├── csv/                      # Datasets / exported CSVs
├── docker-compose.yml        # Backend + PostgreSQL
├── README.md                 # This file
├── README_FINANCIAL_PROTECTION.md
└── backend/FINANCIAL_PROTECTION_CENTER.md
```

---

## Setup Instructions

### Prerequisites

- **Python 3.10+** (3.13 compatible; see `backend/requirements.txt`)
- **PostgreSQL** (or use SQLite for quick local dev)
- **Flutter SDK** (for mobile app)
- **Docker & Docker Compose** (optional, for backend + DB)

---

### Option 1: Docker (Backend + PostgreSQL)

```bash
docker compose up --build
```

- API: `http://localhost:5000`
- DB: PostgreSQL on port `5432` (user/password/db from `docker-compose.yml`)

Use `docker compose` (with a space) on newer Docker versions.

---

### Option 2: Local Python (Flask backend only)

1. **Database**
   - **PostgreSQL:** Create a database (e.g. `krishimitra`) and set `DATABASE_URL`.
   - **SQLite (dev):** Omit `DATABASE_URL` or set it to `sqlite:///krishimitra.db` (file created under `backend/` or project root as per config).

2. **Environment**
   - Copy `.env.example` to `.env` if present, or create `backend/.env` with at least:
     - `DATABASE_URL` (PostgreSQL or SQLite)
     - `SECRET_KEY`
     - Optional: `GROQ_API_KEY`, `OPENWEATHER_API_KEY`, Supabase vars (see [Environment Variables](#environment-variables)).

3. **Install and run**
   ```bash
   cd backend
   pip install -r requirements.txt
   # Optional: generate dummy models if you don't have mysuru_agri_ai models
   python models/generate_dummy_models.py
   python app.py
   ```
   Server runs at `http://localhost:5000`.

4. **Yield ML (optional but recommended)**
   - Ensure `mysuru_agri_ai` has data and trained artifacts under `backend/mysuru_agri_ai/data/` and `backend/mysuru_agri_ai/models/` (e.g. `yield_model.pkl`, `preprocessor.pkl`, `metadata.json`).
   - If you use a separate FastAPI app for development:
     ```bash
     pip install -r mysuru_agri_ai/requirements.txt
     uvicorn mysuru_agri_ai.app.main:app --reload --port 8000
     ```
   - The **Flutter app uses the Flask backend only**; yield is served via Flask routes that call `yield_service.get_yield_advisory()`.

---

### Option 3: Flutter app (with backend running)

1. Start the backend (Option 1 or 2).
2. In another terminal:
   ```bash
   cd mobile_app
   flutter pub get
   # Windows desktop
   flutter run -d windows
   # Android (emulator)
   flutter run
   ```
- **Windows:** App uses `http://localhost:5000`.
- **Android emulator:** App uses `http://10.0.2.2:5000`.

---

## Environment Variables

Configure these in `backend/.env` (or your deployment environment). Do not commit real secrets.

| Variable | Description | Default / Note |
|----------|-------------|----------------|
| `DATABASE_URL` | PostgreSQL or SQLite connection string | `sqlite:///krishimitra.db` if unset |
| `SECRET_KEY` | Flask secret | Set in production |
| `JWT_SECRET_KEY` | JWT signing (often same as SECRET_KEY) | Set in production |
| `GROQ_API_KEY` | Groq API key for AI explanations | Optional; app works with template fallbacks |
| `OPENWEATHER_API_KEY` | Weather API | Optional for weather features |
| `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_PROJECT_REF` | Supabase (if used) | Optional |

---

## API Reference

Base URL: `http://localhost:5000` (or your backend host).

### Auth
- `POST /auth/send-otp` — Send OTP to phone.
- `POST /auth/verify-otp` — Verify OTP; returns JWT and farmer/profile info.
- `POST /auth/update-profile` — Update farmer profile (onboarding).
- `POST /auth/register` — Register with password.
- `POST /auth/login` — Login with password.

### Yield
- `POST /yield/simulate` — Run yield simulation; returns advisory and summary. Always returns **200** (uses fallback if ML fails).  
  **Body:** `{ "district", "crop", "season", "soil_type", "irrigation", "area" }` (defaults applied if omitted).  
  **Response:** `{ "status", "advisory", "summary", "coverage_warning", "confidence_adjusted" }`.
- `GET /yield/options?district=Mysuru` — Options for crops, districts, seasons, soil_type, irrigation, area (from ML dataset).
- `POST /yield/predict` — Legacy yield prediction (single prediction).
- `POST /yield/actual` — Submit actual yield (feedback).

### Farmer & Dashboard
- `POST /farmer/register` — Register farmer.
- `POST /auth/update-profile` — Update farmer profile and complete onboarding (creates farm/crops via `setup_farm_from_onboarding`). Use this for post-login onboarding.
- `GET /dashboard` — Dashboard data (JWT required).
- `GET /farmer/<id>` — Get farmer profile.

### Farms & Crops
- `POST /farms` — Create farm.
- `GET /user/<user_id>/farms` — List farms and crops.
- `GET /crops/suggest?state=...&district=...` — Suggested crops for region.
- `POST /farm/analyze-pest` — Pest analysis (image).

### Intelligence
- `POST /dashboard/intelligent` — Full intelligent dashboard payload (weather, mandi, recommendation, yield_advisory, strategy, etc.). Body can include `farm_crop_id` or flat params.
- `GET /dashboard/strategy?state=...&crop=...` — Strategy only.

### Price & Mandi
- `GET /price/forecast?crop=...&mandi=...` — Price forecast.
- `GET /mandi/prices?crop=...&district=...` — Mandi prices.
- `GET /mandi/risk` — Market risk.

### Recommendation
- `POST /api/recommendation` — Sell/hold recommendation.

### Financial, Loan & Weather
- `GET /financial-protection?crop=...&district=...` — Financial protection analysis (health score, risk breakdown, protection gap, recommended schemes).
- `GET /loan-risk?crop=...&district=...&loan_amount=...&interest_rate=...&tenure_months=...` — Loan risk analysis (risk score, repayment ratio, worst-case ratio, EMI, recommendations).
- `GET /weather-risk?district=...` — Weather risk.

### Notifications & Metrics
- `POST /notifications/alert` — Create price alert.
- `GET /notifications/alerts/<farmer_id>` — List alerts.
- `GET /metrics/evaluation` — Evaluation metrics.

---

## Mobile App

- **Framework:** Flutter.
- **Screens:** Welcome → Language → Location → Phone login → Farm setup (crops, soil, irrigation, area) → Home (dashboard).  
  Home has quick actions: **Scan Leaf**, **Yield Estimate**, Price Forecast, Sell/Hold Advice, Mandi Prices.
- **Bottom tabs (in order):** **Home**, **Mandi**, **Protection** (Financial Protection), **Loan** (Loan Risk Assistant), **Profile**.
- **Yield flow:** User selects crop, district, and land (acres); taps “Estimate Harvest”. App calls `POST /yield/simulate` and shows result card + advisory. On failure or empty result, an **indicative fallback** is shown (no error dialog).
- **Options:** Crop and district lists can be loaded from `GET /yield/options` (or equivalent) so UI stays aligned with ML dataset.

---

## ML Pipeline (Yield)

- **Location:** `backend/mysuru_agri_ai/`.
- **Flow:** User inputs → `yield_service.get_yield_advisory()` → `permutation_engine.generate_scenarios()` → `pipeline.predict.batch_predict()` → `ranking_engine.rank_strategies()` → `advisory_engine.build_advisory_report()`.
- **Outputs:** Human-readable advisory, summary (predicted_yield, estimated_total_yield, confidence, risk_level). If no valid historical combinations, the pipeline uses all permutations with a “limited coverage” flag; the API still returns 200 with an advisory (or backend fallback).
- **Fallback:** If the pipeline or request fails, the backend uses `_fallback_yield_advisory(district, crop, area)` to return an indicative estimate so the client never receives a 500 for yield simulation.

---

## Related Documentation

- **Financial Protection:** `README_FINANCIAL_PROTECTION.md`, `backend/FINANCIAL_PROTECTION_CENTER.md`.
- **ML (Mysuru):** `backend/mysuru_agri_ai/README.md` if present.
- **Mobile:** `mobile_app/README.md` if present.

---

## Quick Test: Yield Estimate

```bash
curl -X POST http://localhost:5000/yield/simulate \
  -H "Content-Type: application/json" \
  -d '{"district":"Mysuru","crop":"Rice","season":"Kharif","soil_type":"Black","irrigation":"Canal","area":2.5}'
```

Expected: HTTP 200 with `status`, `advisory`, and `summary` (or fallback indicative payload).
