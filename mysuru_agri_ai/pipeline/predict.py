import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

import joblib
import numpy as np
import pandas as pd


logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = PROJECT_ROOT / "models"


@dataclass
class ModelBundle:
    model: object
    preprocessor: object
    metadata: Dict


def load_latest_model() -> ModelBundle:
    """
    Load the latest trained model, preprocessor, and metadata.
    """
    model_path = MODELS_DIR / "yield_model.pkl"
    preproc_path = MODELS_DIR / "preprocessor.pkl"
    metadata_path = MODELS_DIR / "metadata.json"

    if not model_path.exists():
        raise FileNotFoundError(
            f"Model file not found at {model_path}. Have you run the training script?"
        )

    model = joblib.load(model_path)
    preprocessor = joblib.load(preproc_path) if preproc_path.exists() else None
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
    logger.info(
        "Loaded model version %s", metadata.get("version", "unknown")
    )
    return ModelBundle(model=model, preprocessor=preprocessor, metadata=metadata)


def _tree_based_confidence_interval(
    model, X_trans: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Estimate prediction mean, lower, and upper bounds using tree ensemble
    variability across estimators (RandomForest or XGBoost with estimators_).
    """
    if hasattr(model, "estimators_"):
        # RandomForest-like
        all_preds = np.stack([tree.predict(X_trans) for tree in model.estimators_], axis=0)
    elif hasattr(model, "get_booster"):
        # XGBoost: use individual trees via predict with output_margin disabled and ntree_limit
        booster = model.get_booster()
        n_trees = len(booster.get_dump())
        all_preds = []
        for i in range(1, n_trees + 1):
            preds = model.predict(X_trans, iteration_range=(0, i))
            all_preds.append(preds)
        all_preds = np.stack(all_preds, axis=0)
    else:
        # Fallback: no per-estimator info; assume fixed uncertainty
        mean_pred = model.predict(X_trans)
        std = np.full_like(mean_pred, fill_value=np.std(mean_pred) * 0.1)
        ci_low = mean_pred - 1.96 * std
        ci_high = mean_pred + 1.96 * std
        return mean_pred, ci_low, ci_high

    mean_pred = all_preds.mean(axis=0)
    std_pred = all_preds.std(axis=0, ddof=1)
    ci_low = mean_pred - 1.96 * std_pred
    ci_high = mean_pred + 1.96 * std_pred
    return mean_pred, ci_low, ci_high


def _confidence_and_risk_from_interval(
    mean_pred: np.ndarray,
    ci_low: np.ndarray,
    ci_high: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    width = ci_high - ci_low
    with np.errstate(divide="ignore", invalid="ignore"):
        rel_width = np.where(mean_pred != 0, width / np.abs(mean_pred), width)
    # Map relative width to qualitative risk only; confidence itself is derived
    # from global cross-validation performance.
    dummy = np.zeros_like(rel_width)
    risk = np.full_like(dummy, fill_value="Moderate", dtype=object)
    risk[rel_width <= 0.15] = "Low"
    risk[rel_width >= 0.35] = "High"
    # Second return value is kept for backward-compatibility with callers.
    return rel_width, risk


def batch_predict(
    bundle: ModelBundle,
    scenarios: pd.DataFrame,
) -> pd.DataFrame:
    """
    Run batch prediction for a set of farming scenarios and compute
    confidence intervals and risk scores.
    """
    model = bundle.model
    preprocessor = bundle.preprocessor

    feature_spec = bundle.metadata.get("feature_spec", {})
    numeric_features = feature_spec.get("numeric", [])
    categorical_features = feature_spec.get("categorical", [])
    numeric_means = bundle.metadata.get("numeric_means", {})

    # Align scenario columns with the training feature space: add any missing
    # numeric features using their training-set means, and default missing
    # categoricals to a neutral "Unknown" token.
    X_full = scenarios.copy()
    for col in numeric_features:
        if col not in X_full.columns:
            X_full[col] = numeric_means.get(col, 0.0)
    for col in categorical_features:
        if col not in X_full.columns:
            X_full[col] = "Unknown"

    # If we have crop-specific models (dict), route each scenario row to the
    # appropriate model; otherwise fall back to a single global model.
    if isinstance(model, dict):
        if "Crops" not in X_full.columns:
            raise ValueError("Crops column is required for crop-specific models.")

        per_crop_meta = bundle.metadata.get("per_crop", {})
        all_rows: list[pd.DataFrame] = []

        for crop, group in X_full.groupby("Crops", sort=False):
            crop_model = model.get(crop)
            if crop_model is None:
                raise ValueError(f"No trained model available for crop '{crop}'.")

            X_sub = group
            X_trans = crop_model.named_steps["preprocessor"].transform(X_sub)  # type: ignore[index]
            mean_pred, ci_low, ci_high = _tree_based_confidence_interval(
                crop_model.named_steps["model"],  # type: ignore[index]
                X_trans,
            )

            _, risk_level = _confidence_and_risk_from_interval(
                mean_pred, ci_low, ci_high
            )

            # Per-crop advisory confidence from training metadata; default to 50.
            crop_meta = per_crop_meta.get(str(crop), {})
            cv_conf = float(crop_meta.get("confidence_pct", 50.0))
            cv_conf = float(np.clip(cv_conf, 0.0, 100.0))

            res = scenarios.loc[X_sub.index].copy()
            res["predicted_yield"] = mean_pred
            res["ci_low"] = ci_low
            res["ci_high"] = ci_high
            res["confidence"] = cv_conf
            res["risk_level"] = risk_level

            all_rows.append(res)

        results = pd.concat(all_rows, axis=0).loc[scenarios.index]
    else:
        if hasattr(model, "predict") and preprocessor is not None:
            X_trans = preprocessor.transform(X_full)
            mean_pred, ci_low, ci_high = _tree_based_confidence_interval(
                model.named_steps.get("model", model),  # type: ignore[arg-type]
                X_trans,
            )
        else:
            mean_pred, ci_low, ci_high = _tree_based_confidence_interval(
                model, X_full
            )

        _, risk_level = _confidence_and_risk_from_interval(
            mean_pred, ci_low, ci_high
        )

        cv_conf = float(bundle.metadata.get("confidence_pct", 50.0))
        cv_conf = float(np.clip(cv_conf, 0.0, 100.0))

        results = scenarios.copy()
        results["predicted_yield"] = mean_pred
        results["ci_low"] = ci_low
        results["ci_high"] = ci_high
        results["confidence"] = cv_conf
        results["risk_level"] = risk_level

    # Optional: compute total production estimate for the given field area.
    if "Area" in results.columns:
        try:
            results["estimated_total_yield"] = (
                results["predicted_yield"] * results["Area"].astype(float)
            )
        except Exception:
            pass

    return results

