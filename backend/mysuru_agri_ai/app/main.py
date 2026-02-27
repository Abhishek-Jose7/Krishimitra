import logging
from typing import Dict, List, Optional, Union

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, validator

from ..advisory.advisory_engine import build_advisory_report
from ..pipeline.predict import ModelBundle, batch_predict, load_latest_model
from ..simulation.permutation_engine import (
    extract_option_space,
    generate_scenarios,
)
from ..simulation.ranking_engine import rank_strategies


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Mysuru Smart Yield Simulation & Optimization Engine",
    description=(
        "Precision agriculture decision-support API for simulating crop, season, "
        "soil, and irrigation strategies in Mysuru district."
    ),
    version="1.0.0",
)


def _normalize_title(v: str) -> str:
    return str(v).strip().title()


def _get_model_bundle() -> ModelBundle:
    """
    Dependency that returns a cached model bundle (loaded once per process).
    """
    bundle = getattr(app.state, "model_bundle", None)
    if bundle is not None:
        return bundle

    try:
        bundle = load_latest_model()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Failed to load model: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load model.")

    app.state.model_bundle = bundle
    return bundle


class SimulationRequest(BaseModel):
    district: Union[str, List[str], None] = Field(
        default="Mysuru",
        description="District(s) to simulate, e.g. Mysuru, Pune.",
    )
    crop: List[str] = Field(..., description="List of crop names.")
    season: List[str] = Field(..., description="List of seasons (e.g. Kharif, Rabi).")
    soil_type: List[str] = Field(..., description="List of soil types.")
    irrigation: List[str] = Field(..., description="List of irrigation methods.")
    area: List[float] = Field(..., description="List of field areas (e.g. acres).")

    @validator("crop", "season", "soil_type", "irrigation", "area")
    def non_empty(cls, v: List):  # type: ignore[override]
        if not v:
            raise ValueError("At least one value must be provided.")
        return v

    @validator("district")
    def normalize_district(cls, v):  # type: ignore[override]
        if v is None:
            return ["Mysuru"]
        if isinstance(v, str):
            return [v]
        if isinstance(v, list) and v:
            return v
        return ["Mysuru"]


class YieldPredictionRequest(BaseModel):
    district: str = Field(default="Mysuru", description="District name (e.g. Mysuru, Pune).")
    crop: str = Field(..., description="Crop name.")
    season: str = Field(..., description="Season (e.g. Kharif, Rabi, Summer).")
    soil_type: str = Field(..., description="Soil type.")
    irrigation: str = Field(..., description="Irrigation method.")
    area: float = Field(..., gt=0, description="Field area in acres.")

    # Optional overrides (if you have real-time observed values).
    Rainfall: Optional[float] = Field(default=None, description="Rainfall (mm).")
    Temperature: Optional[float] = Field(default=None, description="Temperature (C).")
    Humidity: Optional[float] = Field(default=None, description="Humidity (%).")
    N: Optional[float] = Field(default=None, description="Soil Nitrogen.")
    P: Optional[float] = Field(default=None, description="Soil Phosphorus.")
    K: Optional[float] = Field(default=None, description="Soil Potassium.")
    ph: Optional[float] = Field(default=None, description="Soil pH.")


@app.get("/options", response_model=Dict[str, List])
def get_options(district: str = "Mysuru") -> Dict[str, List]:
    """
    Return dynamic option space derived from the underlying CSV data.
    """
    try:
        return extract_option_space(district=district)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Failed to extract options: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to extract options.")


@app.get("/model-info", response_model=Dict)
def model_info(bundle: ModelBundle = Depends(_get_model_bundle)) -> Dict:
    """
    Return basic metadata for the currently loaded yield model.
    """
    meta = bundle.metadata or {}
    return {
        "model_name": meta.get("model_name"),
        "version": meta.get("version"),
        "target_transform": meta.get("target_transform"),
        "feature_spec": meta.get("feature_spec"),
        "per_district": meta.get("per_district"),
    }


@app.post("/predict-yield", response_model=Dict)
def predict_yield(
    request: YieldPredictionRequest,
    bundle: ModelBundle = Depends(_get_model_bundle),
) -> Dict:
    """
    Predict yield for a single scenario (JSON in, JSON out).
    """
    try:
        row: Dict[str, object] = {
            "district": _normalize_title(request.district),
            "Crops": _normalize_title(request.crop),
            "Season": _normalize_title(request.season),
            "Soil type": _normalize_title(request.soil_type),
            "Irrigation": _normalize_title(request.irrigation),
            "Area": float(request.area),
        }

        for k in ("Rainfall", "Temperature", "Humidity", "N", "P", "K", "ph"):
            v = getattr(request, k)
            if v is not None:
                row[k] = float(v)

        scenarios = pd.DataFrame([row])
        results = batch_predict(bundle, scenarios)
        out = results.iloc[0].to_dict()
        return jsonable_encoder(out)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Yield prediction failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Yield prediction failed; see logs for details.",
        )


@app.post(
    "/simulate",
    response_model=str,
    response_description="Plain-text advisory report.",
)
def simulate(
    request: SimulationRequest,
    bundle: ModelBundle = Depends(_get_model_bundle),
) -> str:
    """
    Run a full scenario simulation for the given selection of crops, seasons,
    soil types, irrigation systems, and areas. Returns a human-readable
    advisory report rather than JSON.
    """
    try:
        districts = [str(d).strip().title() for d in (request.district or ["Mysuru"])]
        scenarios = generate_scenarios(
            {
                "district": districts,
                "crop": request.crop,
                "season": request.season,
                "soil_type": request.soil_type,
                "irrigation": request.irrigation,
                "area": request.area,
            },
            district=districts[0] if districts else "Mysuru",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Failed to generate scenarios: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate scenarios.")

    try:
        prediction_results = batch_predict(bundle, scenarios)
        ranked, analytics = rank_strategies(prediction_results)
        district_label = (
            ", ".join(sorted(set(scenarios["district"])))
            if "district" in scenarios.columns
            else (districts[0] if districts else "Mysuru")
        )
        advisory = build_advisory_report(
            district=district_label,
            ranked=ranked,
            analytics=analytics,
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Simulation pipeline failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Simulation pipeline failed; see logs for details.",
        )

    return advisory

