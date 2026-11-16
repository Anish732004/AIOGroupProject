"""
Criteria weights (plan 4.2): pre-calibrated AHP per criticality tier, one-click modes, Shannon entropy, 50/50 blend.

AHP. The plan states the baseline weights per tier (Tier 1: C1 0.10, C2 0.30, C3 0.05, C4 0.30, C5 0.25) and says the
pairwise comparisons were done offline with CR < 0.10. The team has not supplied a pairwise survey, so the pairwise
matrix used here is the one IMPLIED by the plan's weights (a_ij = w_i / w_j). That matrix is perfectly consistent
(CR = 0) and returns exactly the plan's weights. `ahp_from_pairwise` accepts a real survey matrix when the team has one.

Modes (plan 4.2):  Normal = tier weights;  Crisis = +0.10 moved from C1 to C5;  Cost Focus = +0.10 moved from C5 to C1.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

CRITERIA = ["C1_landed_cost", "C2_delivery_risk", "C3_price_integrity", "C4_compliance_risk", "C5_route_exposure"]
SHORT = {c: c[:2] for c in CRITERIA}
RANDOM_INDEX = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45}   # Saaty
MODES = ("Normal", "Crisis", "Cost Focus")
MODE_SHIFT = 0.10


def tier_weights(tiers: pd.DataFrame, tier: int) -> pd.Series:
    row = tiers.loc[tiers["criticality_tier"].astype(int) == int(tier)].iloc[0]
    w = pd.Series([float(row[f"w_{c[:2]}"]) for c in CRITERIA], index=CRITERIA)
    if not np.isclose(w.sum(), 1.0):
        raise ValueError(f"tier {tier} weights sum to {w.sum()}, not 1")
    return w


def mode_weights(base: pd.Series, mode: str) -> pd.Series:
    """Plan 4.2 one-click modes. The shift is limited to what the donor criterion has (never negative)."""
    w = base.copy()
    if mode == "Normal":
        return w
    donor, receiver = (("C1_landed_cost", "C5_route_exposure") if mode == "Crisis"
                       else ("C5_route_exposure", "C1_landed_cost") if mode == "Cost Focus" else (None, None))
    if donor is None:
        raise ValueError(f"unknown mode {mode!r}; use one of {MODES}")
    move = min(MODE_SHIFT, float(w[donor]))
    w[donor] -= move
    w[receiver] += move
    return w.round(10)


def implied_pairwise(w: pd.Series) -> pd.DataFrame:
    """Pairwise matrix implied by a weight vector (a_ij = w_i / w_j). Zero weights are not representable in AHP,
    so they are floored at 1e-6 for the matrix only."""
    v = np.maximum(w.to_numpy(float), 1e-6)
    return pd.DataFrame(np.outer(v, 1 / v), index=w.index, columns=w.index)


def ahp_from_pairwise(a: pd.DataFrame) -> tuple[pd.Series, dict]:
    """Principal-eigenvector weights + Saaty consistency ratio for a pairwise comparison matrix."""
    m = a.to_numpy(float)
    vals, vecs = np.linalg.eig(m)
    k = int(np.argmax(vals.real))
    w = np.abs(vecs[:, k].real)
    w = w / w.sum()
    n = m.shape[0]
    lam = float(vals.real[k])
    ci = (lam - n) / (n - 1) if n > 1 else 0.0
    ri = RANDOM_INDEX.get(n, 1.49)
    cr = 0.0 if ri == 0 else ci / ri
    cr = 0.0 if abs(cr) < 1e-9 else cr
    return pd.Series(w, index=a.index), {"lambda_max": round(lam, 6), "CI": round(ci, 6), "RI": ri,
                                         "CR": round(cr, 6), "consistent (CR < 0.10)": cr < 0.10}


def informative(x: pd.DataFrame, tol: float = 1e-9) -> pd.Series:
    """A criterion carries information only if it differs between the makers being ranked (team decision 12)."""
    return (x.max() - x.min()) > tol


def entropy_weights(x: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
    """Shannon entropy weights from the decision matrix (plan 4.2).

    Each criterion is first rescaled 'higher = better' within the panel (r = (max - x) / (max - min)), the usual
    entropy-method step for lower-is-better criteria, so a tie at the best value does not look like 'no information'.
    Criteria that do not vary across the panel are excluded and get entropy weight 0 (team decision 12).
    Returns the weights and a table explaining each criterion.
    """
    n = len(x)
    info = informative(x)
    rows, d = [], {}
    for c in x.columns:
        if not info[c] or n < 2:
            rows.append({"criterion": c, "varies_across_makers": False, "entropy": np.nan, "divergence": 0.0})
            d[c] = 0.0
            continue
        r = (x[c].max() - x[c]) / (x[c].max() - x[c].min())
        p = r / r.sum()
        e = float(-(p[p > 0] * np.log(p[p > 0])).sum() / np.log(n))
        d[c] = 1.0 - e
        rows.append({"criterion": c, "varies_across_makers": True, "entropy": round(e, 4), "divergence": round(1 - e, 4)})
    d = pd.Series(d)
    w = d / d.sum() if d.sum() > 0 else d
    return w.reindex(x.columns), pd.DataFrame(rows)


def blend(ahp: pd.Series, ent: pd.Series, share_entropy: float = 0.5) -> pd.Series:
    """w = (1 - s) * AHP + s * Entropy (plan: s = 0.5). Re-normalised so the weights sum to 1."""
    w = (1 - share_entropy) * ahp + share_entropy * ent.reindex(ahp.index).fillna(0.0)
    return w / w.sum()
