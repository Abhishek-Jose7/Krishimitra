import json
import os
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
import joblib


KARNATAKA_DISTRICTS: List[str] = [
    "bagalkot",
    "ballari",
    "belagavi",
    "bengaluru rural",
    "bengaluru urban",
    "bidar",
    "chamarajanagar",
    "chikkaballapur",
    "chikkamagaluru",
    "chitradurga",
    "dakshina kannada",
    "davangere",
    "dharwad",
    "gadag",
    "hassan",
    "haveri",
    "kalaburagi",
    "kodagu",
    "kolar",
    "koppal",
    "mandya",
    "mysuru",
    "raichur",
    "ramanagara",
    "shivamogga",
    "tumakuru",
    "udupi",
    "uttara kannada",
    "vijayapura",
    "yadgir",
]


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lower-case and strip column names for easier matching."""
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    return df


def _find_column(columns: List[str], *keywords: str) -> str:
    """Return first column whose name contains all given keywords."""
    for col in columns:
        name = col.lower()
        if all(k.lower() in name for k in keywords):
            return col
    raise ValueError(f"Could not find column matching keywords {keywords} in {columns}")


def load_and_merge_datasets(project_root: Path) -> Tuple[pd.DataFrame, str]:
    """
    Load weather, crop recommendation and crop yield datasets,
    merge them into a single training DataFrame and return (df, target_column_name).

    Assumes the following files live in the top-level `csv` folder:
      - weather-1.csv
      - Crop_recommendation.csv
      - Crop_Predication_dataset.xlsx
    """
    csv_dir = project_root / "csv"

    weather_path = csv_dir / "weather-1.csv"
    crop_rec_path = csv_dir / "Crop_recommendation.csv"
    crop_yield_path = csv_dir / "Crop_Predication_dataset.xlsx"

    if not weather_path.exists():
        raise FileNotFoundError(f"Weather dataset not found at {weather_path}")
    if not crop_rec_path.exists():
        raise FileNotFoundError(f"Crop recommendation dataset not found at {crop_rec_path}")
    if not crop_yield_path.exists():
        raise FileNotFoundError(f"Crop yield dataset not found at {crop_yield_path}")

    # --- Load raw datasets ---
    weather_df = pd.read_csv(weather_path)
    crop_rec_df = pd.read_csv(crop_rec_path)
    crop_yield_df = pd.read_excel(crop_yield_path)

    weather_df = _normalise_columns(weather_df)
    crop_rec_df = _normalise_columns(crop_rec_df)
    crop_yield_df = _normalise_columns(crop_yield_df)

    # --- Standardise key column names using heuristics ---
    # Weather
    weather_district_col = _find_column(weather_df.columns.tolist(), "district") if any(
        "district" in c for c in weather_df.columns
    ) else _find_column(weather_df.columns.tolist(), "location")
    rainfall_col = _find_column(weather_df.columns.tolist(), "rain")
    temp_col = _find_column(weather_df.columns.tolist(), "temp")
    humidity_col = _find_column(weather_df.columns.tolist(), "humid")

    weather_df = weather_df.rename(
        columns={
            weather_district_col: "district",
            rainfall_col: "rainfall",
            temp_col: "temperature",
            humidity_col: "humidity",
        }
    )

    # Crop recommendation – typically N, P, K, ph, rainfall, label (crop)
    n_col = _find_column(crop_rec_df.columns.tolist(), "n")
    p_col = _find_column(crop_rec_df.columns.tolist(), "p")
    k_col = _find_column(crop_rec_df.columns.tolist(), "k")
    ph_col = _find_column(crop_rec_df.columns.tolist(), "ph")
    rec_rainfall_col = _find_column(crop_rec_df.columns.tolist(), "rain")
    crop_label_col = _find_column(crop_rec_df.columns.tolist(), "label")

    crop_rec_df = crop_rec_df.rename(
        columns={
            n_col: "n",
            p_col: "p",
            k_col: "k",
            ph_col: "ph",
            rec_rainfall_col: "rec_rainfall",
            crop_label_col: "crop",
        }
    )

    # Crop yield dataset – crop, district, season, irrigation, area, yield
    y_columns = crop_yield_df.columns.tolist()

    district_col = _find_column(y_columns, "district")
    crop_col = _find_column(y_columns, "crop")

    # Season and irrigation might be named in various ways
    try:
        season_col = _find_column(y_columns, "season")
    except ValueError:
        season_col = None

    try:
        irrigation_col = _find_column(y_columns, "irrigation")
    except ValueError:
        irrigation_col = None

    # Cultivated area
    try:
        area_col = _find_column(y_columns, "area")
    except ValueError:
        area_col = _find_column(y_columns, "cultivated")

    # Target yield
    target_col = _find_column(y_columns, "yield")

    rename_map = {
        district_col: "district",
        crop_col: "crop",
        area_col: "area_hectares",
        target_col: "yield_tons_per_hectare",
    }
    if season_col:
        rename_map[season_col] = "season"
    if irrigation_col:
        rename_map[irrigation_col] = "irrigation_type"

    crop_yield_df = crop_yield_df.rename(columns=rename_map)

    # Filter to Karnataka if state is available, otherwise filter by district list
    if any("state" in c for c in crop_yield_df.columns):
        state_col = _find_column(crop_yield_df.columns.tolist(), "state")
        crop_yield_df = crop_yield_df[crop_yield_df[state_col].str.lower() == "karnataka"]
    else:
        crop_yield_df = crop_yield_df[
            crop_yield_df["district"].str.lower().isin(KARNATAKA_DISTRICTS)
        ]

    # --- Merge datasets ---
    merged = crop_yield_df.merge(
        weather_df[["district", "rainfall", "temperature", "humidity"]],
        on="district",
        how="left",
    )

    merged = merged.merge(
        crop_rec_df[["crop", "n", "p", "k", "ph", "rec_rainfall"]],
        on="crop",
        how="left",
    )

    # Prefer actual rainfall if present, otherwise use recommended rainfall
    if "rainfall" not in merged.columns and "rec_rainfall" in merged.columns:
        merged["rainfall"] = merged["rec_rainfall"]
    elif "rainfall" in merged.columns and "rec_rainfall" in merged.columns:
        merged["rainfall"] = merged["rainfall"].fillna(merged["rec_rainfall"])

    # Drop rows without target
    merged = merged.dropna(subset=["yield_tons_per_hectare"])

    return merged, "yield_tons_per_hectare"


def build_pipeline(feature_df: pd.DataFrame, target_col: str) -> Tuple[Pipeline, dict]:
    """
    Build a preprocessing + model pipeline using a gradient boosting regressor
    and return it with detailed evaluation and monitoring metrics.
    """
    # Select a stable feature set; only keep columns that actually exist
    candidate_features = [
        "district",
        "crop",
        "season",
        "irrigation_type",
        "area_hectares",
        "rainfall",
        "temperature",
        "humidity",
        "n",
        "p",
        "k",
        "ph",
    ]
    available_features = [c for c in candidate_features if c in feature_df.columns]

    if not available_features:
        raise ValueError("No usable feature columns found in merged dataset.")

    df = feature_df.copy()

    X = df[available_features]
    y = df[target_col].astype(float)

    # Identify numeric and categorical features
    numeric_features = [
        c for c in available_features if pd.api.types.is_numeric_dtype(X[c])
    ]
    categorical_features = [c for c in available_features if c not in numeric_features]

    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
        ]
    )

    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features),
        ]
    )

    # HistGradientBoostingRegressor is a strong tabular model that handles
    # heterogeneous features well and is fully compatible with sklearn Pipelines.
    model = HistGradientBoostingRegressor(
        max_depth=None,
        learning_rate=0.1,
        max_iter=300,
        random_state=42,
    )

    pipeline = Pipeline(
        steps=[
            ("preprocess", preprocessor),
            ("model", model),
        ]
    )

    # --- Time-aware or grouped split ---
    # If a year column exists, train on past years and evaluate on the latest year.
    if "year" in df.columns and df["year"].notna().any():
        years = sorted(df["year"].dropna().unique().tolist())
        if len(years) >= 2:
            test_year = years[-1]
            train_mask = df["year"] < test_year
            test_mask = df["year"] == test_year

            if train_mask.sum() > 0 and test_mask.sum() > 0:
                X_train, X_test = X[train_mask], X[test_mask]
                y_train, y_test = y[train_mask], y[test_mask]
            else:
                # Fallback if year split is degenerate
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.2, random_state=42
                )
        else:
            # Not enough distinct years, use standard random split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
    else:
        # No explicit year information; use a standard stratified-by-distribution split.
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

    pipeline.fit(X_train, y_train)

    # --- Global metrics ---
    y_pred = pipeline.predict(X_test)

    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    mae = float(mean_absolute_error(y_test, y_pred))
    r2 = float(r2_score(y_test, y_pred))

    q_low, q_high = np.quantile(y, [0.33, 0.66])

    metrics: Dict[str, Any] = {
        "rmse": rmse,
        "mae": mae,
        "r2": r2,
        "n_samples": int(len(y)),
        "features": available_features,
        "yield_quantiles": {
            "low": float(q_low),
            "high": float(q_high),
        },
    }

    # --- Per-crop and per-crop-per-district monitoring metrics ---
    test_index = X_test.index
    eval_df = df.loc[test_index].copy()
    eval_df["y_true"] = y.loc[test_index]
    eval_df["y_pred"] = y_pred

    per_crop: Dict[str, Dict[str, float]] = {}
    if "crop" in eval_df.columns:
        for crop_name, group in eval_df.groupby("crop"):
            if len(group) < 5:
                continue  # avoid unstable metrics
            per_crop[crop_name] = {
                "rmse": float(
                    np.sqrt(mean_squared_error(group["y_true"], group["y_pred"]))
                ),
                "mae": float(mean_absolute_error(group["y_true"], group["y_pred"])),
                "r2": float(r2_score(group["y_true"], group["y_pred"])),
                "n": int(len(group)),
            }

    per_crop_district: Dict[str, Dict[str, float]] = {}
    if "crop" in eval_df.columns and "district" in eval_df.columns:
        for (crop_name, district_name), group in eval_df.groupby(
            ["crop", "district"]
        ):
            if len(group) < 5:
                continue
            key = f"{crop_name}__{district_name}"
            per_crop_district[key] = {
                "rmse": float(
                    np.sqrt(mean_squared_error(group["y_true"], group["y_pred"]))
                ),
                "mae": float(mean_absolute_error(group["y_true"], group["y_pred"])),
                "r2": float(r2_score(group["y_true"], group["y_pred"])),
                "n": int(len(group)),
            }

    # Per-crop yield quantiles for more contextual categorisation
    per_crop_quantiles: Dict[str, Dict[str, float]] = {}
    if "crop" in df.columns:
        for crop_name, group in df.groupby("crop"):
            if len(group) < 5:
                continue
            low_q, high_q = np.quantile(
                group[target_col].astype(float), [0.33, 0.66]
            )
            per_crop_quantiles[crop_name] = {
                "low": float(low_q),
                "high": float(high_q),
            }

    metrics["per_crop_metrics"] = per_crop
    metrics["per_crop_district_metrics"] = per_crop_district
    metrics["per_crop_yield_quantiles"] = per_crop_quantiles

    return pipeline, metrics


def main() -> None:
    """Entry point to train and persist the Karnataka yield model."""
    # Resolve project root as the parent of this backend directory
    backend_dir = Path(__file__).resolve().parent
    project_root = backend_dir.parent

    print("Loading and merging datasets...")
    merged_df, target_col = load_and_merge_datasets(project_root)
    print(f"Merged dataset shape: {merged_df.shape}")

    print("Building and training model...")
    model, metrics = build_pipeline(merged_df, target_col)

    print("Evaluation metrics on hold-out set:")
    print(f"  RMSE: {metrics['rmse']:.3f}")
    print(f"  MAE:  {metrics['mae']:.3f}")
    print(f"  R²:   {metrics['r2']:.3f}")
    print(f"  Samples: {metrics['n_samples']}")

    models_dir = backend_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    model_path = models_dir / "yield_model.pkl"
    metrics_path = models_dir / "yield_model_metrics.json"

    joblib.dump(model, model_path)
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print(f"Saved trained model to: {model_path}")
    print(f"Saved training metrics to: {metrics_path}")


if __name__ == "__main__":
    main()

