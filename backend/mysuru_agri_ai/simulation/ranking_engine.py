import logging
from typing import Dict, Tuple

import numpy as np
import pandas as pd


logger = logging.getLogger(__name__)


def rank_strategies(results: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    """
    Rank simulated scenarios by predicted yield and compute impact analytics.

    Returns:
        ranked: DataFrame sorted by predicted yield (descending).
        analytics: dictionary containing summary statistics used by the advisory.
    """
    ranked = results.sort_values("predicted_yield", ascending=False).reset_index(
        drop=True
    )

    top5 = ranked.head(5).copy()

    # Irrigation impact analysis
    irrigation_stats = (
        ranked.groupby("Irrigation")["predicted_yield"]
        .agg(["mean", "count"])
        .reset_index()
    )

    # Seasonal impact analysis
    seasonal_stats = (
        ranked.groupby("Season")["predicted_yield"]
        .agg(["mean", "count"])
        .reset_index()
    )

    # Compare best irrigation method to second best
    irrigation_stats_sorted = irrigation_stats.sort_values("mean", ascending=False)
    if len(irrigation_stats_sorted) >= 2:
        best_irrig = irrigation_stats_sorted.iloc[0]
        second_irrig = irrigation_stats_sorted.iloc[1]
        irrig_improvement_pct = (
            (best_irrig["mean"] - second_irrig["mean"]) / second_irrig["mean"] * 100.0
            if second_irrig["mean"] > 0
            else np.nan
        )
    else:
        best_irrig = second_irrig = None
        irrig_improvement_pct = np.nan

    # Yield difference analysis between best and worst
    best_yield = ranked["predicted_yield"].max()
    worst_yield = ranked["predicted_yield"].min()
    yield_diff = best_yield - worst_yield

    # Lowest risk strategy (based on risk_level then highest yield)
    risk_order = {"Low": 0, "Moderate": 1, "High": 2}
    ranked["risk_rank"] = ranked["risk_level"].map(risk_order).fillna(1)
    lowest_risk = ranked.sort_values(
        ["risk_rank", "predicted_yield"], ascending=[True, False]
    ).head(1)

    analytics = {
        "scenario_count": int(len(ranked)),
        "top5": top5,
        "irrigation_stats": irrigation_stats_sorted,
        "seasonal_stats": seasonal_stats.sort_values("mean", ascending=False),
        "irrigation_improvement_pct": (
            float(irrig_improvement_pct) if not np.isnan(irrig_improvement_pct) else None
        ),
        "best_irrigation": best_irrig.to_dict() if best_irrig is not None else None,
        "second_irrigation": second_irrig.to_dict()
        if second_irrig is not None
        else None,
        "best_yield": float(best_yield),
        "worst_yield": float(worst_yield),
        "yield_difference": float(yield_diff),
        "lowest_risk": lowest_risk,
    }

    ranked = ranked.drop(columns=["risk_rank"])
    return ranked, analytics

