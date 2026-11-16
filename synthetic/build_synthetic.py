#!/usr/bin/env python3
"""
PharmaShield GCC - synthetic view (decision S4: the professor asked for synthetic data where no evidence exists).

    python synthetic/build_synthetic.py          # after Layer 1 and Layer 3 (needs the REAL score table)

What it does
  1. Draws one synthetic value per gap from the approved ranges in synthetic/reference/synthetic_ranges.csv
     (fixed random seed, so every run gives the same values). Every value carries the range id it came from.
  2. Copies the REAL score table and re-scores only what those values touch, with the SAME code:
       C1 cost        + synthetic air freight per vial                     (cost formula: % above the cheapest)
       C2 delivery    the trained XGBoost model predicts on the synthetic shipping profile and delivery history
                      (the model is trained on the same real USAID data as always; nothing is fitted on synthetic data)
       C3 billing     Isolation Forest (plan settings) on synthetic invoice lines of the established suppliers;
                      new suppliers keep the plan's 0
       C4 compliance  + 0.20 x the contract reader's score on the 11 synthetic contracts already in the repo
       C5 route       synthetic Hormuz / Gulf-airspace share for air cargo
       capacity       synthetic monthly vials per factory; probation from synthetic past deliveries to this buyer
  3. Writes data/processed/suppliers_matrix_synthetic.csv (same locked schema) and synthetic/outputs/*.
     The real table data/processed/suppliers_matrix.csv is never written.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "layer3_engines"))
from engines import c2_delivery, c3_anomaly  # noqa: E402

SEED = 42
RANGES = ROOT / "synthetic" / "reference" / "synthetic_ranges.csv"
OUT = ROOT / "synthetic" / "outputs"
MATRIX_REAL = ROOT / "data" / "processed" / "suppliers_matrix.csv"
MATRIX_SYN = ROOT / "data" / "processed" / "suppliers_matrix_synthetic.csv"
INTERIM = ROOT / "layer1_ingestion" / "data" / "interim"
ESTABLISHED_MIN_US_SHARE = 9.0            # % of 2025 US Medicaid carboplatin volume (decision S4, R10)
INCOTERMS = {"EXW": 0.58, "DDP": 0.26, "FCA": 0.08, "CIP": 0.08}          # R2
FREIGHT_RANGE_BY_COUNTRY = {"India": "R5a", "Netherlands": "R5b", "Switzerland": "R5b", "Australia": "R5c"}
# one delivery = three real presentations of carboplatin 10 mg/mL; weight factor relative to the 45 mL vial
PRESENTATIONS = [(50, 0.10, 0.35), (150, 0.30, 0.55), (450, 0.60, 1.00)]   # (mg, share of vials, weight factor)
log = logging.getLogger("pharmashield.synthetic")


def ranges() -> pd.DataFrame:
    return pd.read_csv(RANGES).set_index("id")


def _u(rng, r: pd.DataFrame, rid: str) -> float:
    return float(rng.uniform(float(r.at[rid, "low"]), float(r.at[rid, "high"])))


def _ui(rng, r: pd.DataFrame, rid: str) -> int:
    return int(rng.integers(int(r.at[rid, "low"]), int(r.at[rid, "high"]) + 1))


# --------------------------------------------------------------------------- #
# 1. draw the synthetic values
# --------------------------------------------------------------------------- #
def draw_inputs(m: pd.DataFrame, r: pd.DataFrame, seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    e = m[m["eligible_for_ranking"].astype(bool)].sort_values("manufacturer_id").copy()
    share = e["us_medicaid_2025_volume_share_pct"].fillna(0.0).astype(float)
    e["us_share"] = share.values

    # ---- per factory: things that belong to the building and its route ----
    fac = e.groupby("source_plant_group").agg(country=("manufacturing_country", "first"),
                                              us_share=("us_share", "sum")).sort_index()
    top = float(fac["us_share"].max())
    lo8, hi8 = float(r.at["R8", "low"]), float(r.at["R8", "high"])
    rows = {}
    for g, f in fac.iterrows():
        rid = FREIGHT_RANGE_BY_COUNTRY.get(f["country"])
        rate = _u(rng, r, rid) if rid else np.nan                         # Unknown country: filled below
        kg = _u(rng, r, "R3")
        hormuz = _u(rng, r, "R9") if f["country"] != "Unknown" else np.nan
        if f["us_share"] > 0:                                             # R8: scaled by real US market share
            cap = (lo8 + (hi8 - lo8) * f["us_share"] / top) * rng.uniform(0.9, 1.1)
            cap_basis = f"scaled by real US market share {f['us_share']:.1f}% (+/-10%)"
        else:
            cap = rng.uniform(lo8, 4000.0)
            cap_basis = "no US Medicaid sales: uniform 1500-4000"
        rows[g] = {"freight_rate_usd_per_kg": rate, "freight_rate_range": rid or "median of known factories",
                   "kg_per_vial": round(kg, 4), "hormuz_air_share": hormuz,
                   "factory_capacity_vials": int(round(min(hi8, max(lo8, cap)) / 100.0) * 100),
                   "capacity_basis": cap_basis}
    ff = pd.DataFrame.from_dict(rows, orient="index")
    known = ff["freight_rate_usd_per_kg"].notna()
    ff.loc[~known, "freight_rate_usd_per_kg"] = ff.loc[known, "freight_rate_usd_per_kg"].median()  # evidence rule:
    ff.loc[ff["hormuz_air_share"].isna(), "hormuz_air_share"] = ff["hormuz_air_share"].median()    # neutral = median
    ff["freight_rate_usd_per_kg"] = ff["freight_rate_usd_per_kg"].round(3)
    ff["hormuz_air_share"] = ff["hormuz_air_share"].round(4)

    # ---- per supplier: things that belong to the seller's contract and history ----
    out = []
    for _, s in e.iterrows():
        f = ff.loc[s["source_plant_group"]]
        established = s["us_share"] >= ESTABLISHED_MIN_US_SHARE
        term = str(rng.choice(list(INCOTERMS), p=list(INCOTERMS.values())))
        vials = _ui(rng, r, "R4")
        deliveries = _ui(rng, r, "R10") if established else 0
        on_time = round(_u(rng, r, "R11"), 4) if established else np.nan
        err = round(_u(rng, r, "R7"), 4) if established else np.nan
        price = float(s["C1_landed_cost_usd_raw"])                       # real price + real insurance per vial
        freight = round(f["freight_rate_usd_per_kg"] * f["kg_per_vial"], 4)
        out.append({
            "manufacturer_id": s["manufacturer_id"], "factory_group": s["source_plant_group"],
            "country": s["manufacturing_country"], "established": bool(established),
            "us_market_share_pct": round(float(s["us_share"]), 1),
            "shipment_mode": "Air", "vendor_inco_term": term, "shipment_vials": vials,
            "kg_per_vial": f["kg_per_vial"], "shipment_weight_kg": round(vials * f["kg_per_vial"], 1),
            "freight_rate_usd_per_kg": f["freight_rate_usd_per_kg"], "freight_rate_range": f["freight_rate_range"],
            "freight_usd_per_vial": freight, "freight_to_value_ratio": round(freight / price, 6),
            "hormuz_air_share": f["hormuz_air_share"], "factory_capacity_vials": int(f["factory_capacity_vials"]),
            "capacity_basis": f["capacity_basis"], "past_deliveries": deliveries,
            "late_deliveries": int(round(deliveries * (1 - on_time))) if established else 0,
            "on_time_rate": on_time, "invoice_error_rate": err,
            "contract_risk": float(s["contract_risk_demo_only"]),
        })
    return pd.DataFrame(out)


def invoice_lines(inp: pd.DataFrame, seed: int = SEED) -> pd.DataFrame:
    """Synthetic invoices for established suppliers: one invoice per past delivery, three lines (50/150/450 mg vials).
    Errors are injected at the supplier's drawn rate (R7); the truth is kept in injected_error for evaluation."""
    rng = np.random.default_rng(seed + 1)
    rows = []
    for _, s in inp[inp["established"]].iterrows():
        per_mg = (s["freight_usd_per_vial"] / s["freight_to_value_ratio"]) / 450.0       # real price per mg
        for k in range(int(s["past_deliveries"])):
            total = int(round(s["shipment_vials"] * rng.uniform(0.8, 1.2)))
            for mg, part, wf in PRESENTATIONS:
                qty = max(1, int(round(total * part)))
                unit = per_mg * mg * (1 + rng.normal(0, 0.02))
                value = qty * unit
                f2v = s["freight_usd_per_vial"] * wf * qty / value * (1 + rng.normal(0, 0.10))
                kind = ""
                if rng.random() < s["invoice_error_rate"]:
                    kind = str(rng.choice(["overpriced", "freight_overcharge", "value_mismatch"]))
                    if kind == "overpriced":
                        unit *= rng.uniform(1.5, 3.0)
                        value = qty * unit
                    elif kind == "freight_overcharge":
                        f2v *= rng.uniform(3.0, 6.0)
                    else:
                        value *= rng.uniform(5.0, 20.0)
                rows.append({"id": f"SYN-{s['manufacturer_id'][:4]}-{k + 1:02d}-{mg}",
                             "vendor": s["manufacturer_id"], "manufacturing_site": s["factory_group"],
                             "product_group": "CARBOPLATIN_INJ (synthetic)", "delivery": k + 1, "vial_mg": mg,
                             "line_item_quantity": qty, "unit_price": round(unit, 4),
                             "line_item_value": round(value, 2), "freight_to_value_ratio": round(max(f2v, 0.0), 6),
                             "injected_error": kind})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# 2. re-score with the same code
# --------------------------------------------------------------------------- #
def cost_mark(raw: pd.Series) -> pd.Series:
    """Decision S4 (cost formula): how much more expensive than the cheapest rankable supplier, capped at 1.
    On the real data it gives exactly the plan's min-max result (generics 0, Avyxa 1)."""
    lo = float(raw.min())
    return np.minimum(1.0, (raw - lo) / lo).round(4)


def build(m: pd.DataFrame, inp: pd.DataFrame, lines: pd.DataFrame, scms: pd.DataFrame, inf: pd.DataFrame) -> dict:
    s = m.copy()
    elig = s["eligible_for_ranking"].astype(bool)
    i = inp.set_index("manufacturer_id")
    ids = s.loc[elig, "manufacturer_id"]
    at = lambda col: s.loc[elig, "manufacturer_id"].map(i[col])

    # capacity and history
    s.loc[elig, "monthly_capacity_units"] = at("factory_capacity_vials").astype(int)
    s.loc[elig, "capacity_source"] = "synthetic (R8)"
    s.loc[elig, "internal_historical_deliveries"] = at("past_deliveries").astype(int)
    total = s["scms_historical_shipments"].fillna(0) + s["internal_historical_deliveries"].fillna(0)
    s.loc[elig, "is_probation"] = (total[elig] < 5).values

    # C1: real price + real insurance + synthetic freight
    s.loc[elig, "C1_landed_cost_usd_raw"] = (s.loc[elig, "C1_landed_cost_usd_raw"].astype(float)
                                             + at("freight_usd_per_vial")).round(4)
    s.loc[elig, "freight_basis"] = "synthetic air freight (R3 x R5)"
    s.loc[elig, "C1_landed_cost"] = cost_mark(s.loc[elig, "C1_landed_cost_usd_raw"].astype(float))

    # C5: synthetic air-route share, plan formula
    share = at("hormuz_air_share").astype(float)
    lpi = s.loc[elig, "lpi_score"].astype(float)
    s.loc[elig, "hormuz_air_share"] = share
    s.loc[elig, "C5_route_exposure"] = (np.minimum(1.0, share) * (1 - lpi / 5)).round(4)
    s.loc[elig, "C5_route_exposure_crisis"] = (np.minimum(1.0, 1.5 * share) * (1 - lpi / 5)).round(4)

    # C2: same trained model, synthetic shipping profile + synthetic delivery history
    f = inf.copy()
    fx = f["manufacturer_id"].isin(ids)
    for c in ["shipment_mode", "vendor_inco_term", "freight_to_value_ratio"]:
        f.loc[fx, c] = f.loc[fx, "manufacturer_id"].map(i[c])
    f.loc[fx, "weight_kg"] = f.loc[fx, "manufacturer_id"].map(i["shipment_weight_kg"])
    n_real = f["site_prior_n_shipments"].fillna(0).astype(float)
    on_real = f["site_prior_on_time_rate"].fillna(0).astype(float) * n_real
    n_syn = f["manufacturer_id"].map(i["past_deliveries"]).fillna(0).astype(float)
    on_syn = (f["manufacturer_id"].map(i["past_deliveries"] - i["late_deliveries"])).fillna(0).astype(float)
    f["site_prior_n_shipments"] = n_real + n_syn
    f["site_prior_on_time_rate"] = np.where(f["site_prior_n_shipments"] > 0,
                                            (on_real + on_syn) / f["site_prior_n_shipments"].replace(0, np.nan), np.nan)
    f["inputs_fixed"] = fx
    c2 = c2_delivery.run(scms, f)
    p2 = c2_delivery.neutralise_unknown_country(c2["panel"], s).set_index("manufacturer_id")
    for c in ["C2_delivery_risk", "shap_top3_reasons", "c2_score_weighted_model", "site_prior_shipments",
              "shipment_profile", "c2_basis"]:
        s[c] = s["manufacturer_id"].map(p2[c]).where(s["manufacturer_id"].isin(p2.index), s.get(c))

    # C3: Isolation Forest (plan settings) on the synthetic invoices; new suppliers keep the plan's 0
    scored, _ = c3_anomaly.score_lines(lines)
    by = scored.groupby("vendor")["c3_flagged"].agg(["mean", "sum", "size"])
    c3 = []
    for _, r in s.loc[elig].iterrows():
        k = r["manufacturer_id"]
        if bool(r["is_probation"]):
            c3.append((0.0, "probation default 0.0 (plan 4.3)", 0, 0))
        else:
            c3.append((round(float(by.at[k, "mean"]), 4), "isolation_forest_on_synthetic_invoices",
                       int(by.at[k, "size"]), int(by.at[k, "sum"])))
    s.loc[elig, "C3_price_integrity"] = [x[0] for x in c3]
    s.loc[elig, "c3_basis"] = [x[1] for x in c3]
    s.loc[elig, "c3_scored_lines"] = [x[2] for x in c3]
    s.loc[elig, "c3_flagged_lines"] = [x[3] for x in c3]

    # C4: switch the contract term on (plan 4.3: + 0.20 x contract risk)
    s.loc[elig, "contract_risk"] = s.loc[elig, "contract_risk_demo_only"].astype(float)
    s.loc[elig, "contract_risk_source"] = "synthetic contract, scored in the synthetic view"
    s.loc[elig, "C4_compliance_risk"] = np.minimum(
        1.0, s.loc[elig, "C4_compliance_risk"].astype(float) + 0.20 * s.loc[elig, "contract_risk"]).round(4)

    s["data_view"] = np.where(elig, "synthetic", "real (not ranked)")
    inj = scored[scored["injected_error"] != ""]
    summary = {
        "seed": SEED, "established": sorted(inp.loc[inp["established"], "manufacturer_id"]),
        "c2_model_test_roc_auc_unchanged": c2["metrics"]["xgboost_test"]["roc_auc"],
        "c3_invoice_lines": int(len(scored)), "c3_flagged": int(scored["c3_flagged"].sum()),
        "c3_injected_errors": int(len(inj)), "c3_injected_errors_caught": int(inj["c3_flagged"].sum()),
    }
    return {"matrix": s, "lines": scored, "summary": summary}


def main() -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s | %(name)s | %(message)s")
    m = pd.read_csv(MATRIX_REAL)
    r = ranges()
    inp = draw_inputs(m, r)
    lines = invoice_lines(inp)
    res = build(m, inp, lines, pd.read_csv(INTERIM / "scms_shipments_clean.csv", low_memory=False),
                pd.read_csv(INTERIM / "panel_inference_features.csv"))
    OUT.mkdir(parents=True, exist_ok=True)
    inp.to_csv(OUT / "synthetic_inputs.csv", index=False)
    res["lines"][["id", "vendor", "manufacturing_site", "delivery", "vial_mg", "line_item_quantity", "unit_price",
                  "line_item_value", "freight_to_value_ratio", "injected_error", "c3_flagged",
                  "c3_anomaly_score"]].to_csv(OUT / "synthetic_invoice_lines.csv", index=False)
    (OUT / "synthetic_summary.json").write_text(json.dumps(res["summary"], indent=2))
    res["matrix"].to_csv(MATRIX_SYN, index=False)
    s = res["summary"]
    e = res["matrix"][res["matrix"]["eligible_for_ranking"].astype(bool)]
    print(f"synthetic score table: {MATRIX_SYN.relative_to(ROOT)} | established: {', '.join(s['established'])}")
    print(f"  invoices: {s['c3_invoice_lines']} lines, {s['c3_injected_errors']} injected errors, "
          f"{s['c3_injected_errors_caught']} caught by the billing model, {s['c3_flagged']} flagged in total")
    with pd.option_context("display.width", 200):
        print(e[["manufacturer_id", "is_probation", "monthly_capacity_units", "C1_landed_cost", "C2_delivery_risk",
                 "C3_price_integrity", "C4_compliance_risk", "C5_route_exposure"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
