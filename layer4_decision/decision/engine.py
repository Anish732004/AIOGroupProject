"""
Layer 4 engine: weights -> TOPSIS ranking -> order split, for one mode. Used by run_decision.py and the cockpit.

Team decisions applied (docs/DECISIONS.md):
  L1  lambda (risk dial) is an input; default 1.0
  L2  5% probation minimum only if the maker is chosen (binary variable)
  L3  concentration caps per FACTORY (source_plant_group), not per name on the box
  L5  ranking driven by the board's tier (AHP) weights; entropy share is an input, default 0 (plan's live slider)
  12  criteria that do not vary across the rankable makers get no entropy weight
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .allocation import allocate
from .topsis import topsis
from .weights import CRITERIA, ahp_from_pairwise, blend, entropy_weights, implied_pairwise, mode_weights, tier_weights

ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / "data" / "processed" / "suppliers_matrix.csv"
TIERS = ROOT / "layer1_ingestion" / "reference" / "criticality_tiers.csv"
SKU = ROOT / "layer1_ingestion" / "reference" / "sku_master.csv"
DEFAULT_LAMBDA = 1.0
DEFAULT_ENTROPY_SHARE = 0.0


def load_inputs(matrix_path: Path = MATRIX) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    m = pd.read_csv(matrix_path)
    missing = [c for c in CRITERIA if m[c].isna().any()]
    if missing:
        raise ValueError(f"{missing} are empty - run Layer 3 (layer3_engines/run_engines.py) after Layer 1")
    return m, pd.read_csv(TIERS), pd.read_csv(SKU)


def decision_matrix(m: pd.DataFrame, mode: str) -> pd.DataFrame:
    """Rankable makers only (eligible_for_ranking). Crisis mode uses the stressed route column (plan 4.2)."""
    e = m[m["eligible_for_ranking"].astype(bool)].set_index("manufacturer_id")
    x = e[CRITERIA].astype(float).copy()
    if mode == "Crisis":
        x["C5_route_exposure"] = e["C5_route_exposure_crisis"].astype(float)
    return x


def run(m: pd.DataFrame, tiers: pd.DataFrame, sku: pd.DataFrame, mode: str = "Normal",
        lam: float = DEFAULT_LAMBDA, entropy_share: float = DEFAULT_ENTROPY_SHARE,
        offline_factories: set | None = None) -> dict:
    """offline_factories: stress test (natural disaster) - factory groups (source_plant_group) that cannot ship.
    The ranking is unchanged (a disaster does not change a supplier's quality); only the order split re-solves."""
    if not 0 <= entropy_share <= 0.5:
        raise ValueError("entropy share must be between 0 and 0.5 (plan: at most 50/50)")
    if lam < 0:
        raise ValueError("lambda must be >= 0")
    s = sku.iloc[0]
    tier = int(s["criticality_tier"])
    demand = int(s["monthly_demand_units"])
    tier_row = tiers.loc[tiers["criticality_tier"].astype(int) == tier].iloc[0]

    base = tier_weights(tiers, tier)
    ahp_w = mode_weights(base, mode)
    ahp_check_w, ahp_check = ahp_from_pairwise(implied_pairwise(base))
    x = decision_matrix(m, mode)
    ent_w, ent_table = entropy_weights(x)
    w = blend(ahp_w, ent_w, entropy_share)

    rank = topsis(x, w)
    e = m[m["eligible_for_ranking"].astype(bool)].set_index("manufacturer_id")
    rank = rank.join(e[["labeler_name_fda", "factory_name", "source_plant_group", "manufacturing_country",
                        "is_probation", "C1_landed_cost_usd_raw", "monthly_capacity_units"]])
    rank = rank.join(x.add_prefix("value_"))
    alloc_in = pd.DataFrame({
        "manufacturer_id": rank.index, "S": rank["S"].values,
        "landed_cost_usd": rank["C1_landed_cost_usd_raw"].values,
        "is_probation": rank["is_probation"].astype(bool).values,
        "factory_group": rank["source_plant_group"].values,
        "monthly_capacity_units": rank["monthly_capacity_units"].values,
    })
    res = allocate(alloc_in, demand, float(tier_row["max_primary_share"]), lam, offline_factories)
    weights = pd.DataFrame({"AHP (board, this mode)": ahp_w, "Entropy (information only)": ent_w,
                            "Used for ranking": w}).round(4)
    weights.index.name = "criterion"
    return {
        "mode": mode, "lambda": lam, "entropy_share": entropy_share, "tier": tier, "demand": demand,
        "weights": weights, "entropy_table": ent_table, "ranking": rank.sort_values(["rank", "S"]),
        "allocation": res["allocation"], "diagnostics": res["diagnostics"],
        "ahp_consistency": {"weights_from_implied_matrix": ahp_check_w.round(6).to_dict(), **ahp_check,
                            "note": "pairwise matrix implied by the plan's tier weights (no team survey supplied)"},
    }
