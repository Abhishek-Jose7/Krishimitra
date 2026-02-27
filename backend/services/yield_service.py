from __future__ import annotations

import json
import logging
import os
import pickle
import random
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from services.weather_service import WeatherService
from mysuru_agri_ai.advisory.advisory_engine import build_advisory_report
from mysuru_agri_ai.pipeline.predict import ModelBundle, batch_predict, get_model_bundle
from mysuru_agri_ai.simulation.permutation_engine import (
    extract_option_space,
    generate_scenarios,
)
from mysuru_agri_ai.simulation.ranking_engine import rank_strategies

logger = logging.getLogger(__name__)


class DummyYieldModel:
    """Fallback dummy model for legacy yield prediction."""

    def predict(self, features):
        return [random.uniform(10, 50)]


class _CustomUnpickler(pickle.Unpickler):
    """Handles models pickled in __main__ context."""

    def find_class(self, module, name):
        if name == "DummyYieldModel":
            return DummyYieldModel
        return super().find_class(module, name)


class YieldService:
    """
    Legacy yield prediction service used by the price recommendation engine.

    This is kept for backward compatibility so existing endpoints relying on
    YieldService.predict_yield keep working, even as we introduce the new
    mysuru_agri_ai advisory pipeline.
    """

    _model = None
    _metrics: Dict[str, Any] = {}

    @classmethod
    def load_model(cls):
        if cls._model is None:
            base_dir = os.path.dirname(__file__)
            model_path = os.path.join(base_dir, "../models/yield_model.pkl")
            metrics_path = os.path.join(base_dir, "../models/yield_model_metrics.json")
            try:
                with open(model_path, "rb") as f:
                    cls._model = _CustomUnpickler(f).load()
                # Load metrics if available (used for confidence and yield category)
                if os.path.exists(metrics_path):
                    with open(metrics_path, "r", encoding="utf-8") as mf:
                        cls._metrics = json.load(mf)
            except FileNotFoundError:
                logger.warning("Yield model not found, using fallback DummyYieldModel()")
                cls._model = DummyYieldModel()
            except Exception as e:  # pragma: no cover - defensive
                logger.warning(f"Model load error: {e}, using fallback DummyYieldModel()")
                cls._model = DummyYieldModel()

    @staticmethod
    def predict_yield(data):
        YieldService.load_model()
        if not YieldService._model:
            return None

        # Core farmer / agronomy inputs coming from the app
        district = data.get("district")
        crop = data.get("crop")
        land_size = float(data.get("land_size", data.get("area_hectares", 0)))
        season = data.get("season")
        irrigation_type = data.get("irrigation_type")

        # Optional soil parameters if the app collects them
        n = data.get("n")
        p = data.get("p")
        k = data.get("k")
        ph = data.get("ph")

        # Optional sowing date (ISO string) – can be used to refine weather in the future
        sowing_date = data.get("sowing_date")

        # 1. Fetch Weather – pass season and sowing_date for future extensions
        weather = WeatherService.get_weather(district, season=season, sowing_date=sowing_date)

        # 2. Build model feature frame aligned with training pipeline
        row = {
            "district": district,
            "crop": crop,
            "season": season,
            "irrigation_type": irrigation_type,
            "area_hectares": land_size,
            "rainfall": weather.get("rainfall"),
            "temperature": weather.get("temp"),
            "humidity": weather.get("humidity"),
            "n": n,
            "p": p,
            "k": k,
            "ph": ph,
        }

        df = pd.DataFrame([row])
        # Align with model feature names if available
        try:
            feature_names = list(YieldService._model.feature_names_in_)
            df = df[feature_names]
        except Exception:
            pass

        # 3. Predict yield per hectare using the trained sklearn pipeline
        yield_per_hectare = float(YieldService._model.predict(df)[0])

        total_yield = yield_per_hectare * land_size

        # Store in DB if farmer_id is provided
        farmer_id = data.get("farmer_id")
        if farmer_id:
            from database.models import YieldPrediction
            from database.db import db

            try:
                prediction = YieldPrediction(
                    farmer_id=farmer_id,
                    crop=crop,
                    predicted_yield=total_yield,
                )
                db.session.add(prediction)
                db.session.commit()
            except Exception as e:  # pragma: no cover - defensive
                logger.warning(f"Failed to save prediction: {e}")
                # Don't fail the request, just log

        metrics = YieldService._metrics or {}
        confidence = YieldService._format_confidence(metrics)
        yield_category = YieldService._derive_yield_category(
            yield_per_hectare, metrics, crop, district
        )

        weather_condition = weather.get("condition", "current weather")
        explanation = (
            f"Based on {weather_condition} conditions in {district} for {season or 'the season'}, "
            f"the expected yield for {crop} on your farm looks {yield_category.lower()}."
        )

        return {
            "predicted_yield_per_hectare": round(yield_per_hectare, 2),
            "total_expected_production": round(total_yield, 2),
            "confidence": confidence,
            "yield_category": yield_category,
            "risk": "Low" if yield_category == "High" else "Moderate",
            "explanation_text": explanation,
        }

    @staticmethod
    def _format_confidence(metrics: Dict[str, Any]) -> float:
        """
        Use R² from training as a simple proxy for model confidence (0–100%).
        """
        r2 = metrics.get("r2")
        if r2 is None:
            return 0.0
        return round(max(0.0, min(100.0, float(r2) * 100.0)), 1)

    @staticmethod
    def _derive_yield_category(
        yield_per_hectare: float,
        metrics: Dict[str, Any],
        crop: str,
        district: str,
    ) -> str:
        """
        Classify yield into Low / Medium / High using per-crop quantiles
        when available, falling back to global quantiles or a heuristic.
        """
        # 1) Per-crop quantiles if present
        per_crop_q = (metrics.get("per_crop_yield_quantiles") or {}).get(crop or "")
        if per_crop_q:
            low_q = per_crop_q.get("low")
            high_q = per_crop_q.get("high")
            if low_q is not None and high_q is not None:
                if yield_per_hectare < low_q:
                    return "Low"
                if yield_per_hectate < high_q:  # type: ignore[name-defined]
                    return "Medium"
                return "High"

        # 2) Global quantiles
        q = metrics.get("yield_quantiles") or {}
        low_q = q.get("low")
        high_q = q.get("high")
        if low_q is not None and high_q is not None:
            if yield_per_hectare < low_q:
                return "Low"
            if yield_per_hectare < high_q:
                return "Medium"
            return "High"

        # 3) Fallback heuristic
        if yield_per_hectare < 2:
            return "Low"
        if yield_per_hectare < 4:
            return "Medium"
        return "High"


def _normalize_title(value: str | None, fallback: str | None = None) -> str:
    v = (value or fallback or "").strip()
    return v.title() if v else ""


def _ensure_bundle() -> ModelBundle:
    """
    Wrapper around mysuru_agri_ai's lazy model loader.
    Kept here so we can extend logging/metrics later if needed.
    """
    bundle = get_model_bundle()
    return bundle


def get_yield_advisory(user_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the Mysuru smart-yield simulation pipeline for a single
    configuration and return a human-readable advisory string.

    Expected keys in `user_input`:
      - district
      - crop
      - season
      - soil_type
      - irrigation
      - area
    """
    bundle = _ensure_bundle()

    district_raw = user_input.get("district") or "Mysuru"
    crop = user_input.get("crop")
    season = user_input.get("season")
    soil_type = user_input.get("soil_type")
    irrigation = user_input.get("irrigation")
    area = user_input.get("area")

    missing: List[str] = [
        name
        for name, val in [
            ("crop", crop),
            ("season", season),
            ("soil_type", soil_type),
            ("irrigation", irrigation),
            ("area", area),
        ]
        if val in (None, "")
    ]
    if missing:
        raise ValueError(f"Missing required fields for yield simulation: {', '.join(missing)}")

    try:
        area_val = float(area)
    except Exception as exc:  # pragma: no cover - defensive
        raise ValueError("`area` must be a numeric value.") from exc

    districts = [_normalize_title(str(district_raw), "Mysuru")]

    # Reuse the mysuru_agri_ai scenario generation so all
    # validation and historical checks stay centralised.
    scenarios = generate_scenarios(
        {
            "district": districts,
            "crop": [crop],
            "season": [season],
            "soil_type": [soil_type],
            "irrigation": [irrigation],
            "area": [area_val],
        },
        district=districts[0],
    )

    prediction_results = batch_predict(bundle, scenarios)
    ranked, analytics = rank_strategies(prediction_results)
    district_label = (
        ", ".join(sorted(set(scenarios["district"])))
        if "district" in scenarios.columns
        else districts[0]
    )
    advisory = build_advisory_report(
        district=district_label,
        ranked=ranked,
        analytics=analytics,
    )
    # Take the first scenario row (there is typically only one)
    row = prediction_results.iloc[0]
    summary = {
        "district": str(row.get("district", "")),
        "crop": str(row.get("Crops", "")),
        "season": str(row.get("Season", "")),
        "soil_type": str(row.get("Soil type", "")),
        "irrigation": str(row.get("Irrigation", "")),
        "area": float(row.get("Area", area_val)),
        "predicted_yield": float(row.get("predicted_yield", 0.0)),
        "ci_low": float(row.get("ci_low", 0.0)),
        "ci_high": float(row.get("ci_high", 0.0)),
        "confidence": float(row.get("confidence", 0.0)),
        "risk_level": str(row.get("risk_level", "")),
        "evidence_level": str(row.get("evidence_level", "")),
        "estimated_total_yield": float(
            row.get("estimated_total_yield", row.get("predicted_yield", 0.0) * area_val)
        ),
    }
    return {"advisory": advisory, "summary": summary}


def get_yield_options(district: str | None = None) -> Dict[str, Any]:
    """
    Expose dynamic option space (districts, crops, seasons, soil, irrigation, area)
    derived from mysuru_agri_ai datasets.
    """
    base_district = (district or "Mysuru").strip() or "Mysuru"
    opts = extract_option_space(district=base_district)
    return opts
