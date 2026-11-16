"""
C3 - Price & Freight Integrity Risk (plan 4.3, 5.2 step 5; Q3).

    C3_i = (flagged outlier lines of manufacturer i) / (total scored lines of manufacturer i)

* IsolationForest(contamination=0.05, random_state=42) fitted WITHIN each SCMS product group on
  [unit price, freight cost / line value, line item value] (log-scaled: all three are heavily skewed).
* Lines with missing freight ("Freight Included in Commodity Cost", "Invoiced Separately") cannot be scored and are
  counted separately; product groups with fewer than MIN_GROUP_ROWS lines are not modelled.
* Probation suppliers default to C3 = 0.0 (plan 4.3). Non-probation suppliers use the SCMS lines linked to them by
  the Layer 2 entity resolution.
* Exports the 3 most anomalous lines (distinct vendors) with a plain-English reason, for slide 4.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

log = logging.getLogger("pharmashield.layer3.c3")
FEATURES = ["unit_price", "freight_to_value_ratio", "line_item_value"]
CONTAMINATION = 0.05
SEED = 42
MIN_GROUP_ROWS = 50


def score_lines(scms: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    d = scms.copy()
    for c in FEATURES:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    complete = d[FEATURES].notna().all(axis=1) & (d["unit_price"] > 0) & (d["line_item_value"] > 0) \
        & (d["freight_to_value_ratio"] >= 0)
    d["c3_scored"], d["c3_flagged"], d["c3_anomaly_score"] = False, False, np.nan
    d["c3_unscored_reason"] = np.where(complete, "", "missing_or_zero_price_or_freight")
    groups = []
    for grp, g in d[complete].groupby("product_group"):
        if len(g) < MIN_GROUP_ROWS:
            d.loc[g.index, "c3_unscored_reason"] = f"product_group_too_small(<{MIN_GROUP_ROWS})"
            groups.append({"product_group": grp, "lines": len(g), "modelled": False})
            continue
        X = np.log1p(g[FEATURES].to_numpy())
        iso = IsolationForest(contamination=CONTAMINATION, random_state=SEED, n_estimators=300).fit(X)
        d.loc[g.index, "c3_scored"] = True
        d.loc[g.index, "c3_flagged"] = iso.predict(X) == -1
        d.loc[g.index, "c3_anomaly_score"] = -iso.score_samples(X)          # higher = more anomalous
        for c in FEATURES:
            d.loc[g.index, f"group_median_{c}"] = g[c].median()
        groups.append({"product_group": grp, "lines": len(g), "modelled": True,
                       "flagged": int(d.loc[g.index, "c3_flagged"].sum())})
    return d, groups


def explain(row: pd.Series) -> str:
    """Plain-English audit reason for slide 4, relative to the line's own product group."""
    parts = []
    fr, fr_med = row["freight_to_value_ratio"], row.get("group_median_freight_to_value_ratio")
    if pd.notna(fr_med) and fr_med > 0 and fr >= 3 * fr_med:
        freight = row.get("freight_usd")
        amount = f"${freight:,.0f} freight on a ${row['line_item_value']:,.2f} line" if pd.notna(freight) else "freight"
        parts.append(f"{amount}: freight = {fr:,.1f}x the goods value (group median {fr_med:.2f}x)")
    up, up_med = row["unit_price"], row.get("group_median_unit_price")
    if pd.notna(up_med) and up_med > 0 and (up >= 3 * up_med or up <= up_med / 3):
        parts.append(f"unit price ${up:,.2f} vs group median ${up_med:,.2f}")
    lv, lv_med = row["line_item_value"], row.get("group_median_line_item_value")
    if pd.notna(lv_med) and lv_med > 0 and (lv <= lv_med / 100 or lv >= 100 * lv_med):
        parts.append(f"line value ${lv:,.2f} vs group median ${lv_med:,.0f}")
    return "; ".join(parts) or "unusual combination of unit price, freight share and line value"


def anomaly_examples(d: pd.DataFrame, n: int = 3) -> pd.DataFrame:
    flagged = d[d["c3_flagged"]].sort_values("c3_anomaly_score", ascending=False)
    ex = flagged.drop_duplicates("vendor").head(n).copy()
    ex["why_flagged"] = ex.apply(explain, axis=1)
    cols = ["id", "vendor", "manufacturing_site", "product_group", "item_description", "scheduled_delivery_date",
            "shipment_mode", "line_item_quantity", "unit_price", "line_item_value", "freight_usd",
            "freight_to_value_ratio", "c3_anomaly_score", "why_flagged"]
    return ex[[c for c in cols if c in ex.columns]]


def run(scms: pd.DataFrame, matrix: pd.DataFrame, scms_links: pd.DataFrame) -> dict:
    d, groups = score_lines(scms)
    by_lab = scms_links.groupby("labeler_key")["external_name"].agg(set)
    rows = []
    for _, r in matrix.iterrows():
        k = r["manufacturer_id"]
        names = by_lab.get(k, set())
        mine = d[d["vendor"].astype(str).isin(names) | d["manufacturing_site"].astype(str).isin(names)]
        scored = mine[mine["c3_scored"]]
        if bool(r["is_probation"]):
            c3, basis = 0.0, "probation default 0.0 (plan 4.3)"
        elif len(scored):
            c3, basis = round(float(scored["c3_flagged"].mean()), 4), "isolation_forest_share_of_flagged_lines"
        else:
            c3, basis = 0.0, "no scorable linked lines (freight missing) - 0.0, flagged"
        rows.append({"manufacturer_id": k, "C3_price_integrity": c3, "c3_basis": basis,
                     "c3_linked_lines": int(len(mine)), "c3_scored_lines": int(len(scored)),
                     "c3_flagged_lines": int(scored["c3_flagged"].sum()) if len(scored) else 0})
    panel = pd.DataFrame(rows)
    summary = {
        "model": f"IsolationForest(contamination={CONTAMINATION}, random_state={SEED}) per product group",
        "features": FEATURES, "lines_total": int(len(d)), "lines_scored": int(d["c3_scored"].sum()),
        "lines_flagged": int(d["c3_flagged"].sum()),
        "unscored_reasons": d.loc[~d["c3_scored"], "c3_unscored_reason"].value_counts().to_dict(),
        "product_groups": groups,
        "panel_makers_with_model_based_c3": int((panel["c3_basis"] == "isolation_forest_share_of_flagged_lines").sum()),
    }
    line_cols = ["id", "vendor", "manufacturing_site", "product_group", "unit_price", "freight_to_value_ratio",
                 "line_item_value", "c3_scored", "c3_flagged", "c3_anomaly_score", "c3_unscored_reason"]
    return {"panel": panel, "metrics": summary, "examples": anomaly_examples(d), "lines": d[line_cols]}
