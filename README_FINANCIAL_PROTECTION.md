# Financial Protection Feature — Full Technical Overview

This document describes the "Financial Protection" feature implemented in the codebase (service: `FinancialAdvisorService`) and the HTTP route that exposes it (`/financial-protection`). It explains the end-to-end logic, the inputs and outputs, algorithms used to compute risk scores, the scheme engine that recommends protection actions, helper utilities, how the endpoint is invoked, and important edge cases and assumptions. This is written to be a precise, word-for-word description of how the feature works in the current repository.

## High-level purpose

The Financial Protection feature evaluates the financial risk a farmer faces across three domains: weather, market (price), and yield. It synthesizes those risks into a single financial health score, a risk level, a human-readable protection gap message, and a set of recommended protective actions (schemes, insurance, price strategies). The engine is intentionally standalone: it consumes outputs from existing weather, price and yield services and does not change them.

Where to find the code

- Primary implementation: `backend/services/financial_advisor_service.py` (class `FinancialAdvisorService`).
- HTTP route: `backend/routes/financial_routes.py` (route: `GET /financial-protection`).
- The intelligence engine contains region-specific references to schemes and labels: `backend/services/intelligence_engine.py`.

## Contract (function-level)

FinancialAdvisorService.analyze(...)

- Inputs (named parameters):
  - `farmer_profile: Dict[str, Any]` — optional farmer profile object; used to detect land size, existing insurance and district/state defaults.
  - `crop: str` — crop name (e.g., "Rice").
  - `district: str` — district name used for region-specific calculations and to fetch weather risk.
  - `weather_risk: Dict[str, Any] | Any` — a weather risk object produced by WeatherService (or similar). The analyzer reads `rain_risk`, `heat_risk`, and `humidity_risk` keys/attributes.
  - `price_forecast_data: Optional[Dict[str, Any]]` — price forecast structure provided by PriceService; expected keys include `volatility`, `trend`, and optionally `forecast` (list of dicts with `price`).
  - `yield_prediction_data: Optional[Dict[str, Any]]` — yield prediction output from YieldService; expected keys include `confidence` (percentage-like) or `confidence_adjusted`.

- Outputs (returned `Dict[str, Any]`):
  - `financial_health_score: int` — 0–100 score where higher is healthier. Computed as 100 - average_risk (rounded and clamped).
  - `risk_level: str` — one of `HIGH`, `MODERATE`, `LOW`, derived from numeric risk.
  - `risk_breakdown: {weather_risk_score, market_risk_score, yield_risk_score}` — per-domain scores (integers 0–100).
  - `protection_gap: str` — human-readable summary explaining protection gaps and evidence.
  - `recommended_protection_actions: List[dict]` — list of recommended actions; each action has `type`, `scheme_name`, `urgency`, `reason`, and `apply_link`.

Success criteria / error modes

- The analyzer tolerantly handles missing inputs. If forecasts are unavailable it supplies simulated fallback scores.
- The analyzer never throws for missing optional inputs; it returns reasonable defaults and explanatory text in `protection_gap` or reasons.

## Internal helper utilities and their behaviour

- `_clamp(val, lo=0.0, hi=100.0)` — clamps a float into the [lo, hi] range.
- `_risk_label_from_score(score)` — maps numeric score to label:
  - score > 70 → `HIGH`
  - 40 <= score <= 70 → `MODERATE`
  - else → `LOW`
- `_severity_to_score(level)` — maps severity strings to numeric risk scores: `HIGH`→80, `MODERATE`→60, other/None→30.
- `_max_severity(*levels)` — returns the maximum severity among inputs `LOW` < `MODERATE` < `HIGH` based on a simple ordering.
- `_safe_float(v, default=None)` — robustly converts a value to `float`, returns default on failure.

These helpers enforce consistent numeric ranges and normalization across the engine.

## Scoring logic (detailed)

All three domain scores are integers in the 0–100 range and combine (arithmetic mean) to compute a single financial risk value. The health score is computed as 100 - average_risk and clamped to [0,100].

1) Weather scoring — `FinancialAdvisorService._compute_weather_score(weather_risk)`

- Input expectations: a dict-like `weather_risk` with keys `rain_risk`, `heat_risk`, `humidity_risk` (values are severity strings: `LOW`, `MODERATE`, `HIGH`, or similar). The method also accepts objects with attributes of the same names.
- Steps:
  - Extract `rain`, `heat`, and `humidity` from the input.
  - Determine an overall severity via `_max_severity(rain, heat, humidity)`.
  - Map that overall severity to a numeric score using `_severity_to_score(overall)`.
  - Build a human-readable `reason` string listing which categories are `HIGH` (e.g., "high rainfall exposure, heat stress risk"). If none are high, reason is "no major weather red flags detected".
  - Return `(score, overall, reason)` where `score` is an `int` representing weather risk.

Rationale: Weather domain uses the maximum severity among rain/heat/humidity — a single severe factor dominates the weather risk.

2) Market (price) scoring — `FinancialAdvisorService._compute_market_score(price_forecast_data)`

- Input expectations: `price_forecast_data` is optional. When present, it may contain:
  - `volatility` (numeric), e.g., a model-produced volatility like 0.05–0.30.
  - `trend` (string) — expected values include `rising`, `falling`, or other labels.
  - `forecast` — optional list of dicts like `{ "price": 123.4 }` used to infer variance if volatility missing.
- Steps:
  - If `price_forecast_data` is empty/None → return fallback `(55, "UNKNOWN", "price forecast unavailable (simulated market risk)")`.
  - If `volatility` is present, map it to a 0–100 risk by scaling: `market_score = clamp(round(volatility * 250.0))`. (Example: volatility=0.4 → 100). Also set a reason string containing the volatility value.
  - If `volatility` missing but `forecast` list exists, extract numeric prices and compute relative volatility `rel = std/mean`. Map `rel` the same way: `clamp(round(rel * 250.0))` and reason = "forecast variance indicates volatility".
  - If neither volatility nor enough forecast entries are available (fewer than 5 valid prices), fallback to `market_score = 55` and a reason string indicating limited info.
  - Trend adjustment (non-destructive):
    - If `trend.lower() == 'falling'` → add +10 to `market_score` (more risk).
    - If `trend.lower() == 'rising'` → subtract 5 from `market_score` (less risk).
  - Normalize `trend` to an uppercase or `UNKNOWN` string and return `(market_score, trend_norm, reason)`.

Rationale: The market risk is driven by model volatility where higher volatility = higher risk. If volatility isn't available, the engine infers volatility from forecast variance. Trend nudges the numeric score slightly.

3) Yield scoring — `FinancialAdvisorService._compute_yield_score(yield_prediction_data)`

- Input expectations: `yield_prediction_data` may contain `confidence` (percentage-like float) or `confidence_adjusted`.
- Steps:
  - If the data is missing → return fallback `(50, "yield prediction unavailable (simulated yield risk)")`.
  - Read `confidence` (try `confidence`, then `confidence_adjusted`). If still missing → fallback `(50, "yield confidence unavailable (simulated yield risk)")`.
  - Compute `score = clamp(round(100.0 - confidence))`. (Lower model confidence → higher risk score.)
  - Return `(score, f"yield confidence {confidence:.1f}%")`.

Rationale: Yield risk is driven by the inverse of the model's confidence: if the yield model is uncertain, the financial risk rises.

Combination into final outputs

- The numeric `financial_risk_score` is computed as the simple arithmetic mean of the three domain scores: `(weather + market + yield) / 3.0`.
- `financial_health_score` = `int(round(clamp(100.0 - financial_risk_score)))`.
- `risk_level` = `_risk_label_from_score(financial_risk_score)`.

## Protection gap builder

Method: `FinancialAdvisorService._build_protection_gap(...)`

- Purpose: Produce a short human-readable summary of protection gaps and evidence drawn from computed domain levels and farmer attributes.
- Inputs: `farmer_profile`, `weather_level`, `market_trend`, `weather_reason`, `market_reason`, `yield_reason`.
- Behaviour:
  - Detect if insurance is active using `_detect_insurance_active(farmer_profile)` (checks keys like `has_insurance`, `insurance_active`, `pmfby_active`, `active_insurance` — accepts booleans or strings like "yes"/"true").
  - Compose parts:
    - If weather_level == `HIGH` and insurance not active → "High weather exposure and no active insurance detected.".
    - Else if weather_level == `HIGH` and insurance is active → "High weather exposure detected; insurance coverage looks present.".
    - If market_trend is `FALLING` → add: "Prices are trending down; income protection and MSP options become important.".
    - If no parts were added → default to: "No major protection gaps detected, but keep coverage active and review market risks weekly.".
  - Append an evidence tail joining `weather_reason`, `market_reason`, and `yield_reason` (if present) as a single sentence fragment.
  - Return the combined string.

## Scheme engine (recommendation rules)

Method: `FinancialAdvisorService._scheme_engine(...)`

- Purpose: Build a de-duplicated list of `ProtectionAction` recommendations based on weather_level, farmer profile, crop, district, and price forecast.
- Returns: `List[ProtectionAction]` — each is a dataclass with fields `type`, `scheme_name`, `urgency`, `reason`, `apply_link`.

Rules encoded (in order):

1. If `weather_level == 'HIGH'` → recommend `PMFBY` insurance (type="Insurance", urgency="HIGH", apply_link points to `PMFBY_LINK`).

2. If detected landholding in acres is <= 2.0 → recommend `PM-KISAN` income support (type="Income Support", urgency="MEDIUM", apply_link `PM_KISAN_LINK`).
   - Land detection logic: `_detect_landholding_acres(farmer_profile)` tries `landholding_acres` first; if missing it looks for `landholding_hectares` and multiplies by 2.47105 to convert to acres.

3. If the crop is in the hard-coded `MSP_CROPS` set (upper-cased), recommend an MSP procurement suggestion (type="MSP Procurement", scheme_name="MSP"). Urgency is `MEDIUM` unless market trend is `FALLING`, then `HIGH`.

4. If `market_trend == 'FALLING'` or `_forecast_is_decreasing(price_forecast_data)` returns `True`, recommend a `Price Strategy` with scheme_name `Delayed Selling` and urgency `HIGH` for MSP crops, else `MEDIUM`.

- De-duplication: the code removes duplicate recommendations by `(type, scheme_name)`.

Helper: `_forecast_is_decreasing(price_forecast_data)`

- Behaviour: If `price_forecast_data` has a `forecast` list of dicts with `price`, it extracts numeric prices to a list. If there are fewer than 7 prices it returns `False`. Otherwise it returns `True` if the last price is less than 98% of the first price (i.e., `prices[-1] < prices[0] * 0.98`).

## Links and constants

- `PMFBY_LINK` — `https://pmfby.gov.in` (Pradhan Mantri Fasal Bima Yojana).
- `PM_KISAN_LINK` — `https://pmkisan.gov.in` (PM-KISAN scheme).
- `MSP_INFO_LINK` — `https://dfpd.gov.in/Price-Support.htm` (MSP/procurement information).
- `MSP_CROPS` — a set of crop names considered typically procured under MSP. The code normalizes crop input to upper case to check membership.

## HTTP route and integration

Route: `GET /financial-protection` in `backend/routes/financial_routes.py`.

Behavior and flow of the endpoint (word-for-word from how the route invokes the service):

1. Read `crop` and `district` query parameters. `district` is required; missing `district` results in a 400 response with `{ "error": "district parameter required" }`.
2. Attempt to get the current user id from `get_jwt_identity()` (optional authentication). If present, fetch farmer profile via `FarmerService.get_farmer(current_user_id)` and farms via `FarmerService.get_user_farms(current_user_id)`.
3. Sum user farm hectares with helper `_sum_land_hectares(farms_payload)` and prefer any `default_crop` from `FarmerService` to set the `mandi` and `crop` if those query params are missing.
4. If land hectares unknown, default `land_hectares` to `2.0` (so endpoint is usable without auth). The route then ensures `farmer_profile` contains `district`, `landholding_hectares`, and `landholding_acres`.
5. Determine `mandi` from the request params or default to `Pune`.
6. Fetch external inputs used by the analyzer:
   - `weather_risk = WeatherService.calculate_weather_risk(district)`
   - `yield_prediction_data = YieldService.predict_yield({"district": district, "crop": crop, "land_size": land_hectares})` (wrapped in a try/except; falls back to `None` on error)
   - `price_forecast_data = PriceService.forecast_price({"crop": crop, "mandi": mandi, "state": farmer_profile.get("state", "")})` (wrapped in try/except; falls back to `None` on error)
7. Call `FinancialAdvisorService.analyze(...)` with these inputs.
8. Return the JSON result with HTTP 200.

Example request (shell/curl):

```bash
curl -G "http://<host>/financial-protection" \
  --data-urlencode "district=Pune" \
  --data-urlencode "crop=Rice"
```

Example response (shape)

{
  "financial_health_score": 72,
  "risk_level": "MODERATE",
  "risk_breakdown": {
    "weather_risk_score": 60,
    "market_risk_score": 55,
    "yield_risk_score": 53
  },
  "protection_gap": "High weather exposure and no active insurance detected. Evidence: high rainfall exposure; forecast volatility 0.12; yield confidence 70.0%.",
  "recommended_protection_actions": [
    {"type": "Insurance", "scheme_name": "PMFBY", "urgency": "HIGH", "reason": "High weather risk detected; insurance reduces shock losses.", "apply_link": "https://pmfby.gov.in"},
    {"type": "MSP Procurement", "scheme_name": "MSP", "urgency": "MEDIUM", ...}
  ]
}

Note: The numeric values above are illustrative; actual values depend on the inputs returned by the WeatherService, PriceService and YieldService.

## Edge cases, fallbacks and assumptions

- Missing forecast/yield/weather data: the analyzer uses conservative fallback scores (weather from severity mapping, market default=55, yield default=50) and explanatory reasons describing the simulation/fallback.
- Farmer profile variations: the code accepts either `landholding_acres` or `landholding_hectares`; if hectares are present, it converts to acres using 1 hectare = 2.47105 acres.
- Insurance detection accepts booleans or strings such as "yes", "true", "1" (case-insensitive) stored under any of: `has_insurance`, `insurance_active`, `pmfby_active`, `active_insurance`.
- Market `volatility` scaling uses `volatility * 250.0` then clamps to [0,100]. This is a design decision in the codebase to map model volatilities around 0.05–0.30 into a 0–100 risk scale.
- Forecast decreasing detection requires at least 7 price points; otherwise it treats the forecast as not decreasing.

## Where to change behaviour

- Adjust score thresholds and numeric mappings in helper functions:
  - Change `_severity_to_score` to modify weather numeric mapping.
  - Adjust volatility scaling factor in `_compute_market_score` (currently `* 250.0`) to tune market sensitivity.
  - Adjust risk label cutoffs in `_risk_label_from_score`.
- Add or remove recommended schemes and their triggers inside `_scheme_engine`.
- Extend `MSP_CROPS` set if new crops should be considered for MSP recommendations.

## Recommended next steps and tests

1. Add unit tests for `FinancialAdvisorService` covering:
   - Complete happy path: non-empty weather, price (with volatility), and yield inputs.
   - Missing price forecast (None) fallback behaviour.
   - Forecast decreasing detection with 7+ prices.
   - Insurance detection from string and boolean farmer profile values.

2. Add an integration test for `GET /financial-protection` that mocks `WeatherService`, `PriceService`, `YieldService`, and `FarmerService` to validate the full JSON shape and common branches.

3. Consider extracting numeric configuration (volatility scaling, score thresholds) into a small config class or environment variables to enable easier tuning without code edits.

## File references (quick map)

- `backend/services/financial_advisor_service.py` — main logic (scoring, protection_gap, scheme engine, helpers). Look for methods: `analyze`, `_compute_weather_score`, `_compute_market_score`, `_compute_yield_score`, `_build_protection_gap`, `_scheme_engine`, `_forecast_is_decreasing`.
- `backend/routes/financial_routes.py` — how the endpoint collects inputs and calls the analyzer.
- `backend/services/intelligence_engine.py` — region profiles and scheme references used elsewhere in the codebase; may be useful when adding region-specific schemes.

---

This file intentionally documents the *current* implementation in code, describing exact rules and transformations used to produce outputs. If you want, I can also add unit tests and an integration test harness plus a short example notebook to experiment with inputs and see computed scores interactively.

If you'd like this to be added to the root `README.md` instead or to be committed as `README.md`, tell me and I will move it there.
