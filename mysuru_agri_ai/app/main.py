import logging
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, validator

from ..advisory.advisory_engine import build_advisory_report
from ..pipeline.predict import batch_predict, load_latest_model
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


class SimulationRequest(BaseModel):
    crop: List[str] = Field(..., description="List of crop names.")
    season: List[str] = Field(..., description="List of seasons (e.g. Kharif, Rabi).")
    soil_type: List[str] = Field(..., description="List of soil types.")
    irrigation: List[str] = Field(..., description="List of irrigation methods.")
    area: List[float] = Field(..., description="List of field areas (e.g. acres).")
    district: Optional[str] = Field(
        default="Mysuru",
        description="Target district; future-ready for other Karnataka districts.",
    )

    @validator("crop", "season", "soil_type", "irrigation", "area")
    def non_empty(cls, v: List):  # type: ignore[override]
        if not v:
            raise ValueError("At least one value must be provided.")
        return v


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


@app.post(
    "/simulate",
    response_model=str,
    response_description="Plain-text advisory report.",
)
def simulate(request: SimulationRequest) -> str:
    """
    Run a full scenario simulation for the given selection of crops, seasons,
    soil types, irrigation systems, and areas. Returns a human-readable
    advisory report rather than JSON.
    """
    try:
        bundle = load_latest_model()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Failed to load model: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load model.")

    try:
        scenarios = generate_scenarios(
            {
                "crop": request.crop,
                "season": request.season,
                "soil_type": request.soil_type,
                "irrigation": request.irrigation,
                "area": request.area,
            },
            district=request.district or "Mysuru",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Failed to generate scenarios: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate scenarios.")

    try:
        prediction_results = batch_predict(bundle, scenarios)
        ranked, analytics = rank_strategies(prediction_results)
        advisory = build_advisory_report(
            district=request.district or "Mysuru",
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

