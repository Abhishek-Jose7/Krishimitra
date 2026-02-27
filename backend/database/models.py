from database.db import db
from datetime import datetime, date


# ============================================================================
# 🔹 DOMAIN 1: USER DOMAIN
# ============================================================================

class User(db.Model):
    """Login + Identity — minimal, no farm data mixed in."""
    __tablename__ = 'users'

    id = db.Column(db.String(36), primary_key=True)
    phone = db.Column(db.String(15), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=True)  # nullable — OTP-only users won't have one
    name = db.Column(db.String(100))
    language = db.Column(db.String(10), default='en')
    state = db.Column(db.String(50))
    district = db.Column(db.String(50))
    taluk = db.Column(db.String(100))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    onboarding_complete = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    farms = db.relationship('Farm', backref='user', lazy=True, cascade='all, delete-orphan')
    price_alerts = db.relationship('PriceAlert', backref='user', lazy=True, cascade='all, delete-orphan')
    overseer_logs = db.relationship('OverseerLog', backref='user', lazy=True)

    def to_dict(self):
        return {
            'id': self.id, 'phone': self.phone, 'name': self.name,
            'language': self.language, 'state': self.state,
            'district': self.district, 'taluk': self.taluk,
            'latitude': self.latitude, 'longitude': self.longitude,
            'onboarding_complete': self.onboarding_complete,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ============================================================================
# 🔹 DOMAIN 2: FARM DOMAIN
# ============================================================================

class Farm(db.Model):
    """One user can have multiple farms."""
    __tablename__ = 'farms'

    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    farm_name = db.Column(db.String(100))
    total_land_hectares = db.Column(db.Float)
    soil_type = db.Column(db.String(50))
    irrigation_type = db.Column(db.String(50))
    has_storage = db.Column(db.Boolean, default=False)
    storage_capacity_quintals = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    crops = db.relationship('FarmCrop', backref='farm', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id, 'user_id': self.user_id,
            'farm_name': self.farm_name,
            'total_land_hectares': self.total_land_hectares,
            'soil_type': self.soil_type, 'irrigation_type': self.irrigation_type,
            'has_storage': self.has_storage,
            'storage_capacity_quintals': self.storage_capacity_quintals,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ============================================================================
# 🔹 DOMAIN 3: CROP DOMAIN
# ============================================================================

class FarmCrop(db.Model):
    """One farm → multiple crops. Drives dashboard personalization."""
    __tablename__ = 'farm_crops'

    id = db.Column(db.String(36), primary_key=True)
    farm_id = db.Column(db.String(36), db.ForeignKey('farms.id'), nullable=False)
    crop_name = db.Column(db.String(50), nullable=False, index=True)
    variety = db.Column(db.String(100))
    area_hectares = db.Column(db.Float)
    sowing_date = db.Column(db.Date)
    expected_harvest_date = db.Column(db.Date)
    planting_year = db.Column(db.Integer)           # for perennial crops
    tree_count = db.Column(db.Integer)               # optional, orchards
    is_perennial = db.Column(db.Boolean, default=False)
    preferred_mandi = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    yield_predictions = db.relationship('YieldPrediction', backref='farm_crop', lazy=True, cascade='all, delete-orphan')
    recommendations = db.relationship('Recommendation', backref='farm_crop', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id, 'farm_id': self.farm_id,
            'crop_name': self.crop_name, 'variety': self.variety,
            'area_hectares': self.area_hectares,
            'sowing_date': self.sowing_date.isoformat() if self.sowing_date else None,
            'expected_harvest_date': self.expected_harvest_date.isoformat() if self.expected_harvest_date else None,
            'planting_year': self.planting_year, 'tree_count': self.tree_count,
            'is_perennial': self.is_perennial,
            'preferred_mandi': self.preferred_mandi,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


# ============================================================================
# 🔹 DOMAIN 4: MARKET DOMAIN (System Data)
# ============================================================================

class PriceHistory(db.Model):
    """Daily mandi price records — feeds forecasting models."""
    __tablename__ = 'price_history'

    id = db.Column(db.Integer, primary_key=True)
    state = db.Column(db.String(50), nullable=False)
    district = db.Column(db.String(50), nullable=False, index=True)
    market = db.Column(db.String(100), nullable=False, index=True)
    commodity = db.Column(db.String(50), nullable=False, index=True)
    arrival_date = db.Column(db.Date, nullable=False, index=True)
    min_price = db.Column(db.Float)
    max_price = db.Column(db.Float)
    modal_price = db.Column(db.Float)
    arrival_quantity = db.Column(db.Float)       # in quintals
    source = db.Column(db.String(50), default='agmarknet')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Compound index for forecasting queries
    __table_args__ = (
        db.Index('idx_price_commodity_market_date', 'commodity', 'market', 'arrival_date'),
    )

    def to_dict(self):
        return {
            'id': self.id, 'state': self.state, 'district': self.district,
            'market': self.market, 'commodity': self.commodity,
            'arrival_date': self.arrival_date.isoformat(),
            'min_price': self.min_price, 'max_price': self.max_price,
            'modal_price': self.modal_price,
            'arrival_quantity': self.arrival_quantity,
            'source': self.source,
        }


# ============================================================================
# 🔹 DOMAIN 5: WEATHER DOMAIN (System Data)
# ============================================================================

class WeatherHistory(db.Model):
    """Weather snapshots per district — for yield prediction & price forecasting."""
    __tablename__ = 'weather_history'

    id = db.Column(db.Integer, primary_key=True)
    state = db.Column(db.String(50))
    district = db.Column(db.String(50), nullable=False, index=True)
    market = db.Column(db.String(100))
    date = db.Column(db.Date, nullable=False, index=True)
    temp_max_c = db.Column(db.Float)
    temp_min_c = db.Column(db.Float)
    temp_avg_c = db.Column(db.Float)
    humidity = db.Column(db.Float)
    precipitation_mm = db.Column(db.Float)
    rain_7d_rolling = db.Column(db.Float)
    condition = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Compound index
    __table_args__ = (
        db.Index('idx_weather_district_date', 'district', 'date'),
        db.Index('idx_weather_market_date', 'market', 'date'),
    )

    def to_dict(self):
        return {
            'id': self.id, 'state': self.state, 'district': self.district,
            'market': self.market, 'date': self.date.isoformat(),
            'temp_max_c': self.temp_max_c, 'temp_min_c': self.temp_min_c,
            'temp_avg_c': self.temp_avg_c, 'humidity': self.humidity,
            'precipitation_mm': self.precipitation_mm,
            'rain_7d_rolling': self.rain_7d_rolling,
            'condition': self.condition,
        }


# ============================================================================
# 🔹 DOMAIN 6: ML PREDICTIONS DOMAIN
# ============================================================================

class YieldPrediction(db.Model):
    """Model outputs per farm-crop."""
    __tablename__ = 'yield_predictions'

    id = db.Column(db.String(36), primary_key=True)
    farm_crop_id = db.Column(db.String(36), db.ForeignKey('farm_crops.id'), nullable=False)
    prediction_date = db.Column(db.Date, nullable=False, default=date.today)
    predicted_yield_per_hectare = db.Column(db.Float, nullable=False)
    predicted_total_production = db.Column(db.Float)
    actual_yield = db.Column(db.Float)              # filled later for retraining
    confidence_score = db.Column(db.Float)
    risk_level = db.Column(db.String(20))           # LOW / MEDIUM / HIGH
    model_version = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'farm_crop_id': self.farm_crop_id,
            'prediction_date': self.prediction_date.isoformat(),
            'predicted_yield_per_hectare': self.predicted_yield_per_hectare,
            'predicted_total_production': self.predicted_total_production,
            'actual_yield': self.actual_yield,
            'confidence_score': self.confidence_score,
            'risk_level': self.risk_level, 'model_version': self.model_version,
        }


class PriceForecast(db.Model):
    """Allows backtesting, accuracy tracking, drift detection."""
    __tablename__ = 'price_forecasts'

    id = db.Column(db.String(36), primary_key=True)
    commodity = db.Column(db.String(50), nullable=False)
    market = db.Column(db.String(100), nullable=False)
    forecast_date = db.Column(db.Date, nullable=False, default=date.today)
    horizon_days = db.Column(db.Integer, nullable=False, default=7)    # 7 or 30
    predicted_price = db.Column(db.Float, nullable=False)
    lower_bound = db.Column(db.Float)
    upper_bound = db.Column(db.Float)
    actual_price = db.Column(db.Float)              # filled later for evaluation
    confidence_score = db.Column(db.Float)
    model_version = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Compound index
    __table_args__ = (
        db.Index('idx_forecast_commodity_market_date', 'commodity', 'market', 'forecast_date'),
    )

    def to_dict(self):
        return {
            'id': self.id, 'commodity': self.commodity, 'market': self.market,
            'forecast_date': self.forecast_date.isoformat(),
            'horizon_days': self.horizon_days,
            'predicted_price': self.predicted_price,
            'lower_bound': self.lower_bound, 'upper_bound': self.upper_bound,
            'actual_price': self.actual_price,
            'confidence_score': self.confidence_score,
            'model_version': self.model_version,
        }


# ============================================================================
# 🔹 DOMAIN 7: RECOMMENDATION DOMAIN
# ============================================================================

class Recommendation(db.Model):
    """Full transparency + auditability for sell/hold decisions."""
    __tablename__ = 'recommendations'

    id = db.Column(db.String(36), primary_key=True)
    farm_crop_id = db.Column(db.String(36), db.ForeignKey('farm_crops.id'), nullable=False)
    recommendation_date = db.Column(db.Date, nullable=False, default=date.today)
    current_price = db.Column(db.Float)
    forecast_price = db.Column(db.Float)
    expected_yield = db.Column(db.Float)
    sell_now_revenue = db.Column(db.Float)
    hold_revenue = db.Column(db.Float)
    storage_cost = db.Column(db.Float)
    decision = db.Column(db.String(20), nullable=False)     # SELL / HOLD / PARTIAL
    risk_score = db.Column(db.Float)
    confidence_score = db.Column(db.Float)
    explanation_text = db.Column(db.Text)
    overseer_flag = db.Column(db.String(30))                # APPROVED / FLAGGED / OVERRIDDEN
    overseer_reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'farm_crop_id': self.farm_crop_id,
            'recommendation_date': self.recommendation_date.isoformat(),
            'current_price': self.current_price, 'forecast_price': self.forecast_price,
            'expected_yield': self.expected_yield,
            'sell_now_revenue': self.sell_now_revenue, 'hold_revenue': self.hold_revenue,
            'storage_cost': self.storage_cost, 'decision': self.decision,
            'risk_score': self.risk_score, 'confidence_score': self.confidence_score,
            'explanation_text': self.explanation_text,
            'overseer_flag': self.overseer_flag, 'overseer_reason': self.overseer_reason,
        }


# ============================================================================
# 🔹 DOMAIN 8: NOTIFICATIONS DOMAIN
# ============================================================================

class PriceAlert(db.Model):
    """User-set price threshold alerts."""
    __tablename__ = 'price_alerts'

    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    commodity = db.Column(db.String(50), nullable=False)
    market = db.Column(db.String(100), nullable=False)
    target_price = db.Column(db.Float, nullable=False)
    direction = db.Column(db.String(10), nullable=False, default='ABOVE')   # ABOVE / BELOW
    is_active = db.Column(db.Boolean, default=True)
    is_read = db.Column(db.Boolean, default=False)
    triggered_at = db.Column(db.DateTime, nullable=True)
    triggered_price = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'user_id': self.user_id,
            'commodity': self.commodity, 'market': self.market,
            'target_price': self.target_price, 'direction': self.direction,
            'is_active': self.is_active, 'is_read': self.is_read,
            'triggered_at': self.triggered_at.isoformat() if self.triggered_at else None,
            'triggered_price': self.triggered_price,
            'created_at': self.created_at.isoformat(),
        }


# ============================================================================
# 🔹 DOMAIN 9: EVALUATION & DRIFT DOMAIN
# ============================================================================

class EvaluationMetric(db.Model):
    """Model monitoring — used by AI Overseer."""
    __tablename__ = 'evaluation_metrics'

    id = db.Column(db.String(36), primary_key=True)
    model_type = db.Column(db.String(50), nullable=False, index=True)   # 'yield' / 'price'
    commodity = db.Column(db.String(50))
    market = db.Column(db.String(100))
    horizon = db.Column(db.Integer)
    mae = db.Column(db.Float)
    mape = db.Column(db.Float)
    rmse = db.Column(db.Float)
    directional_accuracy = db.Column(db.Float)
    sample_count = db.Column(db.Integer)
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'model_type': self.model_type,
            'commodity': self.commodity, 'market': self.market,
            'horizon': self.horizon, 'mae': self.mae, 'mape': self.mape,
            'rmse': self.rmse, 'directional_accuracy': self.directional_accuracy,
            'sample_count': self.sample_count,
            'calculated_at': self.calculated_at.isoformat(),
        }


class ModelRegistry(db.Model):
    """Hot-swappable model management."""
    __tablename__ = 'model_registry'

    id = db.Column(db.String(36), primary_key=True)
    model_type = db.Column(db.String(50), nullable=False)       # 'yield' / 'price'
    commodity = db.Column(db.String(50))
    version = db.Column(db.String(50), nullable=False)
    file_path = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    accuracy_score = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'model_type': self.model_type,
            'commodity': self.commodity, 'version': self.version,
            'file_path': self.file_path, 'is_active': self.is_active,
            'accuracy_score': self.accuracy_score,
            'created_at': self.created_at.isoformat(),
        }


# ============================================================================
# 🔹 AUDIT DOMAIN
# ============================================================================

class OverseerLog(db.Model):
    """Audit trail for every AI Overseer decision."""
    __tablename__ = 'overseer_logs'

    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    farm_crop_id = db.Column(db.String(36), db.ForeignKey('farm_crops.id'), nullable=True)
    crop = db.Column(db.String(50), nullable=False)
    market = db.Column(db.String(100), nullable=True)
    original_decision = db.Column(db.String(20), nullable=False)
    final_decision = db.Column(db.String(20), nullable=False)
    verdict = db.Column(db.String(30), nullable=False)          # APPROVED / FLAGGED / OVERRIDDEN
    reason = db.Column(db.Text, nullable=True)
    confidence_before = db.Column(db.Float)
    confidence_after = db.Column(db.Float)
    warning_count = db.Column(db.Integer, default=0)
    anomaly_count = db.Column(db.Integer, default=0)
    drift_detected = db.Column(db.Boolean, default=False)
    warnings_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id': self.id, 'user_id': self.user_id,
            'farm_crop_id': self.farm_crop_id,
            'crop': self.crop, 'market': self.market,
            'original_decision': self.original_decision,
            'final_decision': self.final_decision,
            'verdict': self.verdict, 'reason': self.reason,
            'confidence_before': self.confidence_before,
            'confidence_after': self.confidence_after,
            'warning_count': self.warning_count,
            'anomaly_count': self.anomaly_count,
            'drift_detected': self.drift_detected,
            'created_at': self.created_at.isoformat(),
        }


# ============================================================================
# 🔹 REFERENCE DATA
# ============================================================================

class DistrictCropStats(db.Model):
    """Seasonal production statistics — benchmarks for yield comparison."""
    __tablename__ = 'district_crop_stats'

    id = db.Column(db.Integer, primary_key=True)
    district = db.Column(db.String(50), nullable=False, index=True)
    state = db.Column(db.String(50))
    crop = db.Column(db.String(50), nullable=False, index=True)
    season = db.Column(db.String(20))               # kharif / rabi / zaid
    year = db.Column(db.Integer, nullable=False)
    area_hectares = db.Column(db.Float)
    production_tonnes = db.Column(db.Float)
    yield_per_hectare = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'district': self.district, 'state': self.state,
            'crop': self.crop, 'season': self.season, 'year': self.year,
            'area_hectares': self.area_hectares,
            'production_tonnes': self.production_tonnes,
            'yield_per_hectare': self.yield_per_hectare,
        }


# ============================================================================
# BACKWARD COMPATIBILITY ALIAS
# ============================================================================
# The old codebase used "Farmer" — this alias prevents import breakage
# while we migrate routes to use the new User/Farm/FarmCrop structure.
Farmer = User
