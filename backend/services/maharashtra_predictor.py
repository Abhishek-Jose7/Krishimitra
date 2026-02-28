# ============================================================
# maharashtra_predictor.py
#
# Loads pre-trained XGBoost models for Maharashtra cabbage
# price prediction. Exposes 7-day + 30th-day forecasts.
#
# Usage:
#   from services.maharashtra_predictor import MaharashtraForecaster
#   result = MaharashtraForecaster.get_forecast("cabbage", "Pune APMC")
# ============================================================

import json
import os
import numpy as np
import pandas as pd
import xgboost as xgb
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# ─── Base directory for artefacts ────────────────────────────
_BASE_DIR = Path(__file__).resolve().parent.parent / "maharashtra"

# ─── Staleness threshold: markets with data older than this
#     are excluded from nearby-market comparisons ─────────────
_STALE_DAYS = 60

# ─── Max allowed overnight price change in forecast (%) ──────
_MAX_DAILY_PCT = 15.0  # Cabbage is highly volatile


# =============================================================
#  CabbagePredictor
# =============================================================
class CabbagePredictor:
    """
    Loads the cabbage XGBoost model and artefacts.
    Produces single-day predictions and multi-day forecasts.
    """

    # Cabbage does not have an MSP. We use a cost-of-production proxy to alert farmers.
    COP_PROXY = 500          # Rs./quintal — rough cost of production proxy
    LOSS_PER_DAY = 3.0       # % quality loss per day (ambient)

    def __init__(self, artefact_dir: str = None):
        if artefact_dir is None:
            artefact_dir = str(_BASE_DIR / "cabbage_model_artefacts")

        logger.info(f"Loading cabbage model from {artefact_dir} ...")
        self._load(artefact_dir)
        logger.info(
            f"✅ Cabbage model ready — MAE ₹{self.performance['MAE_inr']:,}  "
            f"| {len(self.market_categories)} markets"
        )

    # ── Load artefacts ────────────────────────────────────────
    def _load(self, root: str):
        self.model = xgb.XGBRegressor()
        self.model.load_model(os.path.join(root, "cabbage_price_model.json"))

        with open(os.path.join(root, "market_categories.json")) as f:
            self.market_categories = json.load(f)

        with open(os.path.join(root, "feature_list.json")) as f:
            meta = json.load(f)
            self.features = meta["features"]

        with open(os.path.join(root, "bias_correction.json")) as f:
            bc = json.load(f)
            self.bias_meta = bc
            self.bias = {int(k): v for k, v in bc.get("corrections", {}).items()}

        self.mkt_medians = pd.read_csv(os.path.join(root, "market_month_medians.csv"))

        self.price_lags = pd.read_csv(
            os.path.join(root, "price_lags_latest.csv")
        ).set_index("market")

        with open(os.path.join(root, "model_performance.json")) as f:
            self.performance = json.load(f)

        with open(os.path.join(root, "festival_calendar.json")) as f:
            self.festivals = json.load(f)

    # ── Check data freshness for a market ─────────────────────
    def _is_market_fresh(self, market: str) -> bool:
        """Returns True if the market's lag data is < _STALE_DAYS old."""
        if market not in self.price_lags.index:
            return False
        row = self.price_lags.loc[market]
        try:
            latest = pd.to_datetime(row["latest_date"])
            return (datetime.now() - latest).days <= _STALE_DAYS
        except Exception:
            return False

    def fresh_markets(self) -> list:
        """Return only markets with recent (<60 day) data."""
        return sorted([m for m in self.market_categories if self._is_market_fresh(m)])

    # ── Interpolate market_month_median near month boundaries ─
    def _get_smoothed_median(self, market: str, date: datetime) -> float:
        import calendar
        m = date.month
        day = date.day
        days_in_month = calendar.monthrange(date.year, m)[1]

        # Get current month median
        mm_curr = self.mkt_medians[
            (self.mkt_medians["market"] == market) &
            (self.mkt_medians["month"]  == m)
        ]
        curr_med = float(mm_curr["median_price"].values[0]) if len(mm_curr) > 0 else None

        if curr_med is None:
            return 800.0  # default fallback for cabbage

        if day > days_in_month - 5:
            next_m = (m % 12) + 1
            mm_next = self.mkt_medians[
                (self.mkt_medians["market"] == market) &
                (self.mkt_medians["month"]  == next_m)
            ]
            if len(mm_next) > 0:
                next_med = float(mm_next["median_price"].values[0])
                blend = (day - (days_in_month - 5)) / 5.0
                return curr_med * (1 - blend) + next_med * blend

        if day <= 5:
            prev_m = 12 if m == 1 else m - 1
            mm_prev = self.mkt_medians[
                (self.mkt_medians["market"] == market) &
                (self.mkt_medians["month"]  == prev_m)
            ]
            if len(mm_prev) > 0:
                prev_med = float(mm_prev["median_price"].values[0])
                blend = (5 - day) / 5.0
                return prev_med * blend + curr_med * (1 - blend)

        return curr_med

    # ── Build one feature row ─────────────────────────────────
    def _build_feature_row(self, market: str, date: datetime,
                           quantity: float,
                           temp_c: float = None,
                           rain_mm: float = None,
                           rain_7d: float = None,
                           lag_7_override: float = None,
                           lag_14_override: float = None,
                           lag_30_override: float = None) -> pd.DataFrame:
        m   = date.month
        doy = date.timetuple().tm_yday
        wk  = int(date.strftime("%W"))
        dow = date.weekday()

        if market in self.market_categories:
            mkt_val = market
        else:
            matches = [c for c in self.market_categories
                       if market.split()[0].lower() in c.lower()]
            mkt_val = matches[0] if matches else self.market_categories[0]

        # Lag prices — use overrides if provided
        if market in self.price_lags.index:
            lag_row = self.price_lags.loc[market]
            lag_7  = float(lag_row["p7d_ago"])  if lag_7_override  is None else lag_7_override
            lag_14 = float(lag_row.get("p14d_ago", 800.0)) if lag_14_override is None else lag_14_override
            lag_30 = float(lag_row["p30d_ago"]) if lag_30_override is None else lag_30_override
        else:
            lag_7  = lag_7_override  or 800.0
            lag_14 = lag_14_override or 800.0
            lag_30 = lag_30_override or 800.0

        mkt_med = self._get_smoothed_median(market, date)

        # Weather defaults (Maharashtra)
        TEMP_NORM = {1:22,2:25,3:29,4:32,5:34,6:30,7:27,8:26,9:27,10:28,11:25,12:22}
        RAIN_NORM = {1:1, 2:1, 3:2, 4:5, 5:15, 6:150,7:250,8:200,9:120,10:60,11:10, 12:2}
        if temp_c is None:
            next_m = (m % 12) + 1
            frac = date.day / 30.0
            temp_c = float(TEMP_NORM[m]) * (1 - frac) + float(TEMP_NORM[next_m]) * frac
        if rain_mm is None:
            next_m = (m % 12) + 1
            frac = date.day / 30.0
            rain_mm = float(RAIN_NORM[m]) * (1 - frac) + float(RAIN_NORM[next_m]) * frac
        rain_7d = rain_7d if rain_7d is not None else rain_mm

        # Spoilage rate (temp dependent)
        temp_spoilage_rate = max(0, (temp_c - 20) / 10.0)

        def sc(peak, sharp=1.0):
            fractional_month = m + (date.day - 1) / 30.0
            return float(max(0, np.cos(2 * np.pi * (fractional_month - peak) / 12 * sharp)))

        FEST = self._festival_for(date)[1]

        row = {
            "market_cat"            : mkt_val,
            "arrival_quantity_log"  : np.log1p(max(quantity, 0.1)),
            "qty_rolling_7d_log"    : np.log1p(max(quantity, 0.1)),
            "temp_avg_c"            : temp_c,
            "temp_spoilage_rate"    : temp_spoilage_rate,
            "precipitation_mm"      : rain_mm,
            "rain_7d_rolling"       : rain_7d,
            "month_sin"             : np.sin(2 * np.pi * doy / 365),
            "month_cos"             : np.cos(2 * np.pi * doy / 365),
            "doy_sin"               : np.sin(2 * np.pi * doy / 365),
            "doy_cos"               : np.cos(2 * np.pi * doy / 365),
            "week_sin"              : np.sin(2 * np.pi * wk / 52),
            "week_cos"              : np.cos(2 * np.pi * wk / 52),
            "dow_sin"               : np.sin(2 * np.pi * dow / 7),
            "dow_cos"               : np.cos(2 * np.pi * dow / 7),
            "year_trend"            : (date.year - 2021) / 4.0,
            
            # Cabbage season signals
            "rabi_glut"             : sc(1, 1.5),     # Highest supply Jan-Feb
            "kharif_glut"           : sc(11, 1.5),    # Late Kharif supply
            "summer_crop"           : sc(4, 1.5),     # Weak supply April
            "monsoon_lean"          : sc(7.5, 1.5),   # Lowest supply Jul-Aug (high prices)
            "pre_kharif_lean"       : sc(9.5, 1.5),   # Pre-harvest lean Sep-Oct
            "rabi_taper"            : sc(3, 1.5),     # Supply dropping in Mar
            "heat_stress"           : sc(5, 2.0),     # Max heat May
            "monsoon_disruption"    : sc(7, 2.0),     # Peak rain transport disruption
            "festival_demand"       : FEST,
            "interstate_competition": sc(2, 1.0),
            
            "lag_7"                 : lag_7,
            "lag_14"                : lag_14,
            "lag_30"                : lag_30,
            "price_momentum"        : 0.0,
            "market_month_median"   : mkt_med,
            "market_price_trend"    : 0.0,
            "price_spread"          : 250.0,
            "relative_spread"       : 0.2
        }

        row_filtered = {k: row.get(k, 0) for k in self.features}
        df = pd.DataFrame([row_filtered])

        df["market_cat"] = pd.Categorical(
            df["market_cat"],
            categories=self.market_categories
        )
        return df

    # ── Festival lookup ───────────────────────────────────────
    def _festival_for(self, date: datetime):
        m, d = date.month, date.day
        for f in self.festivals:
            if f["month"] == m and f["day_start"] <= d <= f["day_end"]:
                return f["name"], f["boost_pct"]
        return None, 0

    # ── Single prediction ─────────────────────────────────────
    def predict(self, market: str, date: datetime = None,
                quantity: float = 10.0,
                temp_c: float = None, rain_mm: float = None) -> dict:
        if date is None:
            date = datetime.now()

        row   = self._build_feature_row(market, date, quantity, temp_c, rain_mm)
        raw   = float(self.model.predict(row)[0])
        corr  = self.bias.get(date.month, 0.0)
        price = raw + corr

        fest_name, boost = self._festival_for(date)
        price_adj = price * (1 + boost / 100)
        
        # Absolute floor. Cabbage can go very low (e.g. 150 Rs/qtl)
        price_adj = max(price_adj, 150.0)

        revenue = price_adj * quantity
        above_cop = price_adj >= self.COP_PROXY

        if above_cop:
            msp_note = f"₹{price_adj - self.COP_PROXY:,.0f} above est. Cost of Production"
        else:
            msp_note = f"⚠️ ₹{self.COP_PROXY - price_adj:,.0f} BELOW est. Cost of Production — Risk of distress sale"

        m = date.month
        seasons = {
            (12, 1, 2) : "Rabi Glut — Heavy supply, lowest prices of the year",
            (3, 4, 5)  : "Summer — Heat affects quality, supply tapers",
            (6, 7, 8)  : "Monsoon Lean — Highest prices due to rain damage and transport issues",
            (9, 10, 11): "Kharif Transition — Prices moderate as new crop arrives",
        }
        season = "Transition period"
        for months, label in seasons.items():
            if m in months:
                season = label
                break

        # Generate a decision based purely on perishable nature and COP
        decision = "SELL_IMMEDIATELY" if price_adj > self.COP_PROXY * 1.5 else "SELL (Perishable)"

        return {
            "market"          : market,
            "date"            : date.strftime("%d %b %Y"),
            "predicted_price" : round(price_adj),
            "raw_price"       : round(raw),
            "bias_correction" : round(corr),
            "festival"        : fest_name,
            "festival_boost"  : boost,
            "msp_note"        : msp_note,
            "above_msp"       : above_cop,
            "season"          : season,
            "revenue"         : round(revenue),
            "quantity"        : quantity,
            "decision"        : decision,
            "model_mae"       : self.performance["MAE_inr"],
            "model_built_at"  : self.performance["built_at"],
        }

    # ── Multi-day forecast (with rolling lag propagation) ─────
    def forecast(self, market: str, days: int = 7,
                 quantity: float = 10.0,
                 storage_days: int = 0) -> dict:
        today        = datetime.now()
        today_result = self.predict(market, today, quantity)
        today_price  = today_result["predicted_price"]

        if market in self.price_lags.index:
            lr = self.price_lags.loc[market]
            base_lag_7  = float(lr["p7d_ago"])
            base_lag_14 = float(lr.get("p14d_ago", today_price))
            base_lag_30 = float(lr["p30d_ago"])
        else:
            base_lag_7 = base_lag_14 = base_lag_30 = today_price

        rolling_lag_7  = base_lag_7
        rolling_lag_14 = base_lag_14
        rolling_lag_30 = base_lag_30
        rolling_prices = [today_price]

        forecast_list = []
        for i in range(1, days + 1):
            fd  = today + timedelta(days=i)

            row = self._build_feature_row(
                market, fd, quantity,
                lag_7_override=rolling_lag_7,
                lag_14_override=rolling_lag_14,
                lag_30_override=rolling_lag_30,
            )

            raw   = float(self.model.predict(row)[0])
            corr  = self.bias.get(fd.month, 0.0)
            price = max(raw + corr, 150.0)

            fn, fboost = self._festival_for(fd)
            price = price * (1 + fboost / 100)

            # Cap overnight jump
            prev_price = rolling_prices[-1]
            max_delta  = prev_price * _MAX_DAILY_PCT / 100
            if abs(price - prev_price) > max_delta:
                direction = 1 if price > prev_price else -1
                price = prev_price + direction * max_delta

            rolling_prices.append(price)

            alpha = 0.4 # Higher alpha for cabbage due to volatility
            rolling_lag_7  = alpha * price + (1 - alpha) * rolling_lag_7
            rolling_lag_14 = alpha * price + (1 - alpha) * rolling_lag_14
            rolling_lag_30 = alpha * price + (1 - alpha) * rolling_lag_30

            forecast_list.append({
                "day"       : fd.strftime("%a %d %b"),
                "date"      : fd.strftime("%Y-%m-%d"),
                "price"     : round(price),
                "festival"  : fn,
                "above_msp" : price >= self.COP_PROXY,
            })

        best_day = {"day": "Today", "price": today_price,
                    "net_price": today_price, "gain_pct": 0.0}
        
        # Cabbage loses max 3% per day if not in cold store
        if storage_days > 0 and storage_days <= 7:
            for i, f in enumerate(forecast_list[:storage_days]):
                net = f["price"] * (1 - self.LOSS_PER_DAY * (i + 1) / 100)
                if net > best_day["net_price"]:
                    best_day = {
                        "day"      : f["day"],
                        "price"    : f["price"],
                        "net_price": round(net),
                        "gain_pct" : round((net - today_price) / today_price * 100, 1),
                    }

        prices    = [f["price"] for f in forecast_list]
        trend_pct = (prices[-1] - today_price) / today_price * 100 if prices else 0

        return {
            "today"     : today_result,
            "forecast"  : forecast_list,
            "best_day"  : best_day,
            "trend_pct" : round(trend_pct, 1),
        }

    def available_markets(self) -> list:
        return sorted(self.market_categories)

    def model_info(self) -> dict:
        return {
            "commodity"    : "Cabbage",
            "price_unit"   : "Rs. per quintal (100 kg)",
            "msp_floor"    : "None (Cost of Production proxy used)",
            "storage_loss" : f"{self.LOSS_PER_DAY}% per day (ambient)",
            "markets"      : len(self.market_categories),
            "mae_inr"      : self.performance["MAE_inr"],
            "mape_pct"     : self.performance.get("MAPE_pct"),
            "built_at"     : self.performance["built_at"],
        }


# =============================================================
#  MaharashtraForecaster  — singleton manager
# =============================================================
class MaharashtraForecaster:
    """
    Lazy-loads cabbage predictor once at first use.
    Provides a unified entry point for the rest of the app.
    """

    _cabbage: CabbagePredictor = None

    # Which crops are supported by Maharashtra-specific models
    SUPPORTED_CROPS = {"cabbage"}

    @classmethod
    def _normalize_crop(cls, crop: str) -> str:
        """Normalize crop name to canonical form."""
        return crop.lower().strip()

    @classmethod
    def _ensure_loaded(cls, crop: str):
        crop_l = cls._normalize_crop(crop)
        if crop_l == "cabbage" and cls._cabbage is None:
            cls._cabbage = CabbagePredictor()

    @classmethod
    def _predictor(cls, crop: str):
        crop_l = cls._normalize_crop(crop)
        cls._ensure_loaded(crop_l)
        if crop_l == "cabbage":
            return cls._cabbage
        return None

    @classmethod
    def is_supported(cls, state: str, crop: str) -> bool:
        """Check if this crop should use Maharashtra models based on user location."""
        if not state or not crop:
            return False
        return (
            state.lower().strip() in ("maharashtra", "mh")
            and cls._normalize_crop(crop) in cls.SUPPORTED_CROPS
        )

    @classmethod
    def get_forecast(cls, crop: str, market: str,
                     quantity: float = 10.0) -> dict:
        """
        Returns a dict with forecast results.
        """
        predictor = cls._predictor(crop)
        if predictor is None:
            return None

        # 7-day forecast
        fc7 = predictor.forecast(market, days=7, quantity=quantity,
                                 storage_days=7) # shorter storage for cabbage

        # 30th-day prediction
        target_date = datetime.now() + timedelta(days=30)
        day30 = predictor.predict(market, target_date, quantity)

        return {
            "today"              : fc7["today"],
            "forecast_7day"      : fc7["forecast"],
            "day_30"             : day30,
            "trend_7d_pct"       : fc7["trend_pct"],
            "best_day"           : fc7["best_day"],
            "model_info"         : predictor.model_info(),
            "available_markets"  : predictor.available_markets(),
            "fresh_markets"      : predictor.fresh_markets(),
        }
