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
    # solar radiation), synthesise reasonable constant columns so that the rest
    # of the pipeline can still operate, and log a warning for transparency.
    if missing:
        logger.warning(
            "Weather dataset is missing expected columns %s. "
            "Synthetic constant columns will be created; model performance may "
            "be limited by lack of variability in these features. Available "
            "columns: %s",
            missing,
            original_cols,
        )

        # Ensure we at least have temperature and rainfall; otherwise fail fast.
        if temp_col is None or precip_col is None:
            raise KeyError(
                "Weather dataset must contain at least a temperature and rainfall "
                f"column. Available columns: {original_cols}"
            )

        # Use rainfall mean as a generic magnitude for missing weather metrics.
        default_val = float(df[precip_col].mean())

        if humid_col is None:
            humid_col = "humidity_synth"
            df[humid_col] = default_val
        if wind_col is None:
            wind_col = "windspeed_synth"
            df[wind_col] = default_val
        if solar_col is None:
            solar_col = "solarradiation_synth"
            df[solar_col] = default_val

    # Basic cleaning
    df = df.drop_duplicates()
    df = df.dropna(
        subset=[temp_col, humid_col, precip_col, wind_col, solar_col],
        how="any",
    )

    seasonal = (
        df.groupby(["year", "Season"], as_index=False)
        .agg(
            avg_temp=(temp_col, "mean"),
            total_rainfall=(precip_col, "sum"),
            avg_humidity=(humid_col, "mean"),
            avg_solar_radiation=(solar_col, "mean"),
            avg_windspeed=(wind_col, "mean"),
        )
        .reset_index(drop=True)
    )
    logger.info("Built seasonal weather features with %d rows.", len(seasonal))
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

    if "Area" in df.columns:
        mask = df["Area"].astype(str).str.contains(
            "mysore|mysuru", case=False, na=False
        )
        filtered = df.loc[mask].copy()
        if filtered.empty:
            logger.warning(
                "No rows matched Mysuru/Mysore in Area column; using full dataset."
            )
            filtered = df.copy()
    else:
        logger.warning("Area column not found; cannot filter by district.")
        filtered = df.copy()

    filtered = filtered.drop_duplicates()
    filtered = filtered.dropna(subset=["Crops", "Season", "yeilds"], how="any")

    # Normalise naming for key categoricals
    for col in ("Crops", "Season", "Soil type", "Irrigation"):
        if col in filtered.columns:
            filtered[col] = filtered[col].astype(str).str.strip().str.title()

    return filtered


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

    # Merge weather onto crop management by Season and nearest year if year exists.
    if "year" in weather_seasonal.columns and "Year" in crop_mgmt.columns:
        merged = pd.merge(
            crop_mgmt,
            weather_seasonal,
            left_on=["Year", "Season"],
            right_on=["year", "Season"],
            how="left",
        )
    else:
        merged = pd.merge(crop_mgmt, weather_seasonal, on="Season", how="left")

    merged = pd.merge(merged, soil_nutrients, on="Crops", how="left")

    # Construct a yield-per-area target to avoid the very large absolute
    # production numbers present in the raw `yeilds` column.
    if "Area" in merged.columns:
        merged["yield_per_area"] = merged["yeilds"] / merged["Area"].replace(0, np.nan)
    else:
        merged["yield_per_area"] = merged["yeilds"]

    # Drop rows without a valid target
    merged = merged.dropna(subset=["yield_per_area"])

    # Filter out implausible agronomic outliers. Most rows are in ~0–20 range,
    # but a few reach extremely high values (e.g. >1e5) which destabilise the
    # model. Keep only reasonable yields per acre.
    valid_mask = merged["yield_per_area"].between(0.1, 30)
    merged = merged.loc[valid_mask].copy()

    # Add simple interaction features that capture important agronomic
    # relationships.
    if {"Rainfall", "Temperature"}.issubset(merged.columns):
        merged["rain_temp"] = merged["Rainfall"] * merged["Temperature"]
    if {"Temperature", "Humidity"}.issubset(merged.columns):
        merged["temp_humidity"] = merged["Temperature"] * merged["Humidity"]
    if {"Season", "Crops"}.issubset(merged.columns):
        merged["season_crop"] = (
            merged["Season"].astype(str).str.strip()
            + "_"
            + merged["Crops"].astype(str).str.strip()
        )

    # Fill numeric NaNs with column medians to stabilise the model.
    numeric_cols = merged.select_dtypes(include=[np.number]).columns.tolist()
    # Exclude target, area, and other obvious leakage columns from the
    # feature list.
    for leak_col in ["yeilds", "yield_per_area", "Area"]:
        if leak_col in numeric_cols:
            numeric_cols.remove(leak_col)
    numeric_means: Dict[str, float] = {}
    for col in numeric_cols:
        merged[col] = merged[col].fillna(merged[col].median())
        numeric_means[col] = float(merged[col].mean())

    # Minimal rainfall statistics for later risk analysis.
    rainfall_cols = [c for c in merged.columns if "rainfall" in c.lower()]
    rainfall_stats = {}
    for col in rainfall_cols:
        rainfall_stats[col] = {
            "mean": float(merged[col].mean()),
            "std": float(merged[col].std(ddof=1) if merged[col].std(ddof=1) > 0 else 0.0),
        }

    categorical_features = [
        col
        for col in ["Crops", "Season", "Soil type", "Irrigation"]
        if col in merged.columns
    ]

    # Drop the original production column, the derived target, and Area from X
    # to prevent label leakage and ensure we are truly modelling per-acre yield.
    drop_cols = [c for c in ["yeilds", "yield_per_area", "Area"] if c in merged.columns]
    y = merged["yield_per_area"].astype(float)
    X = merged.drop(columns=drop_cols)

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
    }

    return X, y, feature_spec, metadata


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

