import logging
from datetime import datetime
from pathlib import Path
from typing import Tuple

import joblib
import matplotlib.pyplot as plt
import numpy as np
try:  # SHAP is optional; some numpy/python combos are incompatible
    import shap  # type: ignore[import]
except Exception:  # pragma: no cover - defensive
    shap = None
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import RandomizedSearchCV, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from xgboost import XGBRegressor

from .preprocess import (
    build_feature_matrix,
    build_preprocessor,
    load_crop_management_data,
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
    Train crop-specific XGBoost yield models and persist model artifacts
    and diagnostics. A separate model is trained for each crop with
    sufficient data, which typically improves R2 for heterogeneous
    multi-crop datasets.
    """
    weather_path = DATA_DIR / "mysore2021-.csv"
    crop_path = DATA_DIR / "data_season.csv"
    soil_path = DATA_DIR / "Crop_recommendation.csv"

    weather = load_weather_data(weather_path, district=district)
    crop_mgmt = load_crop_management_data(crop_path, district=district)
    soil = load_soil_nutrient_data(soil_path)

    X, y, feature_spec, metadata = build_feature_matrix(weather, crop_mgmt, soil)

    crops = sorted(X["Crops"].dropna().unique().tolist())
    models_by_crop = {}
    per_crop_meta = {}

    version = _get_version_stamp()
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    for crop in crops:
        mask = X["Crops"] == crop
        Xc = X.loc[mask].copy()
        yc = y.loc[mask].copy()

        if len(Xc) < 50:
            logger.warning(
                "Skipping crop %s due to insufficient samples (%d < 50).",
                crop,
                len(Xc),
            )
            continue

        logger.info("Training model for crop '%s' with %d samples.", crop, len(Xc))

        X_train, X_test, y_train, y_test = train_test_split(
            Xc, yc, test_size=0.2, random_state=42
        )

        preprocessor = build_preprocessor(feature_spec)
        base_model = XGBRegressor(
            random_state=42,
            objective="reg:squarederror",
            n_estimators=300,
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
            n_iter=10,
            cv=3,
            scoring="r2",
            n_jobs=-1,
            random_state=42,
        )
        search.fit(X_train, y_train)
        logger.info(
            "Crop %s - best CV R2: %.4f", crop, search.best_score_
        )
        y_pred = search.predict(X_test)
        r2, mae, rmse = _evaluate_predictions(y_test, y_pred)
        logger.info(
            "Crop %s test metrics -> R2: %.4f, MAE: %.4f, RMSE: %.4f",
            crop,
            r2,
            mae,
            rmse,
        )

        best_model = search.best_estimator_
        models_by_crop[crop] = best_model

        # Cross-validated confidence per crop, mapped into a 0–100 advisory scale.
        cv_scores = cross_val_score(
            best_model, Xc, yc, cv=5, scoring="r2", n_jobs=-1
        )
        cv_r2_mean = float(cv_scores.mean())
        cv_r2_std = float(cv_scores.std(ddof=1)) if len(cv_scores) > 1 else 0.0
        confidence_pct = float(np.clip(50.0 + cv_r2_mean * 50.0, 0.0, 100.0))

        per_crop_meta[crop] = {
            "r2": r2,
            "mae": mae,
            "rmse": rmse,
            "cv_r2_mean": cv_r2_mean,
            "cv_r2_std": cv_r2_std,
            "confidence_pct": confidence_pct,
            "n_samples": int(len(Xc)),
        }

        # Optional SHAP + plots for the first well-supported crop only.
        if shap is not None and len(per_crop_meta) == 1:
            try:
                X_train_trans = best_model.named_steps["preprocessor"].transform(
                    X_train
                )
                model_step = best_model.named_steps["model"]
                try:
                    feature_names = (
                        best_model.named_steps["preprocessor"].get_feature_names_out()
                    )
                except Exception:
                    feature_names = [
                        f"f_{i}" for i in range(X_train_trans.shape[1])
                    ]

                explainer = shap.TreeExplainer(model_step)
                shap_values = explainer.shap_values(X_train_trans)
                shap.summary_plot(
                    shap_values,
                    X_train_trans,
                    feature_names=feature_names,
                    show=False,
                )
                shap_out = MODELS_DIR / f"shap_summary_{version}_{crop}.png"
                shap_out.parent.mkdir(parents=True, exist_ok=True)
                plt.tight_layout()
                plt.savefig(shap_out)
                plt.close()
                logger.info("Saved SHAP summary plot to %s", shap_out)

                _plot_feature_importance(
                    model_step,
                    feature_names,
                    MODELS_DIR / f"feature_importance_{version}_{crop}.png",
                )

                y_pred_all = best_model.predict(Xc)
                _plot_actual_vs_pred(
                    yc,
                    y_pred_all,
                    MODELS_DIR / f"actual_vs_pred_{version}_{crop}.png",
                )
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Failed to compute SHAP/plots for crop %s: %s", crop, exc)

    if not models_by_crop:
        raise RuntimeError("No crop had sufficient samples to train a model.")

    # Persist the dictionary of crop-specific models.
    model_path_versioned = MODELS_DIR / f"yield_model_{version}.pkl"
    joblib.dump(models_by_crop, model_path_versioned)
    joblib.dump(models_by_crop, MODELS_DIR / "yield_model.pkl")

    # Save metadata with per-crop metrics and advisory confidence.
    metadata.update(
        {
            "model_name": "XGBRegressor_per_crop",
            "version": version,
            "per_crop": per_crop_meta,
        }
    )
    save_metadata(metadata, MODELS_DIR, version)

    logger.info(
        "Training complete. Trained models for crops: %s",
        ", ".join(models_by_crop.keys()),
    )


if __name__ == "__main__":
    train_models()

