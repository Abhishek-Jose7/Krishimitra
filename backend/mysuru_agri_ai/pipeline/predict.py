import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

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
    models_dict_path = MODELS_DIR / "yield_models.pkl"
    model_path = MODELS_DIR / "yield_model.pkl"
    preproc_path = MODELS_DIR / "preprocessor.pkl"
    metadata_path = MODELS_DIR / "metadata.json"

    if not models_dict_path.exists() and not model_path.exists():
        raise FileNotFoundError(
            f"No model artifacts found in {MODELS_DIR}. Have you run the training script?"
        )

    model = joblib.load(models_dict_path) if models_dict_path.exists() else joblib.load(model_path)
    preprocessor = joblib.load(preproc_path) if preproc_path.exists() else None
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
    logger.info(
        "Loaded model version %s", metadata.get("version", "unknown")
    )
    return ModelBundle(model=model, preprocessor=preprocessor, metadata=metadata)


_CACHED_BUNDLE: Optional[ModelBundle] = None


def get_model_bundle() -> ModelBundle:
    """
    Lazily load and cache the latest model bundle for reuse across
    multiple calls (Flask services, FastAPI app, CLI, etc.).

    This ensures we do not reload the model artifacts on every request.
    """
    global _CACHED_BUNDLE
    if _CACHED_BUNDLE is None:
        _CACHED_BUNDLE = load_latest_model()
    return _CACHED_BUNDLE


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

    dummy = np.zeros_like(rel_width)
    risk = np.full_like(dummy, fill_value="Moderate", dtype=object)
    risk[rel_width <= 0.15] = "Low"
    risk[rel_width >= 0.35] = "High"
    # Second return value is kept for backward-compatibility with callers.
    return rel_width, risk


def _compute_scenario_confidence(
    mean_pred: np.ndarray,
    ci_low: np.ndarray,
    ci_high: np.ndarray,
    cv_conf_pct: float,
) -> np.ndarray:
    """
    Compute a more informative per-scenario confidence score (0–100%).

    The score combines:
      - Global cross-validation confidence (cv_conf_pct), and
      - Scenario-specific interval width (narrower intervals => higher confidence).
    """
    base = float(np.clip(cv_conf_pct, 0.0, 100.0))

    width = ci_high - ci_low
    with np.errstate(divide="ignore", invalid="ignore"):
        rel_width = np.where(mean_pred != 0, width / np.abs(mean_pred), width)

    # Map relative interval width into a [0, 1] multiplier where:
    #   very narrow (<= 10%)   -> ~1.0
    #   moderate (~25%)        -> ~0.7
    #   very wide (>= 50%)     -> ~0.3
    rel_width_clipped = np.clip(rel_width, 0.05, 0.5)
    interval_factor = 1.2 - (rel_width_clipped / 0.5)  # 0.05 -> ~1.1, 0.5 -> 0.2
    interval_factor = np.clip(interval_factor, 0.3, 1.1)

    conf = base * interval_factor
    conf = np.clip(conf, 5.0, 98.0)
    return conf


def batch_predict(
    bundle: ModelBundle,
    scenarios: pd.DataFrame,
) -> pd.DataFrame:
    """
    Run batch prediction for a set of farming scenarios and compute
    confidence intervals and risk scores.

    Supports both:
    - Unified model (single Pipeline for all districts) — new default
    - Per-district dict of Pipelines — legacy backward compat
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

    # Enrich scenarios with district-season weather and district-level nutrient defaults
    # when those features are required by the model but missing from scenarios.
    refs = bundle.metadata.get("references", {})
    weather_refs = refs.get("weather_by_district_season", {})
    nutrient_refs = refs.get("nutrients_by_district", {})

    if {"district", "Season"}.issubset(X_full.columns):
        for idx, row in X_full[["district", "Season"]].iterrows():
            d = str(row["district"]).strip().title()
            s = str(row["Season"]).strip().title()
            w = weather_refs.get(d, {}).get(s)
            if w:
                for col in (
                    "Temperature",
                    "Rainfall",
                    "Humidity",
                    "seasonal_rainfall_total",
                    "rainfall_variability",
                    "extreme_heat_days",
                    "seasonal_avg_humidity",
                ):
                    if col not in X_full.columns or pd.isna(X_full.at[idx, col]):
                        X_full.at[idx, col] = w.get(col)

    if "district" in X_full.columns:
        for idx, d_raw in X_full["district"].items():
            d = str(d_raw).strip().title()
            n = nutrient_refs.get(d)
            if n:
                for col in ("N", "P", "K", "ph"):
                    if col not in X_full.columns or pd.isna(X_full.at[idx, col]):
                        X_full.at[idx, col] = n.get(col)
    for col in numeric_features:
        if col not in X_full.columns:
            X_full[col] = numeric_means.get(col, 0.0)
    for col in categorical_features:
        if col not in X_full.columns:
            X_full[col] = "Unknown"

    # Add interaction features that the model expects
    if {"Rainfall", "Temperature"}.issubset(X_full.columns):
        if "rain_per_degree" not in X_full.columns:
            X_full["rain_per_degree"] = X_full["Rainfall"] / X_full["Temperature"].replace(0, np.nan)
            X_full["rain_per_degree"] = X_full["rain_per_degree"].fillna(0.0)
    if {"Temperature", "Humidity"}.issubset(X_full.columns):
        if "heat_stress_index" not in X_full.columns:
            X_full["heat_stress_index"] = X_full["Temperature"] * (100 - X_full["Humidity"]) / 100.0

    # Inverse-transform support (if training used log1p target)
    transform = str(bundle.metadata.get("target_transform", "none")).lower()
    use_log1p = transform == "log1p"

    # ── Determine if this is a unified model or per-district dict ──
    is_unified = False
    unified_pipeline = None

    if isinstance(model, dict):
        # New format: dict with "__unified__" key containing single Pipeline
        if "__unified__" in model:
            is_unified = True
            unified_pipeline = model["__unified__"]
        # else: legacy per-district dict format
    elif hasattr(model, "predict") and hasattr(model, "named_steps"):
        # Direct Pipeline object (unified model saved as yield_model.pkl)
        is_unified = True
        unified_pipeline = model

    # Also check metadata for explicit model_type flag
    if bundle.metadata.get("model_type") == "unified" and unified_pipeline is None:
        # Try loading from the Pipeline object itself
        if hasattr(model, "predict"):
            is_unified = True
            unified_pipeline = model

    if is_unified and unified_pipeline is not None:
        # ── UNIFIED MODEL PATH ──
        X_trans = unified_pipeline.named_steps["preprocessor"].transform(X_full)
        mean_pred, ci_low, ci_high = _tree_based_confidence_interval(
            unified_pipeline.named_steps["model"],
            X_trans,
        )

        if use_log1p:
            mean_pred = np.expm1(mean_pred)
            ci_low = np.expm1(ci_low)
            ci_high = np.expm1(ci_high)

        rel_width, risk_level = _confidence_and_risk_from_interval(
            mean_pred, ci_low, ci_high
        )

        # Use per-district confidence if available, else global
        per_district = bundle.metadata.get("per_district", {})
        global_metrics = bundle.metadata.get("global_metrics", {})
        global_conf = float(global_metrics.get("confidence_pct", 50.0))

        # Compute per-row confidence using district-specific or global CV
        if "district" in scenarios.columns:
            district_conf = []
            for _, row in scenarios.iterrows():
                d = str(row["district"]).strip().title()
                meta = per_district.get(d, {})
                cv_conf = float(meta.get("confidence_pct", global_conf))
                district_conf.append(cv_conf)
            cv_conf_array = np.array(district_conf)
        else:
            cv_conf_array = np.full(len(scenarios), global_conf)

        scenario_conf = _compute_scenario_confidence(
            mean_pred, ci_low, ci_high, float(np.mean(cv_conf_array))
        )

        # Adjust per-row confidence by district
        for i in range(len(scenario_conf)):
            district_weight = cv_conf_array[i] / max(global_conf, 1.0)
            scenario_conf[i] = np.clip(scenario_conf[i] * district_weight, 5.0, 98.0)

        results = scenarios.copy()
        results["predicted_yield"] = mean_pred
        results["ci_low"] = ci_low
        results["ci_high"] = ci_high
        results["confidence"] = scenario_conf
        results["risk_level"] = risk_level

        # Evidence level based on whether district was in training data
        results["evidence_level"] = "High"
        if "district" in results.columns:
            trained_districts = set(per_district.keys())
            if trained_districts:
                results.loc[
                    ~results["district"].astype(str).str.title().isin(trained_districts),
                    "evidence_level",
                ] = "Low"

    elif isinstance(model, dict):
        # ── LEGACY PER-DISTRICT DICT PATH ──
        if "district" not in X_full.columns:
            raise ValueError("district column is required for district-specific models.")

        per_district = bundle.metadata.get("per_district", {})
        out_parts: list[pd.DataFrame] = []

        for d, group in X_full.groupby("district", sort=False):
            d_norm = str(d).strip().title()
            district_model = model.get(d_norm)

            evidence_level = "High"
            if district_model is None:
                fallback_key = "Mysuru" if "Mysuru" in model else next(iter(model.keys()))
                district_model = model[fallback_key]
                d_norm = fallback_key
                evidence_level = "Low"

            X_sub = group
            X_trans = district_model.named_steps["preprocessor"].transform(X_sub)
            mean_pred, ci_low, ci_high = _tree_based_confidence_interval(
                district_model.named_steps["model"],
                X_trans,
            )

            if use_log1p:
                mean_pred = np.expm1(mean_pred)
                ci_low = np.expm1(ci_low)
                ci_high = np.expm1(ci_high)

            rel_width, risk_level = _confidence_and_risk_from_interval(
                mean_pred, ci_low, ci_high
            )

            meta = per_district.get(d_norm, {})
            cv_conf = float(meta.get("confidence_pct", 50.0))
            cv_conf = float(np.clip(cv_conf, 0.0, 100.0))
            scenario_conf = _compute_scenario_confidence(
                mean_pred, ci_low, ci_high, cv_conf
            )

            res = scenarios.loc[X_sub.index].copy()
            res["predicted_yield"] = mean_pred
            res["ci_low"] = ci_low
            res["ci_high"] = ci_high
            res["confidence"] = scenario_conf
            res["risk_level"] = risk_level
            res["evidence_level"] = evidence_level

            out_parts.append(res)

        results = pd.concat(out_parts, axis=0).loc[scenarios.index]
    else:
        # Fallback: single model with separate preprocessor
        if hasattr(model, "predict") and preprocessor is not None:
            X_trans = preprocessor.transform(X_full)
            mean_pred, ci_low, ci_high = _tree_based_confidence_interval(
                model.named_steps.get("model", model),
                X_trans,
            )
        else:
            mean_pred, ci_low, ci_high = _tree_based_confidence_interval(
                model, X_full
            )

        if use_log1p:
            mean_pred = np.expm1(mean_pred)
            ci_low = np.expm1(ci_low)
            ci_high = np.expm1(ci_high)

        # ── PHASE 2 FIX: De-normalization ──
        # The model predicts RYI. Multiply by crop_median to get raw units.
        crop_medians = bundle.metadata.get("crop_medians", {})
        
        # We need to map each scenario's crop to its median
        scenario_crop_medians = scenarios["Crops"].map(crop_medians).fillna(1.0).values
        
        mean_pred = mean_pred * scenario_crop_medians
        ci_low = ci_low * scenario_crop_medians
        ci_high = ci_high * scenario_crop_medians

        rel_width, risk_level = _confidence_and_risk_from_interval(
            mean_pred, ci_low, ci_high
        )

        cv_conf = float(bundle.metadata.get("confidence_pct", 50.0))
        cv_conf = float(np.clip(cv_conf, 0.0, 100.0))
        scenario_conf = _compute_scenario_confidence(
            mean_pred, ci_low, ci_high, cv_conf
        )

        results = scenarios.copy()
        results["predicted_yield"] = mean_pred
        results["ci_low"] = ci_low
        results["ci_high"] = ci_high
        results["confidence"] = scenario_conf
        results["risk_level"] = risk_level
        results["evidence_level"] = "High"
        if "district" in scenarios.columns:
            seen = set(
                bundle.metadata.get("references", {})
                .get("weather_by_district_season", {})
                .keys()
            )
            results.loc[~results["district"].astype(str).str.title().isin(seen), "evidence_level"] = "Low"

    # Optional: compute total production estimate for the given field area.
    if "Area" in results.columns:
        try:
            results["estimated_total_yield"] = (
                results["predicted_yield"] * results["Area"].astype(float)
            )
        except Exception:
            pass

    return results

