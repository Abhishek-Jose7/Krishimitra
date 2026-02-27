-- ============================================================================
-- KrishiMitra AI — Complete PostgreSQL Schema for Supabase
-- ============================================================================
-- Run this SQL in Supabase SQL Editor (Dashboard → SQL Editor → New Query)
-- This creates all 11 tables with proper domains, indexes, and RLS-ready structure.
-- ============================================================================

-- ============================================================================
-- 🔹 EXTENSIONS
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- 🔹 DOMAIN 1: USER DOMAIN
-- ============================================================================

-- 1️⃣ USERS TABLE — Login + Identity (minimal, no farm data mixed in)
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    phone           VARCHAR(15) UNIQUE NOT NULL,
    name            VARCHAR(100),
    language        VARCHAR(10) DEFAULT 'en',
    state           VARCHAR(50),
    district        VARCHAR(50),
    taluk           VARCHAR(100),
    latitude        DOUBLE PRECISION,
    longitude       DOUBLE PRECISION,
    onboarding_complete BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Index for phone-based login
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);


-- ============================================================================
-- 🔹 DOMAIN 2: FARM DOMAIN
-- ============================================================================

-- 2️⃣ FARMS TABLE — One user can have multiple farms
CREATE TABLE IF NOT EXISTS farms (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    farm_name                   VARCHAR(100),
    total_land_hectares         DOUBLE PRECISION,
    soil_type                   VARCHAR(50),
    irrigation_type             VARCHAR(50),
    has_storage                 BOOLEAN DEFAULT FALSE,
    storage_capacity_quintals   DOUBLE PRECISION DEFAULT 0,
    created_at                  TIMESTAMPTZ DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_farms_user_id ON farms(user_id);


-- ============================================================================
-- 🔹 DOMAIN 3: CROP DOMAIN
-- ============================================================================

-- 3️⃣ FARM_CROPS TABLE — One farm → multiple crops (drives dashboard personalization)
CREATE TABLE IF NOT EXISTS farm_crops (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    farm_id                 UUID NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
    crop_name               VARCHAR(50) NOT NULL,
    variety                 VARCHAR(100),
    area_hectares           DOUBLE PRECISION,
    sowing_date             DATE,
    expected_harvest_date   DATE,
    planting_year           INTEGER,                -- for perennial crops
    tree_count              INTEGER,                -- optional, for orchards
    is_perennial            BOOLEAN DEFAULT FALSE,
    preferred_mandi         VARCHAR(100),           -- preferred market for this crop
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_farm_crops_farm_id ON farm_crops(farm_id);
CREATE INDEX IF NOT EXISTS idx_farm_crops_crop_name ON farm_crops(crop_name);


-- ============================================================================
-- 🔹 DOMAIN 4: MARKET DOMAIN (System Data)
-- ============================================================================

-- 4️⃣ PRICE_HISTORY TABLE — Mandi prices (feeds forecasting models)
CREATE TABLE IF NOT EXISTS price_history (
    id                  BIGSERIAL PRIMARY KEY,
    state               VARCHAR(50) NOT NULL,
    district            VARCHAR(50) NOT NULL,
    market              VARCHAR(100) NOT NULL,
    commodity           VARCHAR(50) NOT NULL,
    arrival_date        DATE NOT NULL,
    min_price           DOUBLE PRECISION,
    max_price           DOUBLE PRECISION,
    modal_price         DOUBLE PRECISION,
    arrival_quantity    DOUBLE PRECISION,       -- in quintals
    source              VARCHAR(50) DEFAULT 'agmarknet',
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Compound index for forecasting queries (CRITICAL for performance)
CREATE INDEX IF NOT EXISTS idx_price_history_commodity_market_date
    ON price_history(commodity, market, arrival_date DESC);
CREATE INDEX IF NOT EXISTS idx_price_history_state ON price_history(state);
CREATE INDEX IF NOT EXISTS idx_price_history_district ON price_history(district);
CREATE INDEX IF NOT EXISTS idx_price_history_arrival_date ON price_history(arrival_date DESC);


-- ============================================================================
-- 🔹 DOMAIN 5: WEATHER DOMAIN (System Data)
-- ============================================================================

-- 5️⃣ WEATHER_HISTORY TABLE — Used for yield prediction & price forecasting
CREATE TABLE IF NOT EXISTS weather_history (
    id                  BIGSERIAL PRIMARY KEY,
    state               VARCHAR(50),
    district            VARCHAR(50) NOT NULL,
    market              VARCHAR(100),
    date                DATE NOT NULL,
    temp_max_c          DOUBLE PRECISION,
    temp_min_c          DOUBLE PRECISION,
    temp_avg_c          DOUBLE PRECISION,
    humidity            DOUBLE PRECISION,
    precipitation_mm    DOUBLE PRECISION,
    rain_7d_rolling     DOUBLE PRECISION,
    condition           VARCHAR(50),
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Compound index for weather lookups
CREATE INDEX IF NOT EXISTS idx_weather_history_district_date
    ON weather_history(district, date DESC);
CREATE INDEX IF NOT EXISTS idx_weather_history_market_date
    ON weather_history(market, date DESC);


-- ============================================================================
-- 🔹 DOMAIN 6: ML PREDICTIONS DOMAIN
-- ============================================================================

-- 6️⃣ YIELD_PREDICTIONS TABLE — Model outputs per farm-crop
CREATE TABLE IF NOT EXISTS yield_predictions (
    id                              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    farm_crop_id                    UUID NOT NULL REFERENCES farm_crops(id) ON DELETE CASCADE,
    prediction_date                 DATE NOT NULL DEFAULT CURRENT_DATE,
    predicted_yield_per_hectare     DOUBLE PRECISION NOT NULL,
    predicted_total_production      DOUBLE PRECISION,
    actual_yield                    DOUBLE PRECISION,          -- filled later for retraining
    confidence_score                DOUBLE PRECISION,
    risk_level                      VARCHAR(20),               -- LOW / MEDIUM / HIGH
    model_version                   VARCHAR(50),
    created_at                      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_yield_predictions_farm_crop
    ON yield_predictions(farm_crop_id);
CREATE INDEX IF NOT EXISTS idx_yield_predictions_date
    ON yield_predictions(prediction_date DESC);


-- 7️⃣ PRICE_FORECASTS TABLE — Allows backtesting, accuracy tracking, drift detection
CREATE TABLE IF NOT EXISTS price_forecasts (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    commodity           VARCHAR(50) NOT NULL,
    market              VARCHAR(100) NOT NULL,
    forecast_date       DATE NOT NULL DEFAULT CURRENT_DATE,
    horizon_days        INTEGER NOT NULL DEFAULT 7,    -- 7 or 30
    predicted_price     DOUBLE PRECISION NOT NULL,
    lower_bound         DOUBLE PRECISION,
    upper_bound         DOUBLE PRECISION,
    actual_price        DOUBLE PRECISION,              -- filled later for evaluation
    confidence_score    DOUBLE PRECISION,
    model_version       VARCHAR(50),
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_price_forecasts_commodity_market
    ON price_forecasts(commodity, market, forecast_date DESC);


-- ============================================================================
-- 🔹 DOMAIN 7: RECOMMENDATION DOMAIN
-- ============================================================================

-- 8️⃣ RECOMMENDATIONS TABLE — Full transparency + auditability
CREATE TABLE IF NOT EXISTS recommendations (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    farm_crop_id            UUID NOT NULL REFERENCES farm_crops(id) ON DELETE CASCADE,
    recommendation_date     DATE NOT NULL DEFAULT CURRENT_DATE,
    current_price           DOUBLE PRECISION,
    forecast_price          DOUBLE PRECISION,
    expected_yield          DOUBLE PRECISION,
    sell_now_revenue        DOUBLE PRECISION,
    hold_revenue            DOUBLE PRECISION,
    storage_cost            DOUBLE PRECISION,
    decision                VARCHAR(20) NOT NULL,          -- SELL / HOLD / PARTIAL
    risk_score              DOUBLE PRECISION,
    confidence_score        DOUBLE PRECISION,
    explanation_text        TEXT,
    overseer_flag           VARCHAR(30),                   -- APPROVED / FLAGGED / OVERRIDDEN
    overseer_reason         TEXT,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recommendations_farm_crop
    ON recommendations(farm_crop_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_date
    ON recommendations(recommendation_date DESC);


-- ============================================================================
-- 🔹 DOMAIN 8: NOTIFICATIONS DOMAIN
-- ============================================================================

-- 9️⃣ PRICE_ALERTS TABLE — User-set price threshold alerts
CREATE TABLE IF NOT EXISTS price_alerts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    commodity       VARCHAR(50) NOT NULL,
    market          VARCHAR(100) NOT NULL,
    target_price    DOUBLE PRECISION NOT NULL,
    direction       VARCHAR(10) NOT NULL DEFAULT 'ABOVE',  -- ABOVE / BELOW
    is_active       BOOLEAN DEFAULT TRUE,
    is_read         BOOLEAN DEFAULT FALSE,
    triggered_at    TIMESTAMPTZ,
    triggered_price DOUBLE PRECISION,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_price_alerts_user_id ON price_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_price_alerts_active
    ON price_alerts(commodity, market) WHERE is_active = TRUE;


-- ============================================================================
-- 🔹 DOMAIN 9: EVALUATION & DRIFT DOMAIN
-- ============================================================================

-- 🔟 EVALUATION_METRICS TABLE — Model monitoring (used by AI Overseer)
CREATE TABLE IF NOT EXISTS evaluation_metrics (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_type              VARCHAR(50) NOT NULL,          -- 'yield' / 'price'
    commodity               VARCHAR(50),
    market                  VARCHAR(100),
    horizon                 INTEGER,                       -- forecast horizon in days
    mae                     DOUBLE PRECISION,
    mape                    DOUBLE PRECISION,
    rmse                    DOUBLE PRECISION,
    directional_accuracy    DOUBLE PRECISION,
    sample_count            INTEGER,
    calculated_at           TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_evaluation_metrics_type
    ON evaluation_metrics(model_type, commodity);


-- 1️⃣1️⃣ MODEL_REGISTRY TABLE — Hot-swappable model management
CREATE TABLE IF NOT EXISTS model_registry (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_type      VARCHAR(50) NOT NULL,                  -- 'yield' / 'price'
    commodity       VARCHAR(50),
    version         VARCHAR(50) NOT NULL,
    file_path       TEXT NOT NULL,
    is_active       BOOLEAN DEFAULT TRUE,
    accuracy_score  DOUBLE PRECISION,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_model_registry_active
    ON model_registry(model_type, commodity) WHERE is_active = TRUE;


-- ============================================================================
-- 🔹 BONUS: OVERSEER AUDIT LOG (for AI safety & accountability)
-- ============================================================================

CREATE TABLE IF NOT EXISTS overseer_logs (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID REFERENCES users(id) ON DELETE SET NULL,
    farm_crop_id        UUID REFERENCES farm_crops(id) ON DELETE SET NULL,
    crop                VARCHAR(50) NOT NULL,
    market              VARCHAR(100),
    original_decision   VARCHAR(20) NOT NULL,
    final_decision      VARCHAR(20) NOT NULL,
    verdict             VARCHAR(30) NOT NULL,              -- APPROVED / FLAGGED / OVERRIDDEN
    reason              TEXT,
    confidence_before   DOUBLE PRECISION,
    confidence_after    DOUBLE PRECISION,
    warning_count       INTEGER DEFAULT 0,
    anomaly_count       INTEGER DEFAULT 0,
    drift_detected      BOOLEAN DEFAULT FALSE,
    warnings_json       JSONB,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_overseer_logs_user ON overseer_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_overseer_logs_date ON overseer_logs(created_at DESC);


-- ============================================================================
-- 🔹 BONUS: DISTRICT_CROP_STATS (regional benchmarks for yield comparison)
-- ============================================================================

CREATE TABLE IF NOT EXISTS district_crop_stats (
    id                  BIGSERIAL PRIMARY KEY,
    district            VARCHAR(50) NOT NULL,
    state               VARCHAR(50),
    crop                VARCHAR(50) NOT NULL,
    season              VARCHAR(20),                       -- kharif / rabi / zaid
    year                INTEGER NOT NULL,
    area_hectares       DOUBLE PRECISION,
    production_tonnes   DOUBLE PRECISION,
    yield_per_hectare   DOUBLE PRECISION,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_district_crop_stats_lookup
    ON district_crop_stats(district, crop, year DESC);


-- ============================================================================
-- 🔹 AUTO-UPDATE TRIGGER FOR updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables that have updated_at
CREATE TRIGGER set_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER set_farms_updated_at
    BEFORE UPDATE ON farms
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER set_farm_crops_updated_at
    BEFORE UPDATE ON farm_crops
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ============================================================================
-- 🔹 ROW LEVEL SECURITY (RLS) — Supabase best practice
-- ============================================================================
-- Enable RLS on user-facing tables. System tables are accessed via service_role.

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE farms ENABLE ROW LEVEL SECURITY;
ALTER TABLE farm_crops ENABLE ROW LEVEL SECURITY;
ALTER TABLE recommendations ENABLE ROW LEVEL SECURITY;
ALTER TABLE price_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE yield_predictions ENABLE ROW LEVEL SECURITY;

-- Example RLS policies (adjust auth.uid() mapping to your auth strategy)
-- Users can only see/modify their own data:

CREATE POLICY "Users can view own profile"
    ON users FOR SELECT
    USING (id = auth.uid());

CREATE POLICY "Users can update own profile"
    ON users FOR UPDATE
    USING (id = auth.uid());

CREATE POLICY "Users can view own farms"
    ON farms FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "Users can manage own farms"
    ON farms FOR ALL
    USING (user_id = auth.uid());

CREATE POLICY "Users can view own farm crops"
    ON farm_crops FOR SELECT
    USING (farm_id IN (SELECT id FROM farms WHERE user_id = auth.uid()));

CREATE POLICY "Users can manage own farm crops"
    ON farm_crops FOR ALL
    USING (farm_id IN (SELECT id FROM farms WHERE user_id = auth.uid()));

CREATE POLICY "Users can view own recommendations"
    ON recommendations FOR SELECT
    USING (farm_crop_id IN (
        SELECT fc.id FROM farm_crops fc
        JOIN farms f ON fc.farm_id = f.id
        WHERE f.user_id = auth.uid()
    ));

CREATE POLICY "Users can view own yield predictions"
    ON yield_predictions FOR SELECT
    USING (farm_crop_id IN (
        SELECT fc.id FROM farm_crops fc
        JOIN farms f ON fc.farm_id = f.id
        WHERE f.user_id = auth.uid()
    ));

CREATE POLICY "Users can view own alerts"
    ON price_alerts FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "Users can manage own alerts"
    ON price_alerts FOR ALL
    USING (user_id = auth.uid());


-- ============================================================================
-- ✅ SCHEMA COMPLETE
-- ============================================================================
-- Total tables: 13
--   User domain:       users
--   Farm domain:        farms, farm_crops
--   Market domain:      price_history
--   Weather domain:     weather_history
--   ML Predictions:     yield_predictions, price_forecasts
--   Recommendations:    recommendations
--   Notifications:      price_alerts
--   Evaluation & Drift: evaluation_metrics, model_registry
--   Audit:              overseer_logs
--   Reference:          district_crop_stats
-- ============================================================================
