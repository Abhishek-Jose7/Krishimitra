import argparse
import json
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd
import joblib


CANONICAL_FEATURES = [
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


def load_model_and_metadata(backend_dir: Path):
    models_dir = backend_dir / "models"
    model_path = models_dir / "yield_model.pkl"
    metrics_path = models_dir / "yield_model_metrics.json"

    if not model_path.exists():
        raise FileNotFoundError(
            f"Trained yield model not found at {model_path}. "
            f"Run train_model.py first to generate it."
        )

    model = joblib.load(model_path)

    metrics: Dict[str, Any] = {}
    if metrics_path.exists():
        with open(metrics_path, "r", encoding="utf-8") as f:
            metrics = json.load(f)

    return model, metrics


def build_feature_frame(args: argparse.Namespace, model) -> pd.DataFrame:
    """
    Build a single-row DataFrame of features that matches the model's
    expected input columns. Any missing fields are left as NaN so the
    pipeline's imputers can handle them.
    """
    row = {name: np.nan for name in CANONICAL_FEATURES}

    row["district"] = args.district
    row["crop"] = args.crop
    row["season"] = args.season
    row["irrigation_type"] = args.irrigation_type
    row["area_hectares"] = args.area_hectares

    if args.rainfall is not None:
        row["rainfall"] = args.rainfall
    if args.temperature is not None:
        row["temperature"] = args.temperature
    if args.humidity is not None:
        row["humidity"] = args.humidity

    if args.n is not None:
        row["n"] = args.n
    if args.p is not None:
        row["p"] = args.p
    if args.k is not None:
        row["k"] = args.k
    if args.ph is not None:
        row["ph"] = args.ph

    df = pd.DataFrame([row])

    # Align with the feature set the model was actually trained on
    try:
        feature_names = list(model.feature_names_in_)
        df = df[feature_names]
    except AttributeError:
        # Older sklearn versions may not provide feature_names_in_
        pass

    return df


def derive_yield_category(
    yield_per_hectare: float, metrics: Dict[str, Any]
) -> str:
    """Classify yield into Low / Medium / High based on training quantiles if available."""
    quantiles = metrics.get("yield_quantiles") or {}
    low_q = quantiles.get("low")
    high_q = quantiles.get("high")

    if low_q is not None and high_q is not None:
        if yield_per_hectare < low_q:
            return "Low"
        if yield_per_hectare < high_q:
            return "Medium"
        return "High"

    # Fallback heuristic if quantiles are not available
    if yield_per_hectare < 2:
        return "Low"
    if yield_per_hectare < 4:
        return "Medium"
    return "High"


def format_confidence(metrics: Dict[str, Any]) -> float:
    """
    Use R² from training as a simple proxy for model confidence (0–100%).
    This is not a probability but gives a quick quality signal.
    """
    r2 = metrics.get("r2")
    if r2 is None:
        return 0.0
    return max(0.0, min(100.0, float(r2) * 100.0))


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Predict crop yield for Karnataka using the trained RandomForest model.\n"
            "Make sure you have run train_model.py first."
        )
    )

    parser.add_argument("--district", required=True, help="District name in Karnataka")
    parser.add_argument("--crop", required=True, help="Crop name")
    parser.add_argument("--season", default=None, help="Season (e.g., Kharif, Rabi)")
    parser.add_argument(
        "--irrigation_type",
        default=None,
        help="Irrigation type (e.g., Rainfed, Irrigated)",
    )
    parser.add_argument(
        "--area_hectares",
        type=float,
        required=True,
        help="Cultivated area in hectares",
    )

    parser.add_argument(
        "--rainfall",
        type=float,
        default=None,
        help="Recent or expected rainfall (mm) for the season (optional)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Average temperature (°C) during the growing period (optional)",
    )
    parser.add_argument(
        "--humidity",
        type=float,
        default=None,
        help="Average relative humidity (%) during the growing period (optional)",
    )

    parser.add_argument("--n", type=float, default=None, help="Soil Nitrogen value (N)")
    parser.add_argument("--p", type=float, default=None, help="Soil Phosphorus value (P)")
    parser.add_argument("--k", type=float, default=None, help="Soil Potassium value (K)")
    parser.add_argument("--ph", type=float, default=None, help="Soil pH value")

    args = parser.parse_args()

    backend_dir = Path(__file__).resolve().parent
    model, metrics = load_model_and_metadata(backend_dir)

    features_df = build_feature_frame(args, model)

    predicted_yield_per_hectare = float(model.predict(features_df)[0])
    total_yield = predicted_yield_per_hectare * float(args.area_hectares)

    confidence_pct = format_confidence(metrics)
    yield_category = derive_yield_category(predicted_yield_per_hectare, metrics)

    # REQUIRED CONSOLE OUTPUT FORMAT (no JSON)
    print(f"Predicted Yield: {predicted_yield_per_hectare:.2f} tons/hectare")
    print(f"Model Confidence: {confidence_pct:.1f}%")
    print(f"Yield Category: {yield_category}")
    print(f"Total Expected Production: {total_yield:.2f} tons")


if __name__ == "__main__":
    main()

