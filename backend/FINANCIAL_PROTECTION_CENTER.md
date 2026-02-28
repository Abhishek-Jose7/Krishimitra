# Farm Financial Protection Center (KrishiMitra)

This document explains **the complete working** of the **Farm Financial Protection Center** feature (backend + Flutter UI), including every computation step performed by the new financial protection module.

> Non‑negotiable design: This module is **fully isolated**. It **does not modify** existing recommendation logic, weather logic, API response formats for other endpoints, folder structure, or existing services. It only **consumes** existing service outputs and builds a new analysis on top.

---

## What this feature is

The **Farm Financial Protection Center** is an advisory engine that converts existing farm signals (weather risk, market forecast, yield prediction confidence, landholding context) into:

- a **Financial Health Score** (0–100, higher is better)
- a **Risk Exposure** level (`LOW`, `MODERATE`, `HIGH`)
- a **risk breakdown** across Weather / Market / Yield
- a **Protection Gap** explanation (“what is missing or risky right now”)
- **Recommended Protection Actions** (not a generic scheme list—rules are contextual)

---

## Where the code lives

### Backend

- **Service (core logic)**: `backend/services/financial_advisor_service.py`
- **Route (endpoint composition)**: `backend/routes/financial_routes.py`
- **Wiring (blueprint registration)**: `backend/app.py`

### Flutter (UI + API call)

- **New screen**: `mobile_app/lib/screens/financial_protection_screen.dart`
- **New API method**: `mobile_app/lib/services/api_service.dart` → `getFinancialProtection(...)`
- **Navigation**: `mobile_app/lib/screens/home_screen.dart` adds a new bottom tab “Protection”

---

## Backend: Endpoint behavior

### Endpoint

`GET /financial-protection?crop=Rice&district=Kochi`

Optional query:
- `mandi=...` (used for price forecast, if present)

### What the endpoint does (in order)

Implemented in `backend/routes/financial_routes.py`:

1) **Read query params**
- `crop` defaults to `"Rice"`
- `district` is required (returns `400` if missing)

2) **Fetch farmer context (best-effort)**
- If a JWT identity is present, it loads:
  - farmer profile: `FarmerService.get_farmer(user_id)` → dictionary
  - farms list: `FarmerService.get_user_farms(user_id)` → used to estimate landholding
  - default crop: `FarmerService.get_default_crop(user_id)` → used to infer `mandi` if possible
- If user is not authenticated, this step is skipped safely and the endpoint still works.

3) **Compute landholding (for scheme rules)**
- The route sums `total_land_hectares` across the user’s farms.
- If landholding can’t be computed (no farms, no auth), it uses a safe default (`2.0` hectares) so the module is still usable.
- It sets these keys into `farmer_profile` for the service:
  - `landholding_hectares`
  - `landholding_acres = hectares * 2.47105`

4) **Fetch Weather Risk (existing logic, unchanged)**
- `WeatherService.calculate_weather_risk(district)`
- Returns a dict like:

```json
{
  "rain_risk": "LOW|MODERATE|HIGH",
  "heat_risk": "LOW|MODERATE|HIGH",
  "humidity_risk": "LOW|MODERATE|HIGH"
}
```

5) **Fetch Yield Prediction (existing logic, unchanged)**
- Calls existing yield prediction service:
  - `YieldService.predict_yield({ district, crop, land_size })`
- This returns a dict containing (depending on existing pipeline):
  - `confidence` (0–100) **OR** sometimes `confidence_adjusted`
  - plus other yield fields

6) **Fetch Price Forecast (existing logic, unchanged)**
- Calls:
  - `PriceService.forecast_price({ crop, mandi, state })`
- Typically contains:
  - `trend` (`"Rising"|"Falling"|"Stable"`)
  - `volatility` (relative standard deviation)
  - `forecast` list: `[{date, price}, ...]`

7) **Run financial advisory analysis**
- Calls:
  - `FinancialAdvisorService.analyze(...)`

8) **Return JSON**
- The response is exactly the new module’s output.
- No existing endpoints are changed.

---

## Backend: Output JSON contract

The module returns:

```json
{
  "financial_health_score": 64,
  "risk_level": "HIGH",
  "risk_breakdown": {
    "weather_risk_score": 80,
    "market_risk_score": 60,
    "yield_risk_score": 45
  },
  "protection_gap": "High rainfall exposure and no active insurance detected.",
  "recommended_protection_actions": [
    {
      "type": "Insurance",
      "scheme_name": "PMFBY",
      "urgency": "HIGH",
      "reason": "High rainfall risk",
      "apply_link": "https://pmfby.gov.in"
    }
  ]
}
```

Notes:
- `financial_health_score` is **health** (higher is better).
- `risk_breakdown` are **risk scores** (higher is worse).

---

## Backend: Core logic (FinancialAdvisorService)

All logic below is implemented in `backend/services/financial_advisor_service.py`.

### 1) Weather risk scoring

The service consumes the existing weather risk object/dict and derives an **overall weather severity** using the worst of:
- `rain_risk`
- `heat_risk`
- `humidity_risk`

Severity → score mapping (as required):
- `HIGH` → `80`
- `MODERATE` → `60`
- `LOW` (or unknown) → `30`

How “overall” is selected:
- If any component is `HIGH` → overall `HIGH`
- Else if any component is `MODERATE` → overall `MODERATE`
- Else → `LOW`

Also builds a **human reason string**, e.g.:
- `"high rainfall exposure"` when `rain_risk == HIGH`
- `"heat stress risk"` when `heat_risk == HIGH`
- `"high humidity risk"` when `humidity_risk == HIGH`

### 2) Market risk scoring

Goal: reflect market uncertainty using whatever price forecast signals are available.

Inputs consumed:
- `price_forecast_data.volatility` if present
- else variance computed from `price_forecast_data.forecast[*].price`
- plus `price_forecast_data.trend` as a mild adjustment

Rules:

**A) If forecast missing**
- Returns simulated market risk:
  - score `55`
  - trend `"UNKNOWN"`

**B) If `volatility` available**
- Converts volatility to a 0–100-ish score:
  - `market_score = clamp(volatility * 250)`
  - (example: volatility 0.20 → score 50)

**C) If volatility missing but forecast list exists**
- Computes relative volatility:
  - \(rel = std(prices) / mean(prices)\)
  - `market_score = clamp(rel * 250)`

**D) Trend adjustment**
- If `trend == "Falling"` → **+10** risk points (more urgency)
- If `trend == "Rising"` → **-5** risk points (slightly less risk)
- Otherwise no change.

### 3) Yield risk scoring (confidence-based)

The service uses confidence as a proxy for yield uncertainty.

Inputs consumed:
- `yield_prediction_data.confidence` (preferred)
- or `yield_prediction_data.confidence_adjusted` (fallback)

Rule:
- `yield_risk_score = clamp(100 - confidence)`

If yield prediction is missing or confidence not present:
- simulated yield risk:
  - score `50`

### 4) Final financial risk score and risk level

The engine computes:

- `financial_risk_score = (weather + market + yield) / 3`

Then it converts that into a **risk level**:
- `> 70` → `HIGH`
- `40–70` → `MODERATE`
- `< 40` → `LOW`

### 5) Financial Health Score (shown to user)

The API returns a **health score** for UX clarity:

- `financial_health_score = 100 - financial_risk_score` (clamped to 0–100)

This means:
- higher health score → stronger financial resilience
- higher risk breakdown scores → more exposure in that domain

---

## Backend: Protection gap analysis

`protection_gap` is a **human-readable explanation** of what is risky and what coverage appears missing.

Inputs it uses:
- `weather_level` (derived in scoring)
- `market_trend`
- “insurance active” flags in `farmer_profile` (best-effort detection)
- plus a short evidence tail (weather reason + market reason + yield reason)

Insurance detection:
- Looks for any of these in `farmer_profile`:
  - `has_insurance`, `insurance_active`, `pmfby_active`, `active_insurance`
- Supports boolean or `"yes"/"true"/"1"` strings.

Generated examples:
- If weather is HIGH and insurance not detected:
  - “High weather exposure and no active insurance detected.”
- If market trend is Falling:
  - “Prices are trending down; income protection and MSP options become important.”
- Always appends a short evidence tail when available:
  - “Evidence: high rainfall exposure; forecast volatility 0.20; yield confidence 55.0%.”

---

## Backend: Context-aware scheme/action engine

This is intentionally **rule-based**, contextual, and **non-destructive**.
It returns a list of actions under `recommended_protection_actions`.

Each action is a dict:
- `type`: category (Insurance / Income Support / MSP Procurement / Price Strategy)
- `scheme_name`: e.g., `PMFBY`, `PM-KISAN`, `MSP`, `Delayed Selling`
- `urgency`: `LOW|MEDIUM|HIGH`
- `reason`: contextual explanation
- `apply_link`: official or info link

### Rule 1 — Weather risk HIGH → PMFBY

If `weather_level == HIGH`:
- recommend:
  - type: `Insurance`
  - scheme: `PMFBY`
  - urgency: `HIGH`
  - apply_link: `https://pmfby.gov.in`

### Rule 2 — Landholding <= 2 acres → PM‑KISAN

If landholding is known and `<= 2.0 acres`:
- recommend:
  - type: `Income Support`
  - scheme: `PM-KISAN`
  - urgency: `MEDIUM`
  - apply_link: `https://pmkisan.gov.in`

Landholding extraction order:
- `farmer_profile.landholding_acres`
- else `farmer_profile.landholding_hectares * 2.47105`

### Rule 3 — Crop covered under MSP → MSP procurement

If crop is in an internal MSP coverage set (e.g., Rice, Wheat, Maize, Pulses, etc.):
- recommend:
  - type: `MSP Procurement`
  - scheme_name: `MSP`
  - urgency: `HIGH` if market is falling, else `MEDIUM`
  - apply_link: `https://dfpd.gov.in/Price-Support.htm`

### Rule 4 — Price forecast decreasing → delayed selling / MSP

If:
- `trend == "Falling"` OR
- forecast indicates decreasing prices (last < first * 0.98) when enough points exist

Then recommend:
- type: `Price Strategy`
- scheme_name: `Delayed Selling`
- urgency: `HIGH` if crop is MSP-covered else `MEDIUM`
- apply_link: MSP info link (informational)

### De-duplication

To avoid spam, actions are deduped by `(type, scheme_name)`.

---

## Flutter: How the UI uses the endpoint

### Navigation

`mobile_app/lib/screens/home_screen.dart` adds a new bottom tab:
- Label: **Protection**
- Screen: `FinancialProtectionScreen`

This does not change or restructure existing screens.

### API call

`ApiService.getFinancialProtection(...)` calls:

- `GET {baseUrl}/financial-protection?crop={crop}&district={district}&mandi={mandi?}`

Where the inputs come from:
- `crop`: `FarmerProfile.activeCrop.cropName` (fallback `"Rice"`)
- `district`: `FarmerProfile.district` (fallback `"Pune"`)
- `mandi`: `FarmerProfile.activeMandiName` (optional)

### UI components and what they render

Implemented in `mobile_app/lib/screens/financial_protection_screen.dart`.

1) **Financial Health Score gauge**
- reads:
  - `financial_health_score`
  - `risk_level`
- renders:
  - circular gauge 0–100
  - risk label chip (Low/Moderate/High)

2) **Risk Breakdown Cards**
- reads:
  - `risk_breakdown.weather_risk_score`
  - `risk_breakdown.market_risk_score`
  - `risk_breakdown.yield_risk_score`
- each card displays:
  - numeric score
  - progress bar
  - derived severity label based on score thresholds:
    - >=70 HIGH, >=40 MODERATE, else LOW

3) **Protection Gap Banner**
- reads:
  - `protection_gap`
  - `risk_level` (drives styling color)

4) **Scheme / Action cards**
- reads:
  - `recommended_protection_actions[]`
- each card renders:
  - `type`, `scheme_name`, `urgency`, `reason`
  - “Apply Now” button if `apply_link` present

5) **Apply Now behavior**
- Uses `url_launcher` to open `apply_link` in an external browser.

---

## Testing / usage quickstart

### Backend

Start Flask (from `backend/`):

```bash
pip install -r requirements.txt
python app.py
```

Call:

```bash
curl "http://localhost:5000/financial-protection?crop=Rice&district=Kochi"
```

### Flutter

```bash
cd mobile_app
flutter pub get
flutter run
```

Then open the bottom tab: **Protection**.

---

## Important implementation notes (stability & isolation)

- The new module:
  - does **not** touch database schema
  - does **not** change response shapes of existing endpoints
  - does **not** alter existing logic in `RecommendationService`, `WeatherService`, `PriceService`, `YieldService`
- It only:
  - adds a new service file
  - adds a new route file
  - registers the new blueprint
  - adds a new Flutter tab + screen + API method

---

## Extending the module safely (future)

You can enhance this module without breaking anything by only adding **optional** fields to the financial protection response, for example:
- `confidence_notes`
- `recommended_next_review_date`
- `risk_trend` (delta from last run)
- user-specific insurance status (if you later store insurance metadata)

Keep all new logic confined to:
- `backend/services/financial_advisor_service.py`
- and (if needed) additional files under `backend/services/` + `backend/routes/`

