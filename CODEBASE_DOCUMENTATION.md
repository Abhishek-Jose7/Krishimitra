# KrishiMitra AI — Complete Codebase Documentation

> **Project:** AI-powered decision support for Indian farmers
> **Stack:** Flask (Python) backend · Flutter (Dart) mobile app
> **Database:** SQLite (dev) / PostgreSQL (prod via Docker)

---

## 1. Architecture Overview

The app follows a client-server model:
- **Flutter mobile app** → all UI, local state, offline caching via SharedPreferences
- **Flask backend** → authentication, ML predictions, data processing, REST API
- Communication is JSON over HTTP (port 5000)

The dashboard uses a **strategy-driven UI** — the Intelligence Engine picks which cards, alerts, and ordering to show each farmer based on their region and crop.

---

## 2. Project Structure

```
agri/
├── backend/
│   ├── app.py                           # Flask app factory
│   ├── config.py                        # DB URI + secret key
│   ├── database/
│   │   ├── db.py                        # SQLAlchemy instance
│   │   └── models.py                   # Farmer + YieldPrediction ORM
│   ├── models/
│   │   ├── generate_dummy_models.py    # Creates placeholder .pkl files
│   │   ├── yield_model.pkl             # Dummy yield model
│   │   └── price_forecast_model.pkl    # Dummy price model
│   ├── routes/                          # 8 API route blueprints
│   │   ├── auth_routes.py              # OTP send/verify, profile update
│   │   ├── farmer_routes.py            # Registration, profile, dashboard
│   │   ├── yield_routes.py             # Predict yield, submit actual
│   │   ├── price_routes.py             # 90-day price forecast
│   │   ├── mandi_routes.py             # Mandi prices + market risk
│   │   ├── recommendation_routes.py    # Sell/Hold advice
│   │   ├── weather_routes.py           # Weather data
│   │   └── dashboard_routes.py         # Single-call intelligent dashboard
│   └── services/                        # Business logic layer
│       ├── farmer_service.py
│       ├── yield_service.py
│       ├── price_service.py
│       ├── mandi_service.py
│       ├── recommendation_service.py
│       ├── weather_service.py
│       └── intelligence_engine.py      # Region + Crop strategy brain
├── mobile_app/lib/
│   ├── main.dart                        # Entry point + splash routing
│   ├── theme.dart                       # Colors, typography, design tokens
│   ├── providers/
│   │   └── farmer_profile_provider.dart # Central state (ChangeNotifier)
│   ├── services/
│   │   ├── api_service.dart             # HTTP client for all endpoints
│   │   └── region_crop_strategy.dart    # Offline intelligence mirror
│   ├── screens/
│   │   ├── onboarding/                  # 4-step wizard
│   │   │   ├── language_screen.dart
│   │   │   ├── phone_login_screen.dart
│   │   │   ├── location_screen.dart
│   │   │   └── farm_setup_screen.dart
│   │   ├── home_screen.dart             # Bottom nav (3 tabs)
│   │   ├── dashboard_screen.dart        # Main intelligent dashboard
│   │   ├── mandi_screen.dart            # Market comparison
│   │   ├── price_screen.dart            # 90-day chart
│   │   ├── recommendation_screen.dart   # Sell/Hold detail
│   │   ├── yield_screen.dart            # Harvest prediction
│   │   ├── profit_calculator_screen.dart# Offline cost calculator
│   │   └── profile_screen.dart          # View/edit profile + logout
│   └── widgets/
│       ├── app_button.dart              # Themed primary button
│       ├── app_card.dart                # Themed card container
│       └── custom_card.dart             # Feature action card
├── docker-compose.yml                   # Backend + PostgreSQL
└── README.md
```

---

## 3. Backend — Flask API

### 3.1 App Entry Point (app.py)

**What it does:** Creates and configures the Flask app using the factory pattern.

**Step by step:**
1. Creates Flask instance, loads config
2. Sets JWT secret key (hardcoded placeholder)
3. Initializes Flask-JWT-Extended for token auth
4. Initializes SQLAlchemy and connects to app
5. Enables CORS for Flutter cross-origin calls
6. Registers 8 route blueprints (auth, farmer, yield, price, mandi, recommendation, weather, dashboard)
7. Auto-creates all DB tables on startup via `db.create_all()`
8. Starts server on `0.0.0.0:5000`

### 3.2 Configuration (config.py)

- `SECRET_KEY` — from env var or hardcoded fallback
- `SQLALCHEMY_DATABASE_URI` — checks `DATABASE_URL` env var (for PostgreSQL in Docker), falls back to SQLite (`krishimitra.db`) for zero-setup local dev
- `SQLALCHEMY_TRACK_MODIFICATIONS` — disabled to save resources

### 3.3 Database Models (database/models.py)

**Farmer model** — one row per user:

| Field | Type | Purpose |
|-------|------|---------|
| id | Integer PK | Auto-generated |
| phone | String(15), unique | Login identifier |
| name | String(100) | Farmer's name |
| language | String(10) | Preferred language (default 'en') |
| state, district | String | Location |
| latitude, longitude | Float | GPS coords |
| primary_crop | String | Main crop |
| preferred_mandi | String | Nearest market |
| land_size | Float | Farm size in hectares |
| storage_available | Boolean | Has crop storage |
| soil_type, irrigation_type | String | Farm characteristics |
| onboarding_complete | Boolean | Setup finished flag |
| created_at, updated_at | DateTime | Timestamps |

Has `to_dict()` for JSON serialization and `preferred_crop` alias property.

**YieldPrediction model** — records every prediction:

| Field | Type | Purpose |
|-------|------|---------|
| id | Integer PK | Auto-generated |
| farmer_id | FK → Farmer | Which farmer |
| crop | String | Crop name |
| predicted_yield | Float | ML prediction |
| actual_yield | Float (nullable) | Farmer's real yield (feedback) |
| prediction_date | DateTime | When predicted |

### 3.4 Dummy ML Models (models/)

Since this is a prototype, real ML models haven't been trained. Placeholder models return randomized but plausible data:

- **DummyYieldModel.predict()** — ignores features, returns random yield 10–50 quintals/acre
- **DummyPriceModel.forecast()** — picks random base ₹2,000–5,000, generates 90-day series with slight upward trend (+₹5/day) plus random noise (±₹100)
- `generate_models()` pickles both to `.pkl` files; must run once before starting backend

---

### 3.5 Routes (API Endpoints)

#### 3.5.1 Auth Routes (auth_routes.py)

**POST /auth/send-otp** — Receives phone, validates ≥10 digits, generates random 6-digit OTP, stores in memory dict, returns OTP in response (dev mode; production would use SMS).

**POST /auth/verify-otp** — Checks phone+OTP against store (also accepts `123456` as dev bypass). Clears used OTP. Looks up or creates Farmer record. Generates JWT access token. Returns token, farmer ID, new-user flag, onboarding status, and full profile.

**POST /auth/update-profile** — Takes farmer_id plus any updatable fields (name, language, state, district, crop, land_size, etc.). Updates only fields present in request. Commits and returns updated profile.

#### 3.5.2 Farmer Routes (farmer_routes.py)

**POST /farmer/register** — Delegates to FarmerService. If phone exists, returns token for existing user (acts as login).

**GET /dashboard** (JWT required) — Fetches logged-in farmer's profile, gets price forecast for their crop/mandi, finds most recent yield prediction. Returns combined response: farmer profile + market summary + last prediction.

**GET /farmer/<id>** — Returns farmer profile by ID.

#### 3.5.3 Yield Routes (yield_routes.py)

**POST /yield/predict** — Takes crop, district, land_size, soil_type. Calls YieldService. Returns predicted yield/hectare, total production, confidence, risk level, explanation text.

**POST /yield/actual** (JWT required) — Takes actual production number. Finds most recent prediction, updates `actual_yield` field for future model retraining.

#### 3.5.4 Price Routes (price_routes.py)

**GET /price/forecast?crop=Rice&mandi=Pune** — Calls PriceService. Returns current price, trend, peak price/date, volatility, and full 90-day forecast array.

#### 3.5.5 Mandi Routes (mandi_routes.py)

**GET /mandi/prices?crop=Rice&district=Pune** — Returns list of mandis with today's price, yesterday's price, change, MSP comparison, distance, transport cost, effective price.

**GET /mandi/risk** — Returns market risk signal: LOW/MEDIUM/HIGH with color and message.

#### 3.5.6 Recommendation Routes (recommendation_routes.py)

**POST|GET /recommendation** — Takes crop, district, land_size, mandi, optional costs. Returns sell/hold decision, revenue comparison, risk, explanation, storage advice.

#### 3.5.7 Weather Routes (weather_routes.py)

**GET /weather?district=Pune** — Returns temperature, humidity, rainfall, condition.

#### 3.5.8 Dashboard Routes (dashboard_routes.py) — ⭐ Most Important

**POST /dashboard/intelligent** — THE single-call endpoint that replaces 5+ individual API calls:
1. Receives state, crop, district, land_size, storage_available, mandi
2. Calls IntelligenceEngine → strategy (card ordering, alerts, weights, MSP)
3. Calls WeatherService → current weather
4. Calls MandiService → nearby mandi prices + market risk
5. Calls RecommendationService → sell/hold advice
6. Assembles everything into ONE response
7. If any service fails, it doesn't crash — just omits that section

**GET /dashboard/strategy?state=Kerala&crop=Rice** — Lightweight version returning ONLY strategy without live data. Used for UI layout configuration before data loads.

---

### 3.6 Services (Business Logic)

#### 3.6.1 Farmer Service

- `create_farmer(data)` — Checks if phone exists (returns token if so). Otherwise creates Farmer, generates JWT, returns token + profile.
- `get_farmer(id)` — Simple lookup by ID.
- `update_farmer(id, data)` — Updates whitelisted fields only.

#### 3.6.2 Yield Service

`predict_yield(data)`:
1. Loads pickle model (cached after first load)
2. Fetches live weather for farmer's district
3. Prepares features (crop, district, land, soil, temp, humidity)
4. Runs model.predict() → yield per acre
5. Multiplies by land size → total production
6. Saves prediction to DB if farmer_id provided
7. Calculates fake confidence (0.85 + humidity/1000) and risk level
8. Returns: yield/hectare, total production, confidence, risk, explanation

#### 3.6.3 Price Service

`forecast_price(data)`:
1. Loads pickle model, calls forecast(crop, mandi, 90 days)
2. Determines trend: "Rising" if 90-day > current by 5%, "Falling" if below 5%, else "Stable"
3. Calculates volatility = std_dev / mean
4. Finds peak price and which day it occurs
5. Returns: current price, trend, peak date/price, volatility, 90-day forecast array

#### 3.6.4 Mandi Service

Uses 5 hardcoded mandis (Pune, Nashik, Nagpur, Aurangabad, Solapur).

`get_nearby_prices(crop, district)`:
- For each mandi: simulates today's price with random fluctuation, calculates price change, computes distance (shorter if same district), estimates transport at ₹2/km/quintal
- Calculates **effective price** = market price - transport cost
- **Sorts by effective price** (highest first) so farmer sees best real earning opportunity first
- Includes MSP comparison for each

`get_market_risk()`:
- Random volatility 0–1 → maps to LOW (green) / MEDIUM (yellow) / HIGH (red)

#### 3.6.5 Recommendation Service — ⭐ Core Value

`get_recommendation(data)` — The sell/hold decision engine:

1. Gets yield prediction (calls YieldService), converts to quintals
2. Gets price forecast (calls PriceService), extracts current/peak prices and volatility
3. Calculates `sell_now_revenue` = quintals × current price
4. Calculates `sell_peak_revenue` = quintals × peak price
5. `extra_profit` = peak revenue - now revenue
6. Factors in input costs (seed, fertilizer, labour, irrigation) if provided
7. Calculates wait_days until peak
8. Determines risk: volatility <0.1 → LOW, <0.2 → MEDIUM, ≥0.2 → HIGH
9. **Decision logic** — Default is HOLD. Switch to SELL NOW if:
   - Wait < 5 days (not worth waiting), OR
   - Extra profit < ₹500 (too small), OR
   - Risk is HIGH (too volatile)
10. Generates English explanation text
11. If HOLD: provides crop-specific storage advice (Rice: 60 days/14% moisture, Wheat: 90 days/airtight, Maize: 45 days/dry fully, Soybean: 30 days/cool)

#### 3.6.6 Weather Service

- If `OPENWEATHER_API_KEY` env var set → real OpenWeatherMap API call for "{district}, IN"
- Otherwise → mock data: random temp 25–35°C, humidity 40–80%, rainfall 0–10mm, "Sunny (Simulated)"
- Rainfall is always mocked (real rainfall needs specialized API)

#### 3.6.7 Intelligence Engine — ⭐ The "Brain"

Tailors each farmer's dashboard based on two dimensions:

**Region profiles** (by Indian state):

| State | Focus | Primary Cards | Sync Interval |
|-------|-------|--------------|---------------|
| Kerala | Weather-heavy | Extended weather, flood risk, rainfall alerts | 3 hours |
| Karnataka | Volatility & mandi | Volatility alerts, mandi comparison, price trends | 6 hours |
| Tamil Nadu | MSP & government | MSP comparison, govt procurement, sell/hold | 12 hours |
| Maharashtra | Market intelligence | Price insights, sell/hold, mandi comparison | 4 hours |
| Default | Balanced | Weather, price insights, sell/hold | 8 hours |

Each profile has weights (weather_weight, market_weight, msp_weight on 0–1 scale), region-specific alerts (e.g., Kerala gets flood risk during monsoon months 6–10), and government schemes.

**Crop profiles** (by type):

| Crop | Type | Shelf Life | Forecast Horizon |
|------|------|-----------|-----------------|
| Onion, Sugarcane | Perishable | 3–14 days | Short (7–14 days) |
| Cotton, Groundnut | Semi-perishable | 60–180 days | Medium–Long |
| Rice, Wheat, Maize, Soybean | Grain | 120–365 days | Long (30–90 days) |

Each crop type has specific alerts (perishables get urgency warnings, grains get storage optimization tips).

**MSP data (2024-25)** with state bonuses:
- Rice: ₹2,300 (+200 in TN, +500 in Telangana)
- Wheat: ₹2,275 (+200 in MP, +100 in Punjab)
- Soybean: ₹4,892 (+200 in MP)
- Cotton: ₹7,121 (+200 in Gujarat)
- Onion: No MSP

**`get_intelligence()` logic:**
1. Look up region profile (fallback to default)
2. Look up crop profile
3. Merge card priorities: region primary → crop-specific → region secondary (deduplicated)
4. Generate region alerts (monsoon/flood warnings if applicable month)
5. Generate crop alerts (perishable warnings, storage tips)
6. Calculate MSP context (base + state bonus)
7. Pick faster sync interval between region and crop
8. Return complete package: strategy, cards, weights, alerts, MSP, sync, storage, govt schemes

---

## 4. Mobile App — Flutter

### 4.1 Entry Point (main.dart)

1. Sets up `MultiProvider` with `ApiService` (singleton) and `FarmerProfile` (ChangeNotifier)
2. Applies AppTheme.lightTheme
3. Shows `SplashRouter`:
   - Loads profile from SharedPreferences
   - Shows branded splash (green bg, plant icon, "KrishiMitra", spinner)
   - If `onboardingComplete` → HomeScreen; else → LanguageScreen

### 4.2 Theme (theme.dart)

- **Colors:** Primary Deep Forest Green (#1B5E20), neutral grey-white background (#F5F5F5), accents: blue, orange, purple, teal
- **Typography:** Poppins (headings, bold 22–28px), Inter (body, 14–16px)
- **Design tokens:** 4px radii for cards/buttons/inputs (sharp/clean look)
- Includes `inputDecoration()` factory and full `ThemeData` config

### 4.3 State Management (farmer_profile_provider.dart)

`FarmerProfile` (ChangeNotifier) — single source of truth for the entire app.

**Stored data:** JWT token, farmer ID, phone, language, state, district, GPS coords, mandi, primary crop, crop list, land size, storage, soil type, irrigation type, cached API responses (forecast, mandi prices, yield prediction), last sync timestamp, onboarding flag.

**Key behaviors:**
- `loadFromLocal()` — reads all from SharedPreferences at startup
- `saveToLocal()` — persists after every update
- Setter methods: `setLanguage()`, `setAuth()`, `setLocation()`, `setFarmProfile()`, `completeOnboarding()`
- `cacheData()` — stores serialized API responses for offline use
- Computed: `displayName` (Farmer XXXX from phone), `displayCrops` (comma list), `expectedYield` (national averages: Rice 4.7, Wheat 3.5, Maize 3.0, Soybean 1.2 t/ha)
- `clearAll()` — full logout, clears SharedPreferences

### 4.4 API Client (api_service.dart)

Base URL: `http://localhost:5000` (web) or `http://10.0.2.2:5000` (Android emulator).

Methods: `predictYield`, `forecastPrice`, `getRecommendation`, `getMandiPrices`, `getMarketRisk`, `getWeather`, `registerFarmer`, `getProfile`, `submitActualYield`, `postIntelligentDashboard`.

### 4.5 Region/Crop Strategy (region_crop_strategy.dart)

Frontend mirror of backend Intelligence Engine for **offline use**.

Key classes:
- `DashboardCardConfig` — id, title, subtitle, icon, color, emphasis level
- `IntelligenceAlert` — type, severity (critical/high/medium/info), icon, title, message, action; computed severityColor/bgColor
- `MspContext` — base MSP, state bonus, effective MSP, crop name
- `RegionCropStrategy` — Two constructors:
  - `fromJson()` — parses backend response
  - `fromLocal(state, crop, storage)` — builds strategy without API (offline)

Public helpers: `showExtendedWeather` (if weather_weight ≥ 0.7), `showMspCard` (if MSP weight ≥ 0.5), `showMandiCompareProminent`, `showVolatilityAlert`, `forecastLabel` ("7-day"/"30-day"/"90-day"), `adviceLabel` ("Act Now"/"Recommendation"/"Long-term Plan").

### 4.6 Onboarding (4-step wizard)

**Step 1 — Language Screen:** 10 Indian languages (English, Hindi, Marathi, Tamil, Telugu, etc.) with native script names. Saves preference, navigates to phone login.

**Step 2 — Phone Login:** 10-digit phone input → calls POST /auth/send-otp → shows OTP field → calls POST /auth/verify-otp → stores JWT/farmerId/phone → navigates to location.

**Step 3 — Location Screen:** Attempts GPS auto-detection via Geolocator, reverse-geocodes to state/district. Falls back to manual dropdown (hardcoded Indian states + districts). Auto-assigns nearest mandi. Saves to profile.

**Step 4 — Farm Setup:** Multi-crop selection grid (Rice, Wheat, Maize, Soybean, Cotton, Onion, Sugarcane, Groundnut + custom "Other"). Per-crop area allocation. Acres/hectares toggle with real-time conversion. **Auto-inferred storage** — if any perishable crop selected, storage is automatically marked needed. Soil type dropdown (Alluvial/Black/Red/Laterite/Sandy). Irrigation dropdown (Rainfed/Canal/Borewell/Drip/Sprinkler). On submit: saves locally, syncs to backend, marks onboarding complete, navigates to HomeScreen.

### 4.7 Main App Screens

#### Home Screen
Bottom nav with 3 tabs: Dashboard, Mandi, Profile. Uses `IndexedStack` (keeps all screens alive).

#### Dashboard Screen (~743 lines) — ⭐ Main Screen

**On load:**
1. Reads profile from Provider
2. Builds offline strategy via `RegionCropStrategy.fromLocal()`
3. Tries `POST /dashboard/intelligent` with farmer data
4. If API succeeds: parses strategy, weather, mandi, risk, recommendation; caches locally
5. If API fails: uses offline strategy + cached data

**Layout (top to bottom):**
1. **Crop Switcher** — dropdown if multi-crop; switching reloads entire dashboard for that crop
2. **Recommendation Hero** — gradient card (green=SELL, orange=HOLD) showing: "SELL TODAY" or "WAIT ~X days", expected extra profit, risk emoji, explanation, confidence statement
3. **Greeting + Weather** — green card with "Namaste, Farmer XXXX 🙏", temp, humidity, rainfall, condition; flood warning icon if rainfall > 30mm and weather-heavy region
4. **Intelligence Alerts** — colored cards from strategy engine with severity-based styling
5. **Price Insight Card** — nearest mandi's today/yesterday price, change arrow, MSP comparison with judgment phrase ("Good selling zone" / "Marginal" / "Hold if possible")
6. **MSP Card** — base MSP + state bonus = effective MSP, ABOVE/BELOW MSP badge
7. **Market Risk Banner** — green/yellow/red strip with stability message
8. **Price Alert Button** — "Alert me if {crop} > ₹{target}/Q" (5% above current)
9. **Quick Actions** — 2×2 grid of strategy-ordered tiles (Price Forecast, Mandi Prices, Sell/Hold, Yield Estimate)
10. **Profit Calculator** — link tile to ProfitCalculatorScreen
11. **Last Updated** timestamp

#### Mandi Screen
- Horizontal crop selector chips at top
- List of mandis sorted by effective price (highest first)
- Each card shows: mandi name, "BEST" badge on #1, distance + travel time (30km/hr rural road estimate) + transport cost tags, NET price (large, primary) and market price (smaller, secondary), price change arrow, per-mandi risk indicator (based on price change severity)
- Pull-to-refresh

#### Price Screen
- Crop + Mandi dropdowns (auto-refreshes on change)
- **Price Summary Card** — today's price in large font, trend badge (Rising/Falling/Stable with arrow icon)
- **Peak Card** — expected peak price and date
- **90-Day Chart** — `fl_chart` LineChart with labeled x-axis (Today, 1 Mo, 2 Mo, 3 Mo), green line with subtle fill, auto-scaled y-axis
- **Volatility Info** — emoji + "Market Stability: Stable/Moderate/Volatile" with advice text

#### Recommendation Screen
- Input: crop dropdown, land size, mandi dropdown
- Optional expandable cost inputs (seed, fertilizer, labour, irrigation)
- "Get Selling Advice" button
- **Result card:**
  - Hero banner (green SELL NOW or orange HOLD & WAIT with icon)
  - Explanation text + risk level
  - Revenue Comparison: "Sell Today ₹X" vs "Wait ~N days ₹Y" side by side
  - Extra Profit if holding (green highlight)
  - After-costs section (if costs provided): total input cost, profit-if-sell-now, profit-if-hold
  - Storage Tips (if HOLD): method, safe days, quality risk, warning if wait exceeds safe storage
  - Risk banner with emoji and message

#### Yield Screen
- Form: crop dropdown, district dropdown, land size input
- "Estimate Harvest" button
- **Result:** total production in tons (large), yield/acre, estimated revenue at current market price, risk/reliability mini-cards, weather-based explanation

#### Profit Calculator Screen (Offline)
- No API calls — pure local calculation
- Inputs: expected yield (quintals), selling price (₹/Q), costs (seed, fertilizer, labour, irrigation, transport, other)
- Revenue = yield × price, Cost = sum of all, Profit = revenue - cost
- Color-coded (green if profitable, red if loss), profit margin percentage
- Visual cost breakdown bars showing each cost as percentage of total

#### Profile Screen
- **Summary card** — gradient green header with avatar, name, phone, crops/district/land
- **Read-only info tiles** — crops, district, mandi, land size (hectares + acres), storage, state, language, soil, irrigation
- **Edit mode** — dropdowns for crop/district/mandi, land size input, storage toggle; saves locally + syncs to backend
- **Post-harvest feedback** — expandable section to submit actual yield (calls /yield/actual) for model improvement
- **Logout** — confirmation dialog, clears SharedPreferences, navigates to LanguageScreen

### 4.8 Widgets

- **AppButton** — green elevated button, optional icon, loading spinner state, 52px height
- **AppCard** — white container, grey border, 4px radius, optional tap, configurable padding/color
- **CustomCard** — icon in colored circle + title + subtitle, for dashboard action tiles

---

## 5. DevOps

**docker-compose.yml** — two services:
- `backend`: builds from ./backend/Dockerfile, port 5000, uses PostgreSQL URL
- `db`: PostgreSQL 15, user/password/krishimitra, persistent volume

**dependencies:**
- Python: Flask, Flask-CORS, Flask-JWT-Extended, Flask-SQLAlchemy, numpy, requests, psycopg2-binary
- Flutter: http, provider, fl_chart, google_fonts, intl, shared_preferences, geolocator, geocoding

---

## 6. Key Design Decisions

1. **Offline-first** — `RegionCropStrategy.fromLocal()` builds complete dashboard strategy without API. SharedPreferences caches data.

2. **Single dashboard endpoint** — `/dashboard/intelligent` bundles weather + mandi + risk + recommendation in one call, reducing latency.

3. **Strategy-driven UI** — Dashboard layout is NOT fixed. Intelligence Engine determines card ordering and emphasis per farmer. Kerala rice farmer sees weather-dominant; Maharashtra onion farmer sees volatility-focused.

4. **Effective price ranking** — Mandis sorted by price AFTER transport costs, showing actual best option.

5. **Auto-inferred storage** — Instead of asking "Do you have storage?", the app infers need from crop perishability (Onion/Sugarcane = needs storage urgently).

6. **Phone-based auth** — OTP simulated for dev (returned in response body). Production would use SMS gateway.

7. **SQLite fallback** — Zero-setup local dev without PostgreSQL.

8. **Dummy ML models** — Placeholders that can be swapped with real trained models (same pickle interface).

9. **MSP with state bonuses** — Accounts for state-level additions on top of central MSP.

10. **Multi-crop support** — Per-crop area allocation during onboarding; dashboard crop switcher.

---

## 7. Current Limitations

- ML models are **dummy** — return random data. Real models need training.
- Weather API rainfall is always mocked.
- OTP is **simulated** — needs SMS gateway for production.
- Mandi data is **hardcoded** (5 Maharashtra mandis) — needs real data source.
- Price alert button shows snackbar only — no actual notification system.
- No unit/integration tests exist.
- The farmer expectedYield calculation on frontend uses simplified national averages, not the backend prediction.
