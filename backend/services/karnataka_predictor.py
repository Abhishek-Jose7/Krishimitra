# ============================================================
# karnataka_predictor.py
#
# Loads pre-trained XGBoost models for Karnataka groundnut,
# coconut, and paddy price prediction.  Exposes 7-day + 30th-day forecasts.
#
# Usage:
#   from services.karnataka_predictor import KarnatakaForecaster
#   result = KarnatakaForecaster.get_forecast("groundnut", "Raichur APMC")
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
_BASE_DIR = Path(__file__).resolve().parent.parent / "karnataka"

# ─── Staleness threshold: markets with data older than this
#     are excluded from nearby-market comparisons ─────────────
_STALE_DAYS = 60

# ─── Max allowed overnight price change in forecast (%) ──────
_MAX_DAILY_PCT = 3.0


# =============================================================
#  GroundnutPredictor
# =============================================================
class GroundnutPredictor:
    """
    Loads the groundnut XGBoost model and artefacts.
    Produces single-day predictions and multi-day forecasts.
    """

    MSP_2025 = 6783          # Rs./quintal — govt floor price
    LOSS_PER_DAY = 0.25      # % quality loss per day in dry storage

    def __init__(self, artefact_dir: str = None):
        if artefact_dir is None:
            artefact_dir = str(_BASE_DIR / "groundnut" / "groundnut_model_artefacts")

        logger.info(f"Loading groundnut model from {artefact_dir} ...")
        self._load(artefact_dir)
        logger.info(
            f"✅ Groundnut model ready — MAE ₹{self.performance['MAE_inr']:,}  "
            f"| {len(self.market_categories)} markets"
        )

    # ── Load artefacts ────────────────────────────────────────
    def _load(self, root: str):
        self.model = xgb.XGBRegressor()
        self.model.load_model(os.path.join(root, "groundnut_price_model.json"))

        with open(os.path.join(root, "market_categories.json")) as f:
            self.market_categories = json.load(f)

        with open(os.path.join(root, "feature_list.json")) as f:
            meta = json.load(f)
            self.features = meta["features"]

        with open(os.path.join(root, "bias_correction.json")) as f:
            bc = json.load(f)
            self.bias = {int(k): v for k, v in bc["corrections"].items()}

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
        """
        Blends market_month_median between current and adjacent month
        when the date is within 5 days of a month boundary.
        Prevents the overnight cliff at month transitions.
        """
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
            return 6500.0  # default fallback for groundnut

        # Near end of month → blend with next month
        if day > days_in_month - 5:
            next_m = (m % 12) + 1
            mm_next = self.mkt_medians[
                (self.mkt_medians["market"] == market) &
                (self.mkt_medians["month"]  == next_m)
            ]
            if len(mm_next) > 0:
                next_med = float(mm_next["median_price"].values[0])
                # Linear blend: 0% next at day (days_in_month-5), 100% at day (days_in_month)
                blend = (day - (days_in_month - 5)) / 5.0
                return curr_med * (1 - blend) + next_med * blend

        # Near start of month → blend with previous month
        if day <= 5:
            prev_m = 12 if m == 1 else m - 1
            mm_prev = self.mkt_medians[
                (self.mkt_medians["market"] == market) &
                (self.mkt_medians["month"]  == prev_m)
            ]
            if len(mm_prev) > 0:
                prev_med = float(mm_prev["median_price"].values[0])
                # Linear blend: 100% prev at day 1, 0% prev at day 5
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
                           lag_30_override: float = None,
                           lag_90_override: float = None) -> pd.DataFrame:
        m   = date.month
        doy = date.timetuple().tm_yday
        wk  = int(date.strftime("%W"))

        # Resolve market name
        if market in self.market_categories:
            mkt_val = market
        else:
            matches = [c for c in self.market_categories
                       if market.split()[0].lower() in c.lower()]
            mkt_val = matches[0] if matches else self.market_categories[0]

        # Lag prices — use overrides if provided (rolling forecast)
        if market in self.price_lags.index:
            lag_row = self.price_lags.loc[market]
            lag_7  = float(lag_row["p7d_ago"])  if lag_7_override  is None else lag_7_override
            lag_30 = float(lag_row["p30d_ago"]) if lag_30_override is None else lag_30_override
            lag_90 = float(lag_row.get("p90d_ago", 6500.0)) if lag_90_override is None else lag_90_override
        else:
            lag_7  = lag_7_override  or 6500.0
            lag_30 = lag_30_override or 6500.0
            lag_90 = lag_90_override or 6500.0

        # Market × month median — smoothed near month boundaries
        mkt_med = self._get_smoothed_median(market, date)

        # Weather defaults (Karnataka groundnut belt seasonal normals)
        # Use fractional month for smoother weather interpolation
        TEMP_NORM = {1:22,2:25,3:29,4:32,5:33,6:28,7:27,8:27,9:28,10:27,11:24,12:22}
        RAIN_NORM = {1:1, 2:1, 3:1, 4:3, 5:5, 6:55,7:85,8:70,9:45,10:25,11:8, 12:3}
        if temp_c is None:
            # Interpolate between months for smoother weather
            next_m = (m % 12) + 1
            frac = date.day / 30.0
            temp_c = float(TEMP_NORM[m]) * (1 - frac) + float(TEMP_NORM[next_m]) * frac
        if rain_mm is None:
            next_m = (m % 12) + 1
            frac = date.day / 30.0
            rain_mm = float(RAIN_NORM[m]) * (1 - frac) + float(RAIN_NORM[next_m]) * frac
        rain_7d = rain_7d if rain_7d is not None else rain_mm

        FEST = {1:0.07, 8:0.06, 9:0.05, 10:0.09, 11:0.10, 12:0.04}

        def sc(peak, sharp=1.0):
            # Use day-of-year for sub-monthly precision
            fractional_month = m + (date.day - 1) / 30.0
            return float(max(0, np.cos(2 * np.pi * (fractional_month - peak) / 12 * sharp)))

        row = {
            "market_cat"          : mkt_val,
            "arrival_quantity_log": np.log1p(max(quantity, 0.1)),
            "qty_rolling_14d_log" : np.log1p(max(quantity, 0.1)),
            "temp_avg_c"          : temp_c,
            "precipitation_mm"    : rain_mm,
            "rain_7d_rolling"     : rain_7d,
            "month_sin"           : np.sin(2 * np.pi * doy / 365),    # use doy for sub-monthly smoothness
            "month_cos"           : np.cos(2 * np.pi * doy / 365),
            "doy_sin"             : np.sin(2 * np.pi * doy / 365),
            "doy_cos"             : np.cos(2 * np.pi * doy / 365),
            "week_sin"            : np.sin(2 * np.pi * wk / 52),
            "week_cos"            : np.cos(2 * np.pi * wk / 52),
            "year_trend"          : (date.year - 2021) / 4.0,
            "kharif_harvest"      : sc(12, 1.2),
            "rabi_harvest"        : sc(4,  1.5),
            "lean_kharif"         : sc(8,  1.2),
            "lean_inter"          : sc(2,  1.5),
            "pod_fill_window"     : sc(8.5, 2.0),
            "harvest_rain_risk"   : sc(10.5, 2.0),
            "oil_demand_kharif"   : sc(11, 1.5),
            "oil_demand_rabi"     : sc(4, 1.5),
            "festival_demand"     : FEST.get(m, 0.0),
            "lag_7"               : lag_7,
            "lag_30"              : lag_30,
            "lag_90"              : lag_90,
            "market_month_median" : mkt_med,
            "market_price_trend"  : 0.0,
            "price_spread"        : 500.0,
        }

        row_filtered = {k: row[k] for k in self.features if k in row}
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
        price_adj = max(price_adj, self.MSP_2025 * 0.85)

        revenue   = price_adj * quantity
        above_msp = price_adj >= self.MSP_2025

        if above_msp:
            msp_note = f"₹{price_adj - self.MSP_2025:,.0f} above MSP (₹{self.MSP_2025:,})"
        else:
            msp_note = f"⚠️ ₹{self.MSP_2025 - price_adj:,.0f} BELOW MSP (₹{self.MSP_2025:,})"

        m = date.month
        seasons = {
            (11, 12, 1): "Kharif harvest — supply glut, prices typically lower",
            (3, 4, 5)  : "Rabi harvest — secondary supply, moderate prices",
            (7, 8, 9)  : "Lean pre-Kharif — stocks depleting, prices rising",
            (2,)       : "Inter-season lean — prices firm",
            (6,)       : "Kharif sowing — market quiet",
        }
        season = "Post-harvest transition"
        for months, label in seasons.items():
            if m in months:
                season = label
                break

        decision = "GOVT_PROCUREMENT" if not above_msp else "SELL"

        return {
            "market"          : market,
            "date"            : date.strftime("%d %b %Y"),
            "predicted_price" : round(price_adj),
            "raw_price"       : round(raw),
            "bias_correction" : round(corr),
            "festival"        : fest_name,
            "festival_boost"  : boost,
            "msp_note"        : msp_note,
            "above_msp"       : above_msp,
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

        # Get initial lags from CSV
        if market in self.price_lags.index:
            lr = self.price_lags.loc[market]
            base_lag_7  = float(lr["p7d_ago"])
            base_lag_30 = float(lr["p30d_ago"])
            base_lag_90 = float(lr.get("p90d_ago", 6500.0))
        else:
            base_lag_7 = base_lag_30 = base_lag_90 = today_price

        # Rolling lag: blend CSV lag with predicted trajectory
        rolling_lag_7  = base_lag_7
        rolling_lag_30 = base_lag_30
        rolling_lag_90 = base_lag_90
        rolling_prices = [today_price]   # store all predicted prices

        forecast_list = []
        for i in range(1, days + 1):
            fd  = today + timedelta(days=i)

            # Build row with propagated lags
            row = self._build_feature_row(
                market, fd, quantity,
                lag_7_override=rolling_lag_7,
                lag_30_override=rolling_lag_30,
                lag_90_override=rolling_lag_90,
            )

            raw   = float(self.model.predict(row)[0])
            corr  = self.bias.get(fd.month, 0.0)
            price = max(raw + corr, self.MSP_2025 * 0.85)

            fn, fboost = self._festival_for(fd)
            price = price * (1 + fboost / 100)

            # Clamp overnight change to prevent unrealistic cliffs
            prev_price = rolling_prices[-1]
            max_delta  = prev_price * _MAX_DAILY_PCT / 100
            if abs(price - prev_price) > max_delta:
                direction = 1 if price > prev_price else -1
                price = prev_price + direction * max_delta

            rolling_prices.append(price)

            # Evolve the rolling lag: blend toward predicted trajectory
            # This prevents "frozen lag" flat forecasts
            alpha = 0.3  # 30% new prediction, 70% historical
            rolling_lag_7  = alpha * price + (1 - alpha) * rolling_lag_7
            rolling_lag_30 = alpha * price + (1 - alpha) * rolling_lag_30
            rolling_lag_90 = alpha * price + (1 - alpha) * rolling_lag_90

            forecast_list.append({
                "day"       : fd.strftime("%a %d %b"),
                "date"      : fd.strftime("%Y-%m-%d"),
                "price"     : round(price),
                "festival"  : fn,
                "above_msp" : price >= self.MSP_2025,
            })

        # Best sell day (with storage loss)
        best_day = {"day": "Today", "price": today_price,
                    "net_price": today_price, "gain_pct": 0.0}
        if storage_days > 0:
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
            "commodity"    : "Groundnut",
            "price_unit"   : "Rs. per quintal (100 kg)",
            "msp_floor"    : self.MSP_2025,
            "storage_loss" : f"{self.LOSS_PER_DAY}% per day",
            "markets"      : len(self.market_categories),
            "mae_inr"      : self.performance["MAE_inr"],
            "mape_pct"     : self.performance.get("MAPE_pct"),
            "built_at"     : self.performance["built_at"],
        }


# =============================================================
#  CoconutPredictor
# =============================================================
class CoconutPredictor:
    """
    Loads the coconut XGBoost model and artefacts.
    Adapted from GroundnutPredictor with coconut-specific features.
    """

    LOSS_PER_DAY = 0.40      # coconut spoilage: higher than groundnut

    def __init__(self, artefact_dir: str = None):
        if artefact_dir is None:
            artefact_dir = str(_BASE_DIR / "coconut" / "model_artefacts")

        logger.info(f"Loading coconut model from {artefact_dir} ...")
        self._load(artefact_dir)
        logger.info(
            f"✅ Coconut model ready — MAE ₹{self.performance['MAE_inr']:,}  "
            f"| {len(self.market_categories)} markets"
        )

    # ── Load artefacts ────────────────────────────────────────
    def _load(self, root: str):
        self.model = xgb.XGBRegressor()
        self.model.load_model(os.path.join(root, "coconut_price_model.json"))

        with open(os.path.join(root, "market_categories.json")) as f:
            self.market_categories = json.load(f)

        with open(os.path.join(root, "feature_list.json")) as f:
            meta = json.load(f)
            self.features = meta["features"]

        with open(os.path.join(root, "bias_correction.json")) as f:
            bc = json.load(f)
            self.bias = {int(k): v for k, v in bc["corrections"].items()}

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
        if market not in self.price_lags.index:
            return False
        row = self.price_lags.loc[market]
        try:
            latest = pd.to_datetime(row["latest_date"])
            return (datetime.now() - latest).days <= _STALE_DAYS
        except Exception:
            return False

    def fresh_markets(self) -> list:
        return sorted([m for m in self.market_categories if self._is_market_fresh(m)])

    # ── Interpolate market_month_median near month boundaries ─
    def _get_smoothed_median(self, market: str, date: datetime) -> float:
        import calendar
        m = date.month
        day = date.day
        days_in_month = calendar.monthrange(date.year, m)[1]

        mm_curr = self.mkt_medians[
            (self.mkt_medians["market"] == market) &
            (self.mkt_medians["month"]  == m)
        ]
        curr_med = float(mm_curr["median_price"].values[0]) if len(mm_curr) > 0 else None

        if curr_med is None:
            return 20000.0

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

    # ── Build one feature row (coconut-specific) ──────────────
    def _build_feature_row(self, market: str, date: datetime,
                           quantity: float,
                           temp_c: float = None,
                           rain_mm: float = None,
                           rain_7d: float = None,
                           lag_7_override: float = None,
                           lag_30_override: float = None) -> pd.DataFrame:
        m   = date.month
        doy = date.timetuple().tm_yday
        wk  = int(date.strftime("%W"))

        # Resolve market name
        if market in self.market_categories:
            mkt_val = market
        else:
            matches = [c for c in self.market_categories
                       if market.split()[0].lower() in c.lower()]
            mkt_val = matches[0] if matches else self.market_categories[0]

        # Lag prices — use overrides if provided
        if market in self.price_lags.index:
            lag_row  = self.price_lags.loc[market]
            lag_7    = float(lag_row["p7d_ago"])  if lag_7_override  is None else lag_7_override
            lag_30   = float(lag_row["p30d_ago"]) if lag_30_override is None else lag_30_override
        else:
            lag_7  = lag_7_override  or 20000.0
            lag_30 = lag_30_override or 20000.0

        # Market × month median — smoothed near boundaries
        mkt_med = self._get_smoothed_median(market, date)

        # Weather defaults — interpolated for smoother daily transitions
        TEMP_NORM = {1:24,2:26,3:28,4:30,5:30,6:27,7:26,8:26,9:27,10:27,11:25,12:24}
        RAIN_NORM = {1:2,2:2,3:3,4:10,5:20,6:120,7:150,8:130,9:80,10:60,11:15,12:5}
        if temp_c is None:
            next_m = (m % 12) + 1
            frac = date.day / 30.0
            temp_c = float(TEMP_NORM[m]) * (1 - frac) + float(TEMP_NORM[next_m]) * frac
        if rain_mm is None:
            next_m = (m % 12) + 1
            frac = date.day / 30.0
            rain_mm = float(RAIN_NORM[m]) * (1 - frac) + float(RAIN_NORM[next_m]) * frac
        rain_7d = rain_7d if rain_7d is not None else rain_mm

        # Festival demand factor for coconut
        FEST = {1:0.06, 3:0.05, 8:0.08, 9:0.06, 10:0.07, 11:0.09, 12:0.04}

        def sc(peak, sharp=1.0):
            # Use day-of-year for sub-monthly precision
            fractional_month = m + (date.day - 1) / 30.0
            return float(max(0, np.cos(2 * np.pi * (fractional_month - peak) / 12 * sharp)))

        row = {
            "market_cat"              : mkt_val,
            "arrival_quantity_log"    : np.log1p(max(quantity, 0.1)),
            "qty_rolling_14d_log"     : np.log1p(max(quantity, 0.1)),
            "temp_avg_c"              : temp_c,
            "precipitation_mm"        : rain_mm,
            "rain_7d_rolling"         : rain_7d,
            "month_sin"               : np.sin(2 * np.pi * doy / 365),
            "month_cos"               : np.cos(2 * np.pi * doy / 365),
            "doy_sin"                 : np.sin(2 * np.pi * doy / 365),
            "doy_cos"                 : np.cos(2 * np.pi * doy / 365),
            "week_sin"                : np.sin(2 * np.pi * wk / 52),
            "week_cos"                : np.cos(2 * np.pi * wk / 52),
            "year_trend"              : (date.year - 2021) / 4.0,
            # Coconut-specific seasonal signals (smooth cosine)
            "harvest_signal"          : sc(11, 1.0),
            "monsoon_signal"          : sc(7,  1.0),
            "summer_signal"           : sc(4,  1.0),
            "festival_demand_factor"  : FEST.get(m, 0.0),
            "price_lag_7"             : lag_7,
            "price_lag_30"            : lag_30,
            "market_month_median"     : mkt_med,
            "price_spread"            : 3000.0,
            "market_price_trend"      : 0.0,
        }

        row_filtered = {k: row[k] for k in self.features if k in row}
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
        price_adj = max(price_adj, 1000.0)  # soft floor for coconut

        revenue = price_adj * quantity

        # Coconut season context — corrected labels
        m = date.month
        seasons = {
            (10, 11, 12, 1, 2): "Harvest season — supply elevated, watch for dips",
            (3, 4, 5)         : "Post-harvest / Summer — supply easing, demand may rise",
            (6, 7, 8, 9)      : "Monsoon — reduced arrivals, prices typically higher",
        }
        season = "Transition period"
        for months, label in seasons.items():
            if m in months:
                season = label
                break

        return {
            "market"          : market,
            "date"            : date.strftime("%d %b %Y"),
            "predicted_price" : round(price_adj),
            "raw_price"       : round(raw),
            "bias_correction" : round(corr),
            "festival"        : fest_name,
            "festival_boost"  : boost,
            "season"          : season,
            "revenue"         : round(revenue),
            "quantity"        : quantity,
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

        # Get initial lags from CSV
        if market in self.price_lags.index:
            lr = self.price_lags.loc[market]
            base_lag_7  = float(lr["p7d_ago"])
            base_lag_30 = float(lr["p30d_ago"])
        else:
            base_lag_7 = base_lag_30 = today_price

        rolling_lag_7  = base_lag_7
        rolling_lag_30 = base_lag_30
        rolling_prices = [today_price]

        forecast_list = []
        for i in range(1, days + 1):
            fd  = today + timedelta(days=i)

            row = self._build_feature_row(
                market, fd, quantity,
                lag_7_override=rolling_lag_7,
                lag_30_override=rolling_lag_30,
            )

            raw   = float(self.model.predict(row)[0])
            corr  = self.bias.get(fd.month, 0.0)
            price = max(raw + corr, 1000.0)

            fn, fboost = self._festival_for(fd)
            price = price * (1 + fboost / 100)

            # Clamp overnight change to prevent unrealistic cliffs
            prev_price = rolling_prices[-1]
            max_delta  = prev_price * _MAX_DAILY_PCT / 100
            if abs(price - prev_price) > max_delta:
                direction = 1 if price > prev_price else -1
                price = prev_price + direction * max_delta

            rolling_prices.append(price)

            # Evolve rolling lags toward predicted trajectory
            alpha = 0.3
            rolling_lag_7  = alpha * price + (1 - alpha) * rolling_lag_7
            rolling_lag_30 = alpha * price + (1 - alpha) * rolling_lag_30

            forecast_list.append({
                "day"      : fd.strftime("%a %d %b"),
                "date"     : fd.strftime("%Y-%m-%d"),
                "price"    : round(price),
                "festival" : fn,
            })

        # Best sell day (with storage loss)
        best_day = {"day": "Today", "price": today_price,
                    "net_price": today_price, "gain_pct": 0.0}
        if storage_days > 0:
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
            "commodity"    : "Coconut",
            "price_unit"   : "Rs. per quintal (100 kg)",
            "storage_loss" : f"{self.LOSS_PER_DAY}% per day",
            "markets"      : len(self.market_categories),
            "mae_inr"      : self.performance["MAE_inr"],
            "mape_pct"     : self.performance.get("MAPE_pct"),
            "built_at"     : self.performance["built_at"],
        }


# =============================================================
#  PaddyPredictor
# =============================================================
class PaddyPredictor:
    """
    Loads the paddy (common) XGBoost model and artefacts.
    Paddy-specific features: kharif/rabi/summer arrival cycles,
    FCI procurement window, miller demand, harvest rain risk.
    """

    MSP_2025 = 2300           # Rs./quintal — MSP for common paddy
    MSP_GRADE_A = 2320        # Grade A paddy MSP
    LOSS_PER_DAY = 0.10       # % spoilage per day (dry storage)
    FCI_MONTHS = {11, 12, 1, 2, 3}  # FCI procurement window

    def __init__(self, artefact_dir: str = None):
        if artefact_dir is None:
            artefact_dir = str(_BASE_DIR / "paddy" / "paddy_model_artefacts")

        logger.info(f"Loading paddy model from {artefact_dir} ...")
        self._load(artefact_dir)
        logger.info(
            f"✅ Paddy model ready — MAE ₹{self.performance['MAE_inr']:,}  "
            f"| {len(self.market_categories)} markets"
        )

    # ── Load artefacts ────────────────────────────────────────
    def _load(self, root: str):
        self.model = xgb.XGBRegressor()
        self.model.load_model(os.path.join(root, "paddy_price_model.json"))

        with open(os.path.join(root, "market_categories.json")) as f:
            self.market_categories = json.load(f)

        with open(os.path.join(root, "feature_list.json")) as f:
            meta = json.load(f)
            self.features = meta["features"]

        with open(os.path.join(root, "bias_correction.json")) as f:
            bc = json.load(f)
            self.bias = {int(k): v for k, v in bc["corrections"].items()}

        self.mkt_medians = pd.read_csv(os.path.join(root, "market_month_medians.csv"))

        self.price_lags = pd.read_csv(
            os.path.join(root, "price_lags_latest.csv")
        ).set_index("market")

        with open(os.path.join(root, "model_performance.json")) as f:
            self.performance = json.load(f)

        with open(os.path.join(root, "festival_calendar.json")) as f:
            self.festivals = json.load(f)

    # ── Check data freshness ──────────────────────────────────
    def _is_market_fresh(self, market: str) -> bool:
        if market not in self.price_lags.index:
            return False
        row = self.price_lags.loc[market]
        try:
            latest = pd.to_datetime(row["latest_date"])
            return (datetime.now() - latest).days <= _STALE_DAYS
        except Exception:
            return False

    def fresh_markets(self) -> list:
        return sorted([m for m in self.market_categories if self._is_market_fresh(m)])

    # ── Interpolate market_month_median near month boundaries ─
    def _get_smoothed_median(self, market: str, date: datetime) -> float:
        import calendar
        m = date.month
        day = date.day
        days_in_month = calendar.monthrange(date.year, m)[1]

        mm_curr = self.mkt_medians[
            (self.mkt_medians["market"] == market) &
            (self.mkt_medians["month"]  == m)
        ]
        curr_med = float(mm_curr["median_price"].values[0]) if len(mm_curr) > 0 else None

        if curr_med is None:
            return 2300.0  # default = MSP

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

    # ── Build one feature row (paddy-specific) ────────────────
    def _build_feature_row(self, market: str, date: datetime,
                           quantity: float,
                           temp_c: float = None,
                           rain_mm: float = None,
                           rain_7d: float = None,
                           lag_7_override: float = None,
                           lag_30_override: float = None) -> pd.DataFrame:
        m   = date.month
        doy = date.timetuple().tm_yday
        wk  = int(date.strftime("%W"))

        # Resolve market name
        if market in self.market_categories:
            mkt_val = market
        else:
            matches = [c for c in self.market_categories
                       if market.split()[0].lower() in c.lower()]
            mkt_val = matches[0] if matches else self.market_categories[0]

        # Lag prices — use overrides if provided
        if market in self.price_lags.index:
            lag_row  = self.price_lags.loc[market]
            lag_7    = float(lag_row["p7d_ago"])  if lag_7_override  is None else lag_7_override
            lag_30   = float(lag_row["p30d_ago"]) if lag_30_override is None else lag_30_override
        else:
            lag_7  = lag_7_override  or 2300.0
            lag_30 = lag_30_override or 2300.0

        # Market × month median — smoothed near boundaries
        mkt_med = self._get_smoothed_median(market, date)

        # Weather defaults (Karnataka paddy belt)
        TEMP_NORM = {1:22,2:24,3:27,4:30,5:31,6:27,7:26,8:26,9:27,10:27,11:24,12:22}
        RAIN_NORM = {1:2,2:2,3:3,4:10,5:20,6:80,7:120,8:100,9:70,10:50,11:15,12:5}
        if temp_c is None:
            next_m = (m % 12) + 1
            frac = date.day / 30.0
            temp_c = float(TEMP_NORM[m]) * (1 - frac) + float(TEMP_NORM[next_m]) * frac
        if rain_mm is None:
            next_m = (m % 12) + 1
            frac = date.day / 30.0
            rain_mm = float(RAIN_NORM[m]) * (1 - frac) + float(RAIN_NORM[next_m]) * frac
        rain_7d = rain_7d if rain_7d is not None else rain_mm

        # Paddy-specific season signals (smooth cosine curves)
        fractional_month = m + (date.day - 1) / 30.0

        def sc(peak, sharp=1.0):
            return float(max(0, np.cos(2 * np.pi * (fractional_month - peak) / 12 * sharp)))

        # FCI procurement window: Nov-Mar (binary from feature_list notes)
        fci_procurement = 1.0 if m in self.FCI_MONTHS else 0.0

        # MSP pressure = year_trend × lean_preKharif
        year_trend = (date.year - 2021) / 4.0
        lean_pre_kharif = sc(9, 1.2)  # peaks Sep
        msp_pressure = year_trend * lean_pre_kharif

        row = {
            "market_cat"              : mkt_val,
            "arrival_quantity_log"    : np.log1p(max(quantity, 0.1)),
            "qty_rolling_14d_log"     : np.log1p(max(quantity, 0.1)),
            "temp_avg_c"              : temp_c,
            "precipitation_mm"        : rain_mm,
            "rain_7d_rolling"         : rain_7d,
            "month_sin"               : np.sin(2 * np.pi * doy / 365),
            "month_cos"               : np.cos(2 * np.pi * doy / 365),
            "doy_sin"                 : np.sin(2 * np.pi * doy / 365),
            "doy_cos"                 : np.cos(2 * np.pi * doy / 365),
            "week_sin"                : np.sin(2 * np.pi * wk / 52),
            "week_cos"                : np.cos(2 * np.pi * wk / 52),
            "year_trend"              : year_trend,
            # Paddy-specific season signals
            "kharif_arrival"          : sc(12, 1.2),   # peaks Dec — Nov-Jan glut
            "rabi_arrival"            : sc(3.5, 1.5),  # peaks late Mar
            "summer_arrival"          : sc(5.5, 1.5),  # peaks May-Jun
            "lean_preKharif"          : sc(9, 1.2),    # peaks Sep — highest price window
            "lean_interseason"        : sc(2.5, 1.5),  # peaks Feb-Mar
            "fci_procurement_window"  : fci_procurement,
            "miller_demand"           : sc(3, 1.5),    # peaks Mar — milling season
            "veg_stage_window"        : sc(8, 1.5),    # peaks Aug — vegetative rain risk
            "harvest_rain_risk"       : sc(11, 1.5),   # peaks Nov — wet grain discount
            "jan_drying_delay"        : sc(1, 2.0),    # peaks Jan — cold delays drying
            "msp_pressure"            : msp_pressure,
            "lag_7"                   : lag_7,
            "lag_30"                  : lag_30,
            "market_month_median"     : mkt_med,
            "market_price_trend"      : 0.0,
            "price_spread"            : 200.0,   # typical paddy spread
        }

        row_filtered = {k: row[k] for k in self.features if k in row}
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
        price_adj = max(price_adj, self.MSP_2025 * 0.80)  # soft floor

        revenue   = price_adj * quantity
        above_msp = price_adj >= self.MSP_2025

        if above_msp:
            msp_note = f"₹{price_adj - self.MSP_2025:,.0f} above MSP (₹{self.MSP_2025:,})"
        else:
            msp_note = f"⚠️ ₹{self.MSP_2025 - price_adj:,.0f} BELOW MSP (₹{self.MSP_2025:,})"

        # Season context for paddy
        m = date.month
        seasons = {
            (11, 12, 1)  : "Kharif harvest — supply glut, FCI procurement open, prices near MSP",
            (2, 3)       : "Post-kharif / Rabi — FCI still buying, mild uptick possible",
            (4, 5, 6)    : "Summer — low arrivals, prices may firm up",
            (7, 8)       : "Monsoon / Veg stage — rain risk, supplies low, prices rising",
            (9, 10)      : "Pre-kharif lean — highest price window, stocks depleting",
        }
        season = "Transition period"
        for months, label in seasons.items():
            if m in months:
                season = label
                break

        # FCI procurement note
        fci_note = None
        if m in self.FCI_MONTHS:
            fci_note = "FCI procurement window open — check local procurement center"

        decision = "GOVT_PROCUREMENT" if not above_msp else "SELL"

        return {
            "market"          : market,
            "date"            : date.strftime("%d %b %Y"),
            "predicted_price" : round(price_adj),
            "raw_price"       : round(raw),
            "bias_correction" : round(corr),
            "festival"        : fest_name,
            "festival_boost"  : boost,
            "msp_note"        : msp_note,
            "above_msp"       : above_msp,
            "season"          : season,
            "fci_note"        : fci_note,
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

        # Get initial lags from CSV
        if market in self.price_lags.index:
            lr = self.price_lags.loc[market]
            base_lag_7  = float(lr["p7d_ago"])
            base_lag_30 = float(lr["p30d_ago"])
        else:
            base_lag_7 = base_lag_30 = today_price

        rolling_lag_7  = base_lag_7
        rolling_lag_30 = base_lag_30
        rolling_prices = [today_price]

        forecast_list = []
        for i in range(1, days + 1):
            fd  = today + timedelta(days=i)

            row = self._build_feature_row(
                market, fd, quantity,
                lag_7_override=rolling_lag_7,
                lag_30_override=rolling_lag_30,
            )

            raw   = float(self.model.predict(row)[0])
            corr  = self.bias.get(fd.month, 0.0)
            price = max(raw + corr, self.MSP_2025 * 0.80)

            fn, fboost = self._festival_for(fd)
            price = price * (1 + fboost / 100)

            # Clamp overnight change
            prev_price = rolling_prices[-1]
            max_delta  = prev_price * _MAX_DAILY_PCT / 100
            if abs(price - prev_price) > max_delta:
                direction = 1 if price > prev_price else -1
                price = prev_price + direction * max_delta

            rolling_prices.append(price)

            # Evolve rolling lags
            alpha = 0.3
            rolling_lag_7  = alpha * price + (1 - alpha) * rolling_lag_7
            rolling_lag_30 = alpha * price + (1 - alpha) * rolling_lag_30

            forecast_list.append({
                "day"       : fd.strftime("%a %d %b"),
                "date"      : fd.strftime("%Y-%m-%d"),
                "price"     : round(price),
                "festival"  : fn,
                "above_msp" : price >= self.MSP_2025,
            })

        # Best sell day (with storage loss)
        best_day = {"day": "Today", "price": today_price,
                    "net_price": today_price, "gain_pct": 0.0}
        if storage_days > 0:
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
            "commodity"    : "Paddy (Common)",
            "price_unit"   : "Rs. per quintal (100 kg)",
            "msp_floor"    : self.MSP_2025,
            "storage_loss" : f"{self.LOSS_PER_DAY}% per day (dry)",
            "markets"      : len(self.market_categories),
            "mae_inr"      : self.performance["MAE_inr"],
            "mape_pct"     : self.performance.get("MAPE_pct"),
            "built_at"     : self.performance["built_at"],
        }


# =============================================================
#  KarnatakaForecaster  — singleton manager
# =============================================================
class KarnatakaForecaster:
    """
    Lazy-loads groundnut, coconut, and paddy predictors once at first use.
    Provides a unified entry point for the rest of the app.
    """

    _groundnut: GroundnutPredictor = None
    _coconut:   CoconutPredictor   = None
    _paddy:     PaddyPredictor     = None

    # Which crops are supported by Karnataka-specific models
    SUPPORTED_CROPS = {"groundnut", "coconut", "paddy", "rice", "paddy (common)"}

    @classmethod
    def _normalize_crop(cls, crop: str) -> str:
        """Normalize crop name to canonical form."""
        crop_l = crop.lower().strip()
        if crop_l in ("paddy", "rice", "paddy (common)"):
            return "paddy"
        return crop_l

    @classmethod
    def _ensure_loaded(cls, crop: str):
        crop_l = cls._normalize_crop(crop)
        if crop_l == "groundnut" and cls._groundnut is None:
            cls._groundnut = GroundnutPredictor()
        elif crop_l == "coconut" and cls._coconut is None:
            cls._coconut = CoconutPredictor()
        elif crop_l == "paddy" and cls._paddy is None:
            cls._paddy = PaddyPredictor()

    @classmethod
    def _predictor(cls, crop: str):
        crop_l = cls._normalize_crop(crop)
        cls._ensure_loaded(crop_l)
        if crop_l == "groundnut":
            return cls._groundnut
        elif crop_l == "coconut":
            return cls._coconut
        elif crop_l == "paddy":
            return cls._paddy
        return None

    @classmethod
    def is_supported(cls, state: str, crop: str) -> bool:
        """Check if this crop should use Karnataka models based on user location."""
        if not state or not crop:
            return False
        return (
            state.lower().strip() in ("karnataka", "ka", "maharashtra", "mh")
            and cls._normalize_crop(crop) in {"groundnut", "coconut", "paddy"}
        )

    @classmethod
    def get_forecast(cls, crop: str, market: str,
                     quantity: float = 10.0) -> dict:
        """
        Returns a dict with:
          - today         : today's prediction
          - forecast_7day : list of 7 daily predictions
          - day_30        : 30th-day prediction
          - trend_7d_pct  : 7-day trend %
          - best_day      : storage-optimal sell day
          - model_info    : model metadata
          - available_markets : sorted market list
          - fresh_markets     : markets with recent data only
        """
        predictor = cls._predictor(crop)
        if predictor is None:
            return None

        # 7-day forecast
        fc7 = predictor.forecast(market, days=7, quantity=quantity,
                                 storage_days=30)

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
