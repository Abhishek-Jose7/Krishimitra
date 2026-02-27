from typing import Dict

import numpy as np
import pandas as pd


def _format_strategy_row(row: pd.Series) -> str:
    area_txt = ""
    total_txt = ""
    if "Area" in row.index and pd.notna(row["Area"]):
        area_txt = f", area {float(row['Area']):g} acres"
    if "estimated_total_yield" in row.index and pd.notna(row["estimated_total_yield"]):
        total_txt = f" (~{float(row['estimated_total_yield']):.2f} tons total)"

    soil = row.get("Soil type", "unspecified soil")
    conf = float(row.get("confidence", 0.0))
    if conf >= 80.0:
        tail = f"(confidence {conf:.0f}%, risk {row['risk_level']})"
    else:
        tail = f"(risk {row['risk_level']})"

    return (
        f"{row['Crops']} - {row['Season']} - {row['Irrigation']} on {soil}"
        f"{area_txt} - {row['predicted_yield']:.2f} tons/acre{total_txt} "
        f"{tail}"
    )


def build_advisory_report(
    district: str,
    ranked: pd.DataFrame,
    analytics: Dict,
) -> str:
    """
    Convert ranked scenarios and analytics into a human-readable advisory
    suitable for farmers and extension officers.
    """
    scenario_count = analytics.get("scenario_count", len(ranked))
    top5 = analytics["top5"]
    best_row = ranked.iloc[0]
    lowest_risk_df = analytics["lowest_risk"]
    lowest_risk_row = lowest_risk_df.iloc[0]

    best_crop = best_row["Crops"]
    best_season = best_row["Season"]
    best_irrig = best_row["Irrigation"]
    best_soil = best_row.get("Soil type", "unspecified soil")
    best_yield = best_row["predicted_yield"]
    best_conf = float(best_row.get("confidence", 0.0))
    best_risk = best_row["risk_level"]

    yield_difference = analytics.get("yield_difference")

    irrig_improvement_pct = analytics.get("irrigation_improvement_pct")
    best_irrigation = analytics.get("best_irrigation")
    second_irrig = analytics.get("second_irrigation")

    lines = []
    lines.append(
        f"After analysing {scenario_count} possible farming configurations for {district} district:"
    )
    lines.append("")
    lines.append(
        "The highest predicted yield is achieved by cultivating "
        f"{best_crop} during the {best_season} season using {best_irrig.lower()} irrigation "
        f"on {best_soil.lower()}."
    )
    if best_conf >= 80.0:
        conf_fragment = f"(confidence {best_conf:.0f}%, risk level: {best_risk})."
    else:
        conf_fragment = f"(risk level: {best_risk})."

    lines.append(
        f"Estimated yield: {best_yield:.2f} tons/acre {conf_fragment}"
    )
    lines.append("")

    # Evidence note (useful for districts without labeled training data).
    if "evidence_level" in ranked.columns:
        low = ranked[ranked["evidence_level"] == "Low"]
        if not low.empty:
            d_list = (
                sorted(set(low["district"].astype(str).str.title().tolist()))
                if "district" in low.columns
                else []
            )
            if d_list:
                lines.append(
                    "Evidence note: Some scenarios are outside the labeled training data "
                    f"coverage for {', '.join(d_list)}. Treat these recommendations as "
                    "indicative and validate with local agronomy guidance."
                )
                lines.append("")

    if lowest_risk_row.name != best_row.name:
        lines.append(
            "From a risk-management perspective, the most stable configuration is:"
        )
        lines.append(
            f"{lowest_risk_row['Crops']} in {lowest_risk_row['Season']} with "
            f"{lowest_risk_row['Irrigation'].lower()} irrigation on "
            f"{str(lowest_risk_row.get('Soil type', 'unspecified soil')).lower()}, "
            f"delivering approximately {lowest_risk_row['predicted_yield']:.2f} tons/acre "
            f"with risk classified as {lowest_risk_row['risk_level']}."
        )
        lines.append("")

    if (
        irrig_improvement_pct is not None
        and best_irrigation is not None
        and second_irrig is not None
        and np.isfinite(irrig_improvement_pct)
    ):
        lines.append(
            f"{best_irrigation['Irrigation']} irrigation improves yield by approximately "
            f"{irrig_improvement_pct:.1f}% compared to {second_irrig['Irrigation']} systems "
            "under similar crop and seasonal conditions."
        )

    seasonal_stats = analytics.get("seasonal_stats")
    if seasonal_stats is not None and not seasonal_stats.empty:
        top_season = seasonal_stats.iloc[0]
        lines.append(
            f"Across all crops in the simulation, the {top_season['Season']} season "
            f"offers the strongest average yield at {top_season['mean']:.2f} tons/acre."
        )

    if yield_difference is not None:
        lines.append(
            f"The spread between the best and weakest simulated strategies is "
            f"around {yield_difference:.2f} tons/acre, highlighting the importance "
            "of aligning crop choice, season, irrigation method, and soil management."
        )

    lines.append("")
    lines.append("Top 5 recommended strategies:")
    for idx, row in top5.iterrows():
        lines.append(f"{idx + 1}. {_format_strategy_row(row)}")

    lines.append("")
    lines.append(
        "Advisory note: These projections are based on historical weather, soil "
        "nutrient profiles, and recorded management practices in Mysuru. Farmers "
        "should adapt these recommendations to their specific field conditions, "
        "water availability, and market demand, and review them with local "
        "agronomists where possible."
    )

    return "\n".join(lines)

