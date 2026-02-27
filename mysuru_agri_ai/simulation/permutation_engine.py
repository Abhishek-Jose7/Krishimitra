import logging
from itertools import product
from pathlib import Path
from typing import Dict, Iterable, List

import pandas as pd

from ..pipeline.preprocess import load_crop_management_data


logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


def extract_option_space(
    data_season_path: Path | None = None,
    district: str = "Mysuru",
) -> Dict[str, List]:
    """
    Extract dynamic dropdown options from the crop management dataset.

    Returns a dictionary with unique values for crop, season, soil_type,
    irrigation, and area.
    """
    if data_season_path is None:
        data_season_path = DATA_DIR / "data_season.csv"

    df = load_crop_management_data(data_season_path, district=district)

    options = {
        "crop": sorted(df["Crops"].dropna().unique().tolist()),
        "season": sorted(df["Season"].dropna().unique().tolist()),
        "soil_type": (
            sorted(df["Soil type"].dropna().unique().tolist())
            if "Soil type" in df.columns
            else []
        ),
        "irrigation": (
            sorted(df["Irrigation"].dropna().unique().tolist())
            if "Irrigation" in df.columns
            else []
        ),
        "area": sorted(df["Area"].dropna().unique().tolist())
        if "Area" in df.columns
        else [],
    }
    return options


def _validate_combinations_against_history(
    combos: pd.DataFrame, history: pd.DataFrame
) -> pd.DataFrame:
    """
    Keep only those crop–season–soil–irrigation combos that have support in
    the historical data, to avoid unrealistic pairs.
    """
    key_cols = [c for c in ["Crops", "Season", "Soil type", "Irrigation"] if c in history.columns]
    hist_keys = (
        history[key_cols]
        .drop_duplicates()
        .assign(_valid=1)
    )
    merged = combos.merge(hist_keys, on=key_cols, how="left")
    valid = merged[merged["_valid"] == 1].drop(columns=["_valid"])
    return valid


def generate_scenarios(
    selected: Dict[str, Iterable],
    max_combinations: int | None = None,
    district: str = "Mysuru",
) -> pd.DataFrame:
    """
    Generate a structured list of farming scenarios by taking the Cartesian
    product of user-selected options, and validate them against historical
    crop-season patterns.
    """
    data_season_path = DATA_DIR / "data_season.csv"
    history = load_crop_management_data(data_season_path, district=district)

    crops = list(selected.get("crop", []))
    seasons = list(selected.get("season", []))
    soils = list(selected.get("soil_type", []))
    irrigations = list(selected.get("irrigation", []))
    areas = list(selected.get("area", []))

    if not (crops and seasons and soils and irrigations and areas):
        raise ValueError("All of crop, season, soil_type, irrigation, and area must be provided.")

    combo_iter = product(crops, seasons, soils, irrigations, areas)
    rows = []
    for idx, (c, s, soil, irr, area) in enumerate(combo_iter):
        if max_combinations is not None and idx >= max_combinations:
            logger.warning(
                "Reached max_combinations=%d; truncating scenario generation.",
                max_combinations,
            )
            break
        rows.append(
            {
                "Crops": str(c).title(),
                "Season": str(s).title(),
                "Soil type": str(soil).title(),
                "Irrigation": str(irr).title(),
                "Area": area,
            }
        )

    scenarios = pd.DataFrame(rows)
    scenarios = _validate_combinations_against_history(scenarios, history)

    if scenarios.empty:
        raise ValueError(
            "No valid scenarios generated; please adjust your selections to match "
            "historical crop–season–soil–irrigation combinations."
        )

    logger.info("Generated %d valid farming scenarios.", len(scenarios))
    return scenarios

