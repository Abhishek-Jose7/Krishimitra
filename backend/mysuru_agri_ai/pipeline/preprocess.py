import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler


logger = logging.getLogger(__name__)


def _ensure_datetime(df: pd.DataFrame, column: str) -> pd.Series:
    if not np.issubdtype(df[column].dtype, np.datetime64):
        df[column] = pd.to_datetime(df[column], errors="coerce")
    return df[column]


def map_month_to_season(month: int) -> str:
    """Map Gregorian month to Indian agricultural season label."""
    if month in (6, 7, 8, 9):
        return "Kharif"
    if month in (10, 11):
        return "Rabi"
    if month in (12, 1, 2, 3):
        return "Rabi"
    return "Summer"


def load_weather_data(path: Path, district: str = "Mysuru") -> pd.DataFrame:
    """
    Load and clean daily weather data, aggregating to seasonal features.

    The file is expected to contain at least:
    - datetime
    - temp
    - humidity
    - precip
    - cloudcover
    - windspeed
    - solarradiation
    """
    logger.info("Loading weather data from %s", path)
    df = pd.read_csv(path)

    # Normalise column names for case-insensitive matching
    original_cols = list(df.columns)
    lower_map = {c.lower().strip(): c for c in df.columns}

    # Resolve datetime-like column
    datetime_col = None
    for cand in ("datetime", "date", "time"):
        if cand in lower_map:
            datetime_col = lower_map[cand]
            break
    if datetime_col is None:
        raise ValueError(
            "Weather dataset must contain a datetime/date column; "
            f"available columns: {original_cols}"
        )

    _ensure_datetime(df, datetime_col)
    df["year"] = df[datetime_col].dt.year
    df["month"] = df[datetime_col].dt.month
    df["Season"] = df["month"].apply(map_month_to_season)

    # Resolve core numeric fields with flexible naming
    def resolve(name_candidates):
        # First try exact lower-case matches
        for cand in name_candidates:
            if cand in lower_map:
                return lower_map[cand]
        # Then try substring matches such as "temp" in "temp_avg"
        for cand in name_candidates:
            for key, orig in lower_map.items():
                if cand in key:
                    return orig
        return None

    temp_col = resolve(["temp", "temperature", "tempavg", "temp_avg"])
    tempmax_col = resolve(["tempmax", "temp_max", "tmax", "max_temp"])
    humid_col = resolve(["humidity", "hum", "relhumidity"])
    precip_col = resolve(["precip", "rain", "rainfall"])
    wind_col = resolve(["windspeed", "wind_speed", "wind"])
    solar_col = resolve(["solarradiation", "solar_radiation", "solar", "radiation"])

    missing = [
        name
        for name, col in [
            ("temp", temp_col),
            ("humidity", humid_col),
            ("precip", precip_col),
            ("windspeed", wind_col),
            ("solarradiation", solar_col),
        ]
        if col is None
    ]

    # If some expected weather attributes are absent (e.g. humidity, windspeed,
    # solar radiation), EXCLUDE them rather than creating synthetic constant
    # columns that add zero signal but noise to the model.
    if missing:
        logger.warning(
            "Weather dataset is missing columns %s — they will be excluded "
            "from features (not synthesised). Available columns: %s",
            missing,
            original_cols,
        )

        # Ensure we at least have temperature and rainfall; otherwise fail fast.
        if temp_col is None or precip_col is None:
            raise KeyError(
                "Weather dataset must contain at least a temperature and rainfall "
                f"column. Available columns: {original_cols}"
            )

    # Basic cleaning — only require columns that actually exist
    df = df.drop_duplicates()
    required_cols = [c for c in [temp_col, humid_col, precip_col, wind_col, solar_col] if c is not None]
    df = df.dropna(subset=required_cols, how="any")

    # Build aggregation dict from available columns only
    agg_dict = {
        "avg_temp": (temp_col, "mean"),
        "total_rainfall": (precip_col, "sum"),
        "rainfall_variability": (precip_col, "std"),
    }
    if humid_col is not None:
        agg_dict["avg_humidity"] = (humid_col, "mean")
    if solar_col is not None:
        agg_dict["avg_solar_radiation"] = (solar_col, "mean")
    if wind_col is not None:
        agg_dict["avg_windspeed"] = (wind_col, "mean")

    seasonal = (
        df.groupby(["year", "Season"], as_index=False)
        .agg(**agg_dict)
        .reset_index(drop=True)
    )

    # Extreme heat days (>35C) using temp_max if present, else avg temp.
    heat_source = tempmax_col if tempmax_col is not None else temp_col
    heat_days = (
        df.assign(_hot=(df[heat_source] > 35.0).astype(int))
        .groupby(["year", "Season"], as_index=False)["_hot"]
        .sum()
        .rename(columns={"_hot": "extreme_heat_days"})
    )
    seasonal = seasonal.merge(heat_days, on=["year", "Season"], how="left")
    seasonal["rainfall_variability"] = seasonal["rainfall_variability"].fillna(0.0)
    seasonal["extreme_heat_days"] = seasonal["extreme_heat_days"].fillna(0.0)

    # Label district and provide "seasonal_*" aliases.
    seasonal["district"] = str(district).strip().title() if district else "Unknown"
    seasonal = seasonal.rename(
        columns={
            "total_rainfall": "seasonal_rainfall_total",
            "avg_humidity": "seasonal_avg_humidity",
        }
    )
    # Backward-compatible aliases
    seasonal["total_rainfall"] = seasonal["seasonal_rainfall_total"]
    seasonal["avg_humidity"] = seasonal["seasonal_avg_humidity"]

    logger.info("Built seasonal weather features with %d rows. Columns: %s", len(seasonal), seasonal.columns.tolist())
    return seasonal


def load_crop_management_data(path: Path, district: str = "Mysuru") -> pd.DataFrame:
    """
    Load crop + management + yield dataset and filter for the given district.

    The dataset is expected to contain:
    - Area (location or district; filtered to Mysuru / Mysore)
    - Rainfall
    - Temperature
    - Soil type
    - Irrigation
    - Humidity
    - Crops
    - Season
    - yeilds
    """
    logger.info("Loading crop management data from %s", path)
    df = pd.read_csv(path)

    # Normalise column names for robustness
    df.columns = [c.strip() for c in df.columns]

    # Filter by district using the Location column when present.
    filtered = df.copy()
    if "Location" in filtered.columns and district:
        mask = filtered["Location"].astype(str).str.contains(district, case=False, na=False)
        matched = filtered.loc[mask].copy()
        if matched.empty:
            logger.warning(
                "No rows matched district '%s' in Location; using full dataset.", district
            )
        else:
            filtered = matched

    filtered = filtered.drop_duplicates()
    filtered = filtered.dropna(subset=["Crops", "Season", "yeilds", "Area"], how="any")

    # Normalise naming for key categoricals
    for col in ("Crops", "Season", "Soil type", "Irrigation"):
        if col in filtered.columns:
            filtered[col] = filtered[col].astype(str).str.strip().str.title()

    # District feature for multi-district learning/prediction
    filtered["district"] = str(district).strip().title() if district else "Unknown"

    return filtered


def load_crop_management_all(path: Path) -> pd.DataFrame:
    """
    Load crop + management + yield dataset for all locations and infer `district`
    from the `Location` column (if present). This enables training district-specific
    models without hardcoding district names.
    """
    logger.info("Loading crop management data (all districts) from %s", path)
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]

    df = df.drop_duplicates()
    df = df.dropna(subset=["Crops", "Season", "yeilds", "Area"], how="any")

    for col in ("Crops", "Season", "Soil type", "Irrigation"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.title()

    if "Location" in df.columns:
        df["district"] = df["Location"].astype(str).str.strip().str.title()
    else:
        df["district"] = "Unknown"

    return df


def load_pune_nutrient_features(path: Path) -> pd.DataFrame:
    """
    Load Pune Nutrient.csv and convert sufficiency counts into numeric indices.

    Returns a district-level nutrient feature table with columns:
    district, N, P, K, ph

    Note: the source file provides sufficiency counts (High/Medium/Low) rather
    than raw soil test values; we convert them into 0-100 indices and a coarse
    pH estimate.
    """
    logger.info("Loading Pune nutrient data from %s", path)
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]

    required = {
        "District",
        "n_High", "n_Medium", "n_Low",
        "p_High", "p_Medium", "p_Low",
        "k_High", "k_Medium", "k_Low",
        "pH_Alkaline", "pH_Acidic", "pH_Neutral",
    }
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Nutrient.csv is missing columns: {missing}")

    def _idx(high: pd.Series, med: pd.Series, low: pd.Series) -> pd.Series:
        total = (high + med + low).replace(0, np.nan)
        return ((high * 1.0 + med * 0.5 + low * 0.0) / total) * 100.0

    df["district"] = df["District"].astype(str).str.strip().str.title()
    df["N"] = _idx(df["n_High"], df["n_Medium"], df["n_Low"])
    df["P"] = _idx(df["p_High"], df["p_Medium"], df["p_Low"])
    df["K"] = _idx(df["k_High"], df["k_Medium"], df["k_Low"])

    ph_total = (df["pH_Acidic"] + df["pH_Neutral"] + df["pH_Alkaline"]).replace(0, np.nan)
    df["ph"] = (
        (df["pH_Acidic"] * 6.0 + df["pH_Neutral"] * 7.0 + df["pH_Alkaline"] * 8.0)
        / ph_total
    )

    out = (
        df.groupby("district", as_index=False)[["N", "P", "K", "ph"]]
        .mean()
        .reset_index(drop=True)
    )
    return out


def load_pune_soil_types(path: Path) -> pd.DataFrame:
    """
    Load Pune taluka soil types and return a mapping table:
    Taluka -> Soil type (dominant).
    """
    logger.info("Loading Pune soil types from %s", path)
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    if not {"Taluka", "Dominant_Soil_Type"}.issubset(df.columns):
        raise ValueError("pune_taluka_soil_types.csv must contain Taluka and Dominant_Soil_Type.")
    df["Taluka"] = df["Taluka"].astype(str).str.strip().str.title()
    df["Soil type"] = df["Dominant_Soil_Type"].astype(str).str.strip()
    return df[["Taluka", "Soil type"]].drop_duplicates().reset_index(drop=True)


def load_pune_yield_labels(data_dir: Path) -> pd.DataFrame:
    """
    Optional: load Pune yield labels for district-specific model training.

    Expected location:
      - data/pune_yield_season.csv  (preferred)
      - data/pune_yield.csv         (fallback)

    Minimum required columns (case-insensitive):
      - Area
      - yeilds  (or yields/production)
      - Crops
      - Season
      - Irrigation

    Optional:
      - Year (recommended for weather join)
      - Taluka (for soil type join via pune_taluka_soil_types.csv)
      - Soil type (if already present)

    Returns an empty DataFrame if no file is present.
    """
    candidates = [
        data_dir / "pune_yield_season.csv",
        data_dir / "pune_yield.csv",
    ]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        return pd.DataFrame()

    logger.info("Loading Pune yield labels from %s", path)
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    lower_map = {c.lower().strip(): c for c in df.columns}

    def col(*names: str) -> str | None:
        for n in names:
            if n.lower() in lower_map:
                return lower_map[n.lower()]
        # substring match
        for n in names:
            for k, orig in lower_map.items():
                if n.lower() in k:
                    return orig
        return None

    area_col = col("area")
    yield_col = col("yeilds", "yields", "production")
    crops_col = col("crops", "crop")
    season_col = col("season")
    irrigation_col = col("irrigation")
    year_col = col("year")
    taluka_col = col("taluka", "block")
    soil_col = col("soil type", "soil_type", "soil")

    missing = [n for n, c_ in [("Area", area_col), ("yeilds", yield_col), ("Crops", crops_col), ("Season", season_col), ("Irrigation", irrigation_col)] if c_ is None]
    if missing:
        raise ValueError(
            f"Pune yield labels file {path.name} is missing required columns: {missing}. "
            f"Found columns: {list(df.columns)}"
        )

    out = pd.DataFrame(
        {
            "Area": df[area_col],
            "yeilds": df[yield_col],
            "Crops": df[crops_col],
            "Season": df[season_col],
            "Irrigation": df[irrigation_col],
        }
    )
    if year_col is not None:
        out["Year"] = df[year_col]
    if taluka_col is not None:
        out["Taluka"] = df[taluka_col].astype(str).str.strip().str.title()
    if soil_col is not None:
        out["Soil type"] = df[soil_col].astype(str).str.strip()

    # If soil type is missing but Taluka is available, merge from soil types table.
    if "Soil type" not in out.columns and "Taluka" in out.columns:
        soil_path = data_dir / "pune_taluka_soil_types.csv"
        if soil_path.exists():
            soil_map = load_pune_soil_types(soil_path)
            out = out.merge(soil_map, on="Taluka", how="left")

    # Standardize district + categoricals
    out["district"] = "Pune"
    for c in ("Crops", "Season", "Soil type", "Irrigation"):
        if c in out.columns:
            out[c] = out[c].astype(str).str.strip().str.title()

    out = out.drop_duplicates()
    out = out.dropna(subset=["Area", "yeilds", "Crops", "Season", "Irrigation"], how="any")
    return out


def load_soil_nutrient_data(path: Path) -> pd.DataFrame:
    """
    Load soil nutrient dataset and aggregate typical nutrient profile per crop.

    The dataset is expected to contain:
    - N, P, K, temperature, humidity, ph, rainfall, label
    """
    logger.info("Loading soil nutrient data from %s", path)
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]

    if "label" not in df.columns:
        raise ValueError("Soil nutrient dataset must contain a 'label' column.")

    df["label"] = df["label"].astype(str).str.strip().str.title()
    nutrient_means = (
        df.groupby("label", as_index=False)[["N", "P", "K", "ph", "rainfall"]]
        .mean()
        .rename(columns={"label": "Crops", "rainfall": "nutrient_rainfall"})
    )
    return nutrient_means


@dataclass
class FeatureSpec:
    numeric_features: List[str]
    categorical_features: List[str]


def build_feature_matrix(
    weather_seasonal: pd.DataFrame,
    crop_mgmt: pd.DataFrame,
    soil_nutrients: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.Series, FeatureSpec, Dict]:
    """
    Merge weather, management, and soil nutrient datasets into a single
    feature matrix and target vector.
    """
    logger.info("Merging seasonal weather with crop management and soil nutrients.")

    # Merge weather onto crop management by district/year/season when available.
    if weather_seasonal.empty or "Season" not in weather_seasonal.columns:
        logger.warning("No weather data available to merge; proceeding with management features only.")
        merged = crop_mgmt.copy()
    else:
        # Pre-merge check for join keys
        weather_keys = ["district", "year", "Season"]
        crop_keys = ["district", "Year", "Season"]
        
        if (
            all(k in weather_seasonal.columns for k in weather_keys)
            and all(k in crop_mgmt.columns for k in crop_keys)
        ):
            merged = pd.merge(
                crop_mgmt,
                weather_seasonal,
                left_on=crop_keys,
                right_on=weather_keys,
                how="left",
                suffixes=("_mgmt", "_sensor") # ── PHASE 3 FIX 1: Resolve Conflicts ──
            )
        else:
            # Fallback to season-only merge if district/year columns are missing
            merged = pd.merge(
                crop_mgmt, 
                weather_seasonal, 
                on="Season", 
                how="left",
                suffixes=("_mgmt", "_sensor")
            )

        # ── PHASE 3 FIX 2: Feature Coalescing ──
        # data_season.csv already contains base climate data (mgmt). 
        # External sensor files (sensor) provide bonus features.
        # Merge them so that Sensor > Mgmt.
        COALESCE_MAP = {
            "Rainfall": "Rainfall_sensor",
            "Temperature": "Temperature_sensor",
            "Humidity": "Humidity_sensor"
        }
        
        for base_col, sensor_col in COALESCE_MAP.items():
            mgmt_col = f"{base_col}_mgmt"
            if sensor_col in merged.columns and mgmt_col in merged.columns:
                # Use sensor data if present, else fallback to management CSV data
                merged[base_col] = merged[sensor_col].fillna(merged[mgmt_col])
                # Drop the temporary conflict columns
                merged.drop(columns=[sensor_col, mgmt_col], inplace=True)
            elif mgmt_col in merged.columns:
                merged.rename(columns={mgmt_col: base_col}, inplace=True)
            elif sensor_col in merged.columns:
                merged.rename(columns={sensor_col: base_col}, inplace=True)

        # ── INTER-PHASE FIX 2: Regional Weather Proxy ──
        # If a row has no weather data (because of missing district files),
        # fill it with the mean weather across ALL OTHER districts for that Year/Season.
        # This provides a "monsoon proxy" which is better than a global median.
        weather_cols = ["Rainfall", "Temperature", "Humidity", "avg_temp", 
                        "total_rainfall", "avg_humidity", "avg_solar_radiation", 
                        "avg_windspeed", "rainfall_variability"]
        
        # Identify columns that exist in merged and are likely from weather sensor
        weather_cols = [c for c in weather_cols if c in merged.columns]
        
        if weather_cols:
            # Group by year/season across all districts to find the regional "norm"
            regional_weather = (
                weather_seasonal.groupby(["year", "Season"])[weather_cols]
                .mean().reset_index()
            )
            
            if not regional_weather.empty:
                # Merge regional norm as secondary backup
                merged = pd.merge(
                    merged, 
                    regional_weather, 
                    left_on=["Year", "Season"], 
                    right_on=["year", "Season"], 
                    how="left",
                    suffixes=("", "_regional")
                )
                
                # Fill gaps using the regional norm
                for col in weather_cols:
                    regional_col = f"{col}_regional"
                    if regional_col in merged.columns:
                        merged[col] = merged[col].fillna(merged[col_regional])
                        merged.drop(columns=[regional_col], inplace=True)
                
                if "year_regional" in merged.columns:
                    merged.drop(columns=["year_regional"], inplace=True)

    # Merge soil/nutrient features by crop when available, else by district.
    if "Crops" in soil_nutrients.columns:
        merged = pd.merge(merged, soil_nutrients, on="Crops", how="left")
    elif "district" in soil_nutrients.columns:
        merged = pd.merge(merged, soil_nutrients, on="district", how="left")

    # Ensure district exists as a feature.
    if "district" not in merged.columns:
        merged["district"] = "Unknown"

    # ── PHASE 2 FIX: Target Normalization (Relative Yield Index) ──
    # Yields often have wildly different units/magnitudes (Coconut nuts ~10K 
    # vs Paddy tons ~2). Predictive indices (actual / median_for_crop) allow 
    # the model to learn universal patterns.
    
    # First calculate raw yield per area
    # Calculate raw yield per area
    if "Area" in merged.columns:
        merged["yield_per_area"] = merged["yeilds"] / merged["Area"].replace(0, np.nan)
    else:
        merged["yield_per_area"] = merged["yeilds"]
    
    merged = merged.dropna(subset=["yield_per_area"])

    # ── PHASE 2.1 FIX: Robust Normalization ──
    # Aggressively filter outliers BEFORE calculating medians to avoid skew.
    def filter_crop_outliers(group):
        if len(group) < 5: return group
        q_low = group["yield_per_area"].quantile(0.01)
        q_high = group["yield_per_area"].quantile(0.95) # Drop top 5% extreme outliers
        return group[group["yield_per_area"].between(q_low, q_high)]

    cleaned_for_median = merged.groupby("Crops", group_keys=False).apply(filter_crop_outliers)
    crop_medians = cleaned_for_median.groupby("Crops")["yield_per_area"].median().to_dict()
    
    # Apply normalization: RYI = yield_per_area / crop_median
    merged["yield_index"] = merged.apply(
        lambda r: r["yield_per_area"] / crop_medians.get(r["Crops"], 1.0) 
        if pd.notna(r["yield_per_area"]) and r["Crops"] in crop_medians else np.nan,
        axis=1
    )

    # Drop rows without a valid target
    merged = merged.dropna(subset=["yield_index"])

    # Filter out remaining relative outliers (e.g. data errors)
    valid_mask = merged["yield_index"].between(0.01, 10.0)
    merged = merged.loc[valid_mask].copy()

    # ── FIX 3: Stable ratio-based interaction features ──
    # Replace raw product features (rain_temp ~ 170,000) with normalised ratios
    # that have agronomic meaning.
    if {"Rainfall", "Temperature"}.issubset(merged.columns):
        merged["rain_per_degree"] = merged["Rainfall"] / merged["Temperature"].replace(0, np.nan)
        merged["rain_per_degree"] = merged["rain_per_degree"].fillna(0.0)
    if {"Temperature", "Humidity"}.issubset(merged.columns):
        # Vapour-pressure-deficit proxy: high temp + low humidity = stress
        merged["heat_stress_index"] = merged["Temperature"] * (100 - merged["Humidity"]) / 100.0

    # ── FIX 1: Explicit feature whitelist ──
    # Only include features that would be KNOWN at prediction time.
    # Excludes: price (leakage), year/Year (overfitting to time), Location,
    #           season_crop (redundant with separate Season + Crops categoricals),
    #           and any other metadata columns.
    NUMERIC_WHITELIST = {
        # Climate features
        "Rainfall", "Temperature", "Humidity",
        # Seasonal weather aggregates
        "avg_temp", "seasonal_rainfall_total", "seasonal_avg_humidity",
        "avg_solar_radiation", "avg_windspeed", "rainfall_variability",
        "extreme_heat_days", "total_rainfall", "avg_humidity",
        # Soil nutrient features
        "N", "P", "K", "ph", "nutrient_rainfall",
        # Interaction features (ratio-based)
        "rain_per_degree", "heat_stress_index",
    }

    numeric_cols = [
        col for col in merged.select_dtypes(include=[np.number]).columns
        if col in NUMERIC_WHITELIST
    ]

    numeric_means: Dict[str, float] = {}
    for col in numeric_cols:
        merged[col] = merged[col].fillna(merged[col].median())
        numeric_means[col] = float(merged[col].mean())

    # Minimal rainfall statistics for later risk analysis.
    rainfall_cols = [c for c in numeric_cols if "rainfall" in c.lower() or "rain" in c.lower()]
    rainfall_stats = {}
    for col in rainfall_cols:
        rainfall_stats[col] = {
            "mean": float(merged[col].mean()),
            "std": float(merged[col].std(ddof=1) if merged[col].std(ddof=1) > 0 else 0.0),
        }

    categorical_features = [
        col
        for col in ["district", "Crops", "Season", "Soil type", "Irrigation"]
        if col in merged.columns
    ]

    # Build X by selecting ONLY whitelisted features + categoricals.
    keep_cols = numeric_cols + categorical_features
    # Ensure all kept columns exist
    keep_cols = [c for c in keep_cols if c in merged.columns]
    y = merged["yield_index"].astype(float)
    X = merged[keep_cols].copy()

    feature_spec = FeatureSpec(
        numeric_features=numeric_cols,
        categorical_features=categorical_features,
    )

    metadata = {
        "created_at": datetime.utcnow().isoformat(),
        "feature_spec": {
            "numeric": feature_spec.numeric_features,
            "categorical": feature_spec.categorical_features,
        },
        "rainfall_stats": rainfall_stats,
        "numeric_means": numeric_means,
        "crop_medians": crop_medians,
    }

    return X, y, feature_spec, metadata


def build_district_reference_tables(data_dir: Path) -> Dict:
    """
    Build reference lookups used at simulation time to enrich scenarios with
    district-season weather and district-level nutrient defaults.
    """
    refs: Dict = {"weather_by_district_season": {}, "nutrients_by_district": {}}

    # Weather references: discover weather CSVs in data_dir.
    weather_candidates = list(sorted(data_dir.glob("*weather*.csv")))
    # Also include known Mysuru file naming used in this project.
    mysuru_known = data_dir / "mysore2021-.csv"
    if mysuru_known.exists() and mysuru_known not in weather_candidates:
        weather_candidates.append(mysuru_known)

    for p in weather_candidates:
        name = p.stem.lower()
        if "pune" in name:
            district = "Pune"
        elif "mysore" in name or "mysuru" in name:
            district = "Mysuru"
        else:
            district = p.stem.split("_")[0].strip().title()

        try:
            w = load_weather_data(p, district=district)
        except Exception:
            continue

        w = w.groupby("Season", as_index=False).agg(
            Temperature=("avg_temp", "mean"),
            Rainfall=("seasonal_rainfall_total", "mean"),
            Humidity=("seasonal_avg_humidity", "mean"),
            seasonal_rainfall_total=("seasonal_rainfall_total", "mean"),
            rainfall_variability=("rainfall_variability", "mean"),
            extreme_heat_days=("extreme_heat_days", "mean"),
            seasonal_avg_humidity=("seasonal_avg_humidity", "mean"),
        )

        refs["weather_by_district_season"][district] = {
            r["Season"]: {
                "Temperature": float(r["Temperature"]),
                "Rainfall": float(r["Rainfall"]),
                "Humidity": float(r["Humidity"]),
                "seasonal_rainfall_total": float(r["seasonal_rainfall_total"]),
                "rainfall_variability": float(r["rainfall_variability"]),
                "extreme_heat_days": float(r["extreme_heat_days"]),
                "seasonal_avg_humidity": float(r["seasonal_avg_humidity"]),
            }
            for _, r in w.iterrows()
        }

    # Pune nutrient reference
    pune_nutrient_path = data_dir / "Nutrient.csv"
    if pune_nutrient_path.exists():
        n = load_pune_nutrient_features(pune_nutrient_path)
        refs["nutrients_by_district"].update(
            {r["district"]: {"N": float(r["N"]), "P": float(r["P"]), "K": float(r["K"]), "ph": float(r["ph"])} for _, r in n.iterrows()}
        )

    return refs


def build_preprocessor(feature_spec: FeatureSpec) -> ColumnTransformer:
    """
    Build a ColumnTransformer that scales numeric features and one-hot encodes
    categorical features.
    """
    transformers = []
    if feature_spec.numeric_features:
        transformers.append(
            (
                "num",
                StandardScaler(),
                feature_spec.numeric_features,
            )
        )
    if feature_spec.categorical_features:
        transformers.append(
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore"),
                feature_spec.categorical_features,
            )
        )
    preprocessor = ColumnTransformer(transformers=transformers)
    return preprocessor


def save_metadata(metadata: Dict, models_dir: Path, version: str) -> None:
    """
    Persist training metadata and feature configuration for reproducibility.
    """
    models_dir.mkdir(parents=True, exist_ok=True)
    meta = metadata.copy()
    meta["version"] = version
    meta_path = models_dir / f"metadata_{version}.json"
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    # Also keep a canonical metadata.json pointer to latest
    latest = models_dir / "metadata.json"
    latest.write_text(meta_path.read_text(encoding="utf-8"), encoding="utf-8")

