import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Tuple

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
try:  # SHAP is optional; some numpy/python combos are incompatible
    import shap  # type: ignore[import]
except Exception:  # pragma: no cover - defensive
    shap = None
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import RandomizedSearchCV, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from xgboost import XGBRegressor

from .preprocess import (
    build_district_reference_tables,
    build_feature_matrix,
    build_preprocessor,
    load_crop_management_all,
    load_pune_yield_labels,
    load_soil_nutrient_data,
    load_weather_data,
    save_metadata,
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"


def _get_version_stamp() -> str:
    return datetime.utcnow().strftime("v%Y%m%d%H%M%S")


def _evaluate_predictions(y_true, y_pred) -> Tuple[float, float, float]:
    r2 = r2_score(y_true, y_pred)
    mae = mean_absolute_error(y_true, y_pred)
    rmse = mean_squared_error(y_true, y_pred, squared=False)
    return r2, mae, rmse


def _plot_feature_importance(
    model, feature_names, out_path: Path, title: str = "Feature importance"
) -> None:
    importances = getattr(model, "feature_importances_", None)
    if importances is None:
        logger.warning("Model does not expose feature_importances_; skipping plot.")
        return
    indices = np.argsort(importances)[::-1]
    plt.figure(figsize=(10, 6))
    plt.title(title)
    plt.bar(range(len(importances)), importances[indices])
    plt.xticks(range(len(importances)), [feature_names[i] for i in indices], rotation=90)
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path)
    plt.close()


def _plot_actual_vs_pred(
    y_true, y_pred, out_path: Path, title: str = "Actual vs predicted yields"
) -> None:
    plt.figure(figsize=(6, 6))
    plt.scatter(y_true, y_pred, alpha=0.6)
    min_val = min(y_true.min(), y_pred.min())
    max_val = max(y_true.max(), y_pred.max())
    plt.plot([min_val, max_val], [min_val, max_val], "r--", label="Ideal")
    plt.xlabel("Actual yield")
    plt.ylabel("Predicted yield")
    plt.title(title)
    plt.legend()
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path)
    plt.close()


def train_models(district: str = "Mysuru") -> None:
    """
    Train a unified XGBoost yield model for multi-district simulation.
    The model includes `district` as a categorical feature and supports
    scenario simulation across districts.
    """
    crop_path = DATA_DIR / "data_season.csv"
    soil_path = DATA_DIR / "Crop_recommendation.csv"

    # Load all labeled yield rows and infer district from Location.
    crop_all = load_crop_management_all(crop_path)
    # Optional: append Pune yield labels if provided as a separate file.
    pune_labels = load_pune_yield_labels(DATA_DIR)
    if not pune_labels.empty:
        crop_all = pd.concat([crop_all, pune_labels], ignore_index=True)
        logger.info("Appended Pune yield labels: %d rows", len(pune_labels))
    else:
        logger.warning(
            "No Pune yield-label file found (data/pune_yield_season.csv). "
            "Pune model will not be trained until labeled Pune yield data is provided."
        )
    soil = load_soil_nutrient_data(soil_path)

    # Build district reference tables from available CSVs (Mysuru, Pune, etc.)
    refs = build_district_reference_tables(DATA_DIR)

    # Attach engineered seasonal weather features per district+year+season.
    weather_features_all = []
    for d, season_map in refs.get("weather_by_district_season", {}).items():
        # Build a per-year seasonal table from that district's daily weather file if present.
        # We re-run load_weather_data for each discovered district weather source.
        weather_file = None
        for p in sorted(DATA_DIR.glob("*weather*.csv")):
            if d.lower() in p.stem.lower() or (d == "Mysuru" and "mysore" in p.stem.lower()):
                weather_file = p
                break
        if weather_file is None:
            continue
        try:
            w = load_weather_data(weather_file, district=d)
            weather_features_all.append(w)
        except Exception:
            continue

    weather_all = pd.concat(weather_features_all, ignore_index=True) if weather_features_all else pd.DataFrame()

    # Create a unified feature matrix for the full labeled dataset.
    X, y, feature_spec, metadata = build_feature_matrix(weather_all, crop_all, soil)

    logger.info("Total labeled rows: %d", len(X))
    if "district" in X.columns:
        logger.info("Rows per district:\n%s", X["district"].value_counts().to_string())

    # Optional target transform to stabilise variance for skewed agricultural yields.
    use_log1p = os.getenv("MYSURU_AGRI_LOG1P_TARGET", "1").strip() not in ("0", "false", "False")
    y_for_training = np.log1p(y) if use_log1p else y

    # District-specific model training
    models_by_district = {}
    per_district_meta = {}

    districts = sorted(X["district"].astype(str).str.title().unique().tolist()) if "district" in X.columns else ["Unknown"]

    for d in districts:
        mask = X["district"].astype(str).str.title() == d
        Xd = X.loc[mask].copy()
        yd = y_for_training.loc[mask].copy()

        logger.info("DISTRICT: %s", d)
        logger.info("Row count: %d", len(Xd))

        if len(Xd) < 50:
            logger.warning("Skipping district %s due to insufficient rows (<50).", d)
            continue

        preprocessor = build_preprocessor(feature_spec)

        X_train, X_test, y_train, y_test = train_test_split(
            Xd, yd, test_size=0.2, random_state=42
        )

        base_model = XGBRegressor(
            random_state=42,
            objective="reg:squarederror",
            n_estimators=700,
            learning_rate=0.05,
        )
        xgb_params = {
            "model__max_depth": [4, 6, 8],
            "model__subsample": [0.7, 0.9, 1.0],
            "model__colsample_bytree": [0.7, 0.9, 1.0],
        }

        pipe = Pipeline(
            steps=[
                ("preprocessor", preprocessor),
                ("model", base_model),
            ]
        )

        search = RandomizedSearchCV(
            pipe,
            param_distributions=xgb_params,
            n_iter=12,
            cv=3,
            scoring="r2",
            n_jobs=-1,
            random_state=42,
        )
        search.fit(X_train, y_train)
        best_model = search.best_estimator_

        y_pred = best_model.predict(X_test)
        if use_log1p:
            y_test_eval = np.expm1(y_test)
            y_pred_eval = np.expm1(y_pred)
        else:
            y_test_eval = y_test
            y_pred_eval = y_pred
        r2, mae, rmse = _evaluate_predictions(y_test_eval, y_pred_eval)

        cv_scores = cross_val_score(best_model, Xd, yd, cv=5, scoring="r2", n_jobs=-1)
        cv_r2_mean = float(cv_scores.mean())
        cv_r2_std = float(cv_scores.std(ddof=1)) if len(cv_scores) > 1 else 0.0
        confidence_pct = float(np.clip(50.0 + cv_r2_mean * 50.0, 0.0, 100.0))

        logger.info("CV R2: %.4f ± %.4f", cv_r2_mean, cv_r2_std)
        logger.info("MAE: %.4f | RMSE: %.4f | Test R2: %.4f", mae, rmse, r2)

        # Feature importance logging (top 15)
        try:
            fn = best_model.named_steps["preprocessor"].get_feature_names_out().tolist()  # type: ignore[index]
            imp = best_model.named_steps["model"].feature_importances_  # type: ignore[index]
            top_idx = np.argsort(imp)[::-1][:15]
            top_feats = [(fn[i], float(imp[i])) for i in top_idx]
        except Exception:
            top_feats = []

        per_district_meta[d] = {
            "n_rows": int(len(Xd)),
            "cv_r2_mean": cv_r2_mean,
            "cv_r2_std": cv_r2_std,
            "confidence_pct": confidence_pct,
            "test_r2": float(r2),
            "mae": float(mae),
            "rmse": float(rmse),
            "top_features": top_feats,
        }

        models_by_district[d] = best_model

    if not models_by_district:
        raise RuntimeError("No district had sufficient rows to train a model.")

    version = _get_version_stamp()
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # Persist district model dictionary
    joblib.dump(models_by_district, MODELS_DIR / f"yield_models_{version}.pkl")
    joblib.dump(models_by_district, MODELS_DIR / "yield_models.pkl")

    # Metadata for prediction and advisory
    metadata.update(
        {
            "model_name": "XGBRegressor_by_district",
            "version": version,
            "per_district": per_district_meta,
            "references": refs,
            "target_transform": "log1p" if use_log1p else "none",
            "feature_spec": {
                "numeric": feature_spec.numeric_features,
                "categorical": feature_spec.categorical_features,
            },
        }
    )

    save_metadata(metadata, MODELS_DIR, version)

    logger.info("Training complete. Saved yield_models.pkl (version %s).", version)


if __name__ == "__main__":
    train_models()

