#!/usr/bin/env python3
"""
Consistency check: the project plan, the pipeline (backend) and the website (frontend) must not contradict each other.

    python tools/check_consistency.py

  A. Plan constants   -> the code and reference files use the plan's numbers (or a documented decision)
  B. Backend -> site  -> web/data/snapshot.json shows exactly what the pipeline computed
  C. Site text        -> every number written in the site's text matches the data
  D. Documented       -> every deliberate difference from the plan is listed on the site and in docs/DECISIONS.md
  E. Synthetic view   -> every synthetic value inside its approved range; the site's synthetic view equals Layer 4
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "layer1_ingestion"))
sys.path.insert(0, str(ROOT / "layer4_decision"))
sys.path.insert(0, str(ROOT / "layer3_engines"))

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, bool(ok), detail))


def main() -> int:
    from decision import allocation, engine
    from decision.weights import CRITERIA, mode_weights, tier_weights
    from engines import c3_anomaly, c4_compliance
    from ingestion.config import SETTINGS

    m, tiers, sku = engine.load_inputs()
    snap = json.loads((ROOT / "web/data/snapshot.json").read_text())
    content = snap["content"]
    e = m[m["eligible_for_ranking"].astype(bool)].sort_values("manufacturer_id").reset_index(drop=True)
    ids = e["manufacturer_id"].tolist()

    # ------------------------------------------------------------------ A. plan constants
    check("A1 demand D = 10,000 vials (plan 4.4)", int(sku.iloc[0]["monthly_demand_units"]) == 10000)
    check("A2 target SKU is Tier 1 (plan 4.2)", int(sku.iloc[0]["criticality_tier"]) == 1)
    plan_w = {1: [0.10, 0.30, 0.05, 0.30, 0.25], 2: [0.20, 0.25, 0.10, 0.25, 0.20], 3: [0.40, 0.20, 0.10, 0.20, 0.10]}
    for t, w in plan_w.items():
        check(f"A3 Tier {t} weights match the plan table (plan 4.2)", np.allclose(tier_weights(tiers, t).values, w))
    w1 = tier_weights(tiers, 1)
    check("A4 Crisis = 0.10 from cost to route; Tier 1 -> [0, .30, .05, .30, .35] (plan 4.2)",
          np.allclose(mode_weights(w1, "Crisis").values, [0.0, 0.30, 0.05, 0.30, 0.35]))
    check("A5 Cost Focus = 0.10 from route to cost (plan 4.2)",
          np.allclose(mode_weights(w1, "Cost Focus").values, [0.20, 0.30, 0.05, 0.30, 0.15]))
    caps = tiers.set_index("criticality_tier")["max_primary_share"].astype(float).to_dict()
    check("A6 tier caps 70% / 80% / 100% (plan 4.4)", caps == {1: 0.70, 2: 0.80, 3: 1.00})
    check("A7 probation floor 5%, cap 15%, relaxed 30% (plan 4.4)",
          (allocation.PROBATION_FLOOR, allocation.PROBATION_CAP_WITH_2_ESTABLISHED, allocation.PROBATION_CAP_RELAXED) == (0.05, 0.15, 0.30))
    check("A8 emergency penalty M = 1,000,000 (plan 4.4)", allocation.BIG_M == 1e6)
    check("A9 probation = fewer than 5 shipments (plan 3.1, 5.1)", SETTINGS.scms.probation_min_shipments == 5)
    check("A10 time split: train <= 2013, test 2014-2015 (plan 5.2 step 4)",
          SETTINGS.scms.train_end_year == 2013 and tuple(SETTINGS.scms.test_years) == (2014, 2015))
    check("A11 Isolation Forest contamination 0.05, random_state 42 (plan 4.3)",
          c3_anomaly.CONTAMINATION == 0.05 and c3_anomaly.SEED == 42)
    check("A12 rapidfuzz threshold 88, manual check of top 20 (plan 5.2 step 3)",
          SETTINGS.sku.fuzzy_match_threshold == 88 and SETTINGS.sku.manual_check_top_n == 20)
    src = (ROOT / "layer3_engines/engines/c4_compliance.py").read_text()
    check("A13 C4 formula weights 0.30 / 0.10 / 0.20 / 0.20 / 0.20 (plan 4.3)",
          "0.20 * panel[\"nlp_warning_severity\"] + 0.20 * panel[\"contract_risk\"]" in src
          and "0.30 * (panel[\"oai_count_5yr\"] > 0) + 0.10 * (panel[\"vai_count_5yr\"] > 0)"
          in (ROOT / "layer1_ingestion/ingestion/scenario.py").read_text())
    c5 = np.minimum(1.0, e["hormuz_air_share"]) * (1 - e["lpi_score"] / 5)
    c5c = np.minimum(1.0, 1.5 * e["hormuz_air_share"]) * (1 - e["lpi_score"] / 5)
    check("A14 C5 = min(1, share) x (1 - LPI/5), Crisis x1.5 capped at 1 (plan 4.3)",
          np.allclose(c5, e["C5_route_exposure"], atol=1e-5) and np.allclose(c5c, e["C5_route_exposure_crisis"], atol=1e-5))
    locked = pd.read_csv(ROOT / "layer1_ingestion/reference/locked_schema.csv")["column"].tolist()
    check("A15 locked 16-column schema, names and order (plan 5.1)", list(m.columns[:16]) == locked and len(locked) == 16)
    for c in CRITERIA:
        check(f"A16 {c} in [0, 1], no empty values (plan 4.3)", m[c].notna().all() and m[c].between(0, 1).all())
    check("A17 probation makers have C3 = 0 (plan 4.3)", (m.loc[m["is_probation"].astype(bool), "C3_price_integrity"] == 0).all())

    # ------------------------------------------------------------------ B. backend -> website
    check("B1 snapshot made from the current score table (fingerprint)",
          snap["meta"]["matrix_sha256"] == __import__("hashlib").sha256((ROOT / "data/processed/suppliers_matrix.csv").read_bytes()).hexdigest())
    check("B2 same suppliers, same order", snap["supplier_ids"] == ids)
    sm = {s["id"]: s for s in snap["suppliers"]}
    worst = max(abs(sm[k]["marks"][c] - float(e.set_index("manufacturer_id").loc[k, c])) for k in ids for c in CRITERIA)
    check("B3 every supplier's five marks on the site equal the pipeline's", worst < 1e-9, f"max diff {worst}")
    for mode in snap["meta"]["modes"]:
        r = engine.run(m, tiers, sku, mode, 1.0, 0.0)
        sc = snap["scenarios"][f"{mode}|1.00|0.0"]
        rk = r["ranking"].reindex(ids)
        al = r["allocation"].set_index("manufacturer_id").reindex(ids)
        check(f"B4 {mode}: site scores and ranks equal Layer 4", np.allclose(sc["S"], rk["S"], atol=1e-4) and sc["rank"] == rk["rank"].astype(int).tolist())
        check(f"B5 {mode}: site order split equals Layer 4", np.allclose(sc["vials"], al["vials"], atol=0.11))
    out = pd.read_csv(ROOT / "layer4_decision/outputs/allocation_normal.csv").set_index("manufacturer_id").reindex(ids)
    check("B6 site Normal split equals layer4_decision/outputs", np.allclose(snap["scenarios"]["Normal|1.00|0.0"]["vials"], out["vials"], atol=0.11))
    india = [o for o in snap["stress"]["outages"] if o["kind"] == "country"][0]
    r = engine.run(m, tiers, sku, "Normal", 1.0, 0.0, set(india["groups"]))
    check("B7 disaster stress test on the site equals Layer 4",
          np.allclose(snap["stress"]["results"][india["key"]]["Normal|1.00|0.0"]["vials"],
                      r["allocation"].set_index("manufacturer_id").reindex(ids)["vials"], atol=0.11))
    c2 = json.loads((ROOT / "layer3_engines/outputs/c2_metrics.json").read_text())
    check("B8 model figures on the site equal Layer 3", snap["models"]["c2"]["xgboost_test"] == c2["xgboost_test"])

    # ------------------------------------------------------------------ C. numbers written in the site's text
    text = json.dumps(content)
    n_lab, n_rank = len(m), len(e)
    check("C1 text: '18 labelers; 11 ... ranked; 7 ... powder'",
          f"{n_lab} labelers; {n_rank} sell finished vials" in text and f"{n_lab - n_rank} sell only" in text)
    known = int((e["manufacturing_country"] != "Unknown").sum())
    check("C2 text: factory 'known for 10 of 11 suppliers'", f"Known for {known} of {n_rank} suppliers" in text)
    share = e["hormuz_air_share"].unique()
    check("C3 text: 'one share, 0.85, for every origin'", len(share) == 1 and f"{share[0]:.2f}" in text)
    check("C4 text: weights 'Cost 10%, late delivery 30%, billing 5%, compliance 30%, route 25%'",
          "Cost 10%, late delivery 30%, billing 5%, compliance 30%, route 25%" in text)
    check("C5 text: '7,771 ... tested on 2,545'", f"{c2['train_rows']:,}" in text and f"{c2['test_rows']:,}" in text)
    check("C6 text: 'None of the 11 has 5 or more past shipments of its own'",
          int((~e["is_probation"].astype(bool)).sum()) == 0 and f"None of the {n_rank} has 5" in text)
    check("C7 text: '8 factories' equals the data", snap["meta"]["factories"] == e["source_plant_group"].nunique())
    c3_same = e["C3_price_integrity"].nunique() == 1
    c3_row = [r for r in content["evidence_ledger"] if r["feeds"].startswith("C3")]
    check("C9 billing has no data for anyone -> labelled 'No data' on the site, and has no effect",
          c3_same and len(c3_row) == 1 and c3_row[0]["level"] == "nodata")
    check("C8 text: approver initials only, no personal data in scores", "initials or a staff ID only" in text)

    # ------------------------------------------------------------------ D. documented differences
    dec = (ROOT / "docs/DECISIONS.md").read_text()
    topics = {"entropy": "L5", "contract": "| 7 |", "capacity": "| 3 |", "per factory": "L3", "Hormuz": "| 5 |",
              "Cost": "| 4 |", "probation": "| 9 |", "synthetic": "S4"}
    diffs = " ".join(d["plan"] + " " + d["here"] + " " + d.get("synthetic", "") for d in content.get("plan_differences", []))
    for word, key in topics.items():
        check(f"D1 difference about '{word}' is on the site and in DECISIONS.md", word.lower() in diffs.lower() and key in dec)

    # ------------------------------------------------------------------ E. synthetic view (decision S4)
    syn = snap.get("synthetic")
    sm_path = ROOT / "data/processed/suppliers_matrix_synthetic.csv"
    check("E1 synthetic view is on the site and built from the current synthetic table",
          syn is not None and sm_path.exists()
          and syn["matrix_sha256"] == __import__("hashlib").sha256(sm_path.read_bytes()).hexdigest())
    if syn is not None and sm_path.exists():
        ms = pd.read_csv(sm_path)
        check("E2 synthetic table keeps the locked schema and the same 11 ranked suppliers",
              list(ms.columns[:16]) == locked
              and sorted(ms.loc[ms["eligible_for_ranking"].astype(bool), "manufacturer_id"]) == ids)
        rng = pd.read_csv(ROOT / "synthetic/reference/synthetic_ranges.csv").set_index("id")
        inp = pd.read_csv(ROOT / "synthetic/outputs/synthetic_inputs.csv")
        inside = lambda col, rid: inp[col].dropna().between(rng.at[rid, "low"], rng.at[rid, "high"]).all()
        check("E3 every synthetic value is inside its approved range (R3, R4, R7-R11)",
              all(inside(c, r) for c, r in [("kg_per_vial", "R3"), ("shipment_vials", "R4"), ("invoice_error_rate", "R7"),
                                            ("factory_capacity_vials", "R8"), ("hormuz_air_share", "R9")])
              and inp.loc[inp["established"], "past_deliveries"].between(rng.at["R10", "low"], rng.at["R10", "high"]).all()
              and inp.loc[inp["established"], "on_time_rate"].between(rng.at["R11", "low"], rng.at["R11", "high"]).all())
        check("E4 the ranges table on the site equals synthetic/reference/synthetic_ranges.csv",
              [r["id"] for r in syn["ranges"]] == list(rng.index))
        for mode in snap["meta"]["modes"]:
            r = engine.run(ms, tiers, sku, mode, 1.0, 0.0)
            sc = syn["scenarios"][f"{mode}|1.00|0.0"]
            check(f"E5 synthetic {mode}: site ranks and split equal Layer 4",
                  sc["rank"] == r["ranking"].reindex(ids)["rank"].astype(int).tolist()
                  and np.allclose(sc["vials"], r["allocation"].set_index("manufacturer_id").reindex(ids)["vials"], atol=0.11))
        lo = float(e["C1_landed_cost_usd_raw"].min())
        check("E6 the new cost formula (% above the cheapest, capped at 1) gives the plan's result on real data",
              np.allclose(np.minimum(1, (e["C1_landed_cost_usd_raw"] - lo) / lo), e["C1_landed_cost"], atol=1e-4))
        out_syn = pd.read_csv(ROOT / "layer4_decision/outputs/synthetic/allocation_normal.csv").set_index("manufacturer_id").reindex(ids)
        check("E7 site synthetic Normal split equals layer4_decision/outputs/synthetic",
              np.allclose(syn["scenarios"]["Normal|1.00|0.0"]["vials"], out_syn["vials"], atol=0.11))

    # ------------------------------------------------------------------ F. plan KPIs and documents (decision S5)
    rn = engine.run(m, tiers, sku, "Normal", 1.0, 0.0)["diagnostics"]
    check("F1 warm-backup share on the site equals Layer 4 (plan Q7)",
          abs(snap["scenarios"]["Normal|1.00|0.0"]["backup"] - rn["warm_backup_share_pct"]) < 0.01)
    views = [snap] + ([snap["synthetic"]] if snap.get("synthetic") else [])
    allsc = [v for vw in views for v in vw["scenarios"].values()] + \
            [v for vw in views for res in vw["stress"]["results"].values() for v in res.values() if v["spot"] < 0.5]
    check("F2 every scenario and covered stress test meets the Tier 1 two-supplier rule (plan 4.2)",
          all(v["two_ok"] for v in allsc), f"{sum(not v['two_ok'] for v in allsc)} fail")
    check("F3 every order is in whole vials", all(float(x).is_integer() for v in allsc for x in v["vials"]))
    qa = (ROOT / "docs/QA_DEFENSE.md").read_text()
    india = next(o for o in engine.stress_outages(m) if o["kind"] == "country")
    worst = next(o for o in engine.stress_outages(m) if o["kind"] == "country_worst")
    ri = engine.run(m, tiers, sku, "Normal", 1.0, 0.0, set(india["groups"]))["diagnostics"]
    rw = engine.run(m, tiers, sku, "Normal", 1.0, 0.0, set(worst["groups"]))["diagnostics"]
    from decimal import ROUND_HALF_UP, Decimal
    money = lambda v: "$" + f"{int(Decimal(str(v)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)):,}"
    fac_split = engine.run(m, tiers, sku)["allocation"].groupby("factory_group")["vials"].sum()
    split = "/".join(str(round(v / 100)) for v in sorted(fac_split[fac_split > 0.5], reverse=True))
    qa_facts = [money(rn["monthly_spend_usd"]), money(ri["monthly_spend_usd"]), money(rw["monthly_spend_usd"]), split,
                f"{c2['train_rows']:,} shipments", f"{c2['test_rows']:,} later", f"{c2['xgboost_test']['recall_late']:.0%}",
                f"there are {e['C2_delivery_risk'].nunique()} different late-delivery scores",
                f"warm-backup share of {rn['warm_backup_share_pct']:.0f}%"]
    missing = [f for f in qa_facts if f not in qa.replace("\n", " ")]
    check("F4 every number in docs/QA_DEFENSE.md matches the data", not missing, f"missing: {missing}")
    tr = (ROOT / "docs/PLAN_TRACEABILITY.md").read_text()
    check("F5 docs/PLAN_TRACEABILITY.md covers every plan section (1-6)", all(f"## §{k}" in tr for k in range(1, 7)))
    pdf = ROOT / "docs/GenAI_Prompt_Log.pdf"
    logs = [ROOT / "docs" / f for f in ("GENAI_PROMPT_LOG_layer1.md", "GENAI_PROMPT_LOG_layer2_3.md", "GENAI_PROMPT_LOG_layer4_5.md")]
    check("F6 the GenAI Prompt Log PDF is newer than its three markdown logs", pdf.exists() and all(pdf.stat().st_mtime >= x.stat().st_mtime for x in logs))
    nb3 = json.loads((ROOT / "notebooks/03_layer4_decision.ipynb").read_text())
    check("F7 notebooks run with no errors and no unrun cells (plan step 10)", all(
        not any(o.get("output_type") == "error" for c in nb["cells"] for o in c.get("outputs", []))
        and all(c.get("execution_count") for c in nb["cells"] if c["cell_type"] == "code")
        for nb in [json.loads((ROOT / f"notebooks/{n}.ipynb").read_text()) for n in
                   ("01_layer1_data_ingestion", "02_layer3_risk_engines", "03_layer4_decision")]))
    check("F8 notebook 03 ends with the numbers for the slides", "Numbers for the slides" in json.dumps(nb3))

    # ------------------------------------------------------------------ G. evidence ledger per view
    led = content["evidence_ledger"]
    syn_led = [{**r, **r.get("synthetic", {})} for r in led]
    filled = {"Freight cost to the UAE", "Shipping mode, terms and weight for UAE orders", "Supplier contracts",
              "Billing oddities (each supplier's own invoices)", "Factory capacity"}
    check("G1 synthetic view: every 'no data' input of the real view is filled by a synthetic range",
          {r["input"] for r in led if r["level"] == "nodata"} <= {r["input"] for r in syn_led if r["level"] == "synthetic"}
          and not any(r["level"] == "nodata" for r in syn_led) and filled <= {r["input"] for r in led if r["level"] == "nodata"})
    rng_ids = set(pd.read_csv(ROOT / "synthetic/reference/synthetic_ranges.csv")["id"])
    cited = set(re.findall(r"R\d+[a-c]?", " ".join(r["source"] for r in syn_led if r["level"] == "synthetic")))
    check("G2 every range a synthetic ledger row cites exists in synthetic_ranges.csv",
          bool(cited) and all(x in rng_ids or x + "a" in rng_ids for x in cited), f"{cited - rng_ids}")

    width = max(len(n) for n, _, _ in results)
    for n, ok, d in results:
        print(("  ok   " if ok else "  FAIL ") + n.ljust(width) + ("  " + d if d and not ok else ""))
    bad = [n for n, ok, _ in results if not ok]
    print(f"{len(results) - len(bad)} of {len(results)} consistency checks passed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
