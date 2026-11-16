"""
Zero-guarded TOPSIS (plan 4.4). All criteria are lower-is-better and scaled to [0, 1].

  r_ij = x_ij / sqrt(sum_k x_kj^2)        (r_ij = 0 when the column norm is 0)
  v_ij = w_j * r_ij
  A+_j = min_i v_ij  (ideal best)        A-_j = max_i v_ij  (ideal worst)
  S_i  = D-_i / (D+_i + D-_i + 1e-12)    higher S = better supplier; (1 - S) = composite risk
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def topsis(x: pd.DataFrame, w: pd.Series) -> pd.DataFrame:
    x = x.astype(float)
    if x.isna().any().any():
        raise ValueError(f"decision matrix has empty cells: {x.columns[x.isna().any()].tolist()}")
    norm = np.sqrt((x ** 2).sum())
    r = x.divide(norm.replace(0, np.nan)).fillna(0.0)
    v = r * w.reindex(x.columns).fillna(0.0)
    best, worst = v.min(), v.max()
    d_plus = np.sqrt(((v - best) ** 2).sum(axis=1))
    d_minus = np.sqrt(((v - worst) ** 2).sum(axis=1))
    s = d_minus / (d_plus + d_minus + 1e-12)
    out = pd.DataFrame({"S": s.round(6), "composite_risk": (1 - s).round(6),
                        "D_plus": d_plus.round(6), "D_minus": d_minus.round(6)})
    out["rank"] = out["S"].rank(ascending=False, method="min").astype(int)
    # contribution of each criterion to the distance from the ideal (for the "why" explanation)
    contrib = (v - best) ** 2
    share = contrib.div(contrib.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    for c in x.columns:
        out[f"gap_share_{c[:2]}"] = share[c].round(4)
    return out
