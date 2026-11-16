#!/usr/bin/env python3
"""
Export the pipeline's results into ONE JSON file for the Vercel showcase site (web/data/snapshot.json).

    python tools/export_web_snapshot.py        # after Layer 1, Layer 3 (and Layer 4 is run here, per scenario)

The site is static: it cannot run Python. So every scenario the reader can choose (3 modes x risk-dial steps x
entropy-share steps) is solved HERE by the real Layer 4 engine and stored. The site only looks results up, so its
numbers are identical to the pipeline's. Re-run this script whenever the pipeline is re-run.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "layer4_decision"))
from decision import engine  # noqa: E402
from decision.weights import CRITERIA, MODES  # noqa: E402

INTERIM = ROOT / "layer1_ingestion" / "data" / "interim"
L1_REF = ROOT / "layer1_ingestion" / "reference"
QUALITY = ROOT / "layer1_ingestion" / "data" / "quality" / "quality_report.json"
L3 = ROOT / "layer3_engines" / "outputs"
WEB = ROOT / "web"
SYN_DIR = ROOT / "synthetic"
SYN_MATRIX = ROOT / "data" / "processed" / "suppliers_matrix_synthetic.csv"
LAMBDAS = [round(0.25 * i, 2) for i in range(13)]          # 0 .. 3 in steps of 0.25
ENTROPY = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]                    # 0% .. 50%
SOURCE_LABELS = {
    "scms": "USAID SCMS delivery history (training data)", "ghsc_psm": "USAID GHSC-PSM (optional, skipped)",
    "internal_gpo": "Internal GPO purchase and delivery data", "openfda_ndc": "openFDA NDC Directory (who may sell)",
    "openfda_label": "Official drug labels (manufacturing site)", "openfda_recalls": "openFDA recalls, last 5 years",
    "openfda_shortages": "openFDA drug shortages", "fda_inspections": "FDA inspection classifications, last 5 years",
    "worldbank": "World Bank logistics and stability scores", "warning_letters": "FDA warning letters (sample)",
    "contracts": "Supplier contracts (synthetic)", "scenario": "Evidence files and scenario settings",
    "suppliers_matrix": "Final supplier score table",
}


def clean(v):
    """JSON-safe scalar."""
    if v is None:
        return None
    if isinstance(v, (np.bool_, bool)):
        return bool(v)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        return None if (np.isnan(v) or np.isinf(v)) else float(v)
    if isinstance(v, pd.Timestamp):
        return v.strftime("%Y-%m-%d")
    return v


def records(df: pd.DataFrame, cols: list[str]) -> list[dict]:
    return [{c: clean(r[c]) for c in cols if c in df.columns} for _, r in df.iterrows()]


def glossary(path: Path) -> list[dict]:
    out, section = [], ""
    for line in path.read_text().splitlines():
        if line.startswith("## "):
            section = re.sub(r"^\d+\.\s*", "", line[3:].strip())
        elif line.startswith("| **"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            plain = lambda t: re.sub(r"\*+", "", t).strip()        # drop markdown bold / italics
            term = plain(cells[0])
            meaning = plain(cells[1]) if len(cells) == 2 else plain(cells[1]) + " " + plain(cells[2])
            out.append({"section": section or "Words with two meanings", "term": term, "meaning": meaning})
    return out


def synthetic_block(tiers: pd.DataFrame, sku: pd.DataFrame, sites: pd.DataFrame, ids: list[str]) -> dict | None:
    """Synthetic view (decision S4): same solves on data/processed/suppliers_matrix_synthetic.csv, plus every synthetic
    value with the range it was drawn from. None if synthetic/build_synthetic.py has not been run."""
    if not SYN_MATRIX.exists():
        return None
    ms = pd.read_csv(SYN_MATRIX)
    b = solve_dataset(ms, tiers, sku, sites)
    if b["ids"] != ids:
        raise ValueError("synthetic view must rank the same suppliers as the real view")
    inp = pd.read_csv(SYN_DIR / "outputs" / "synthetic_inputs.csv").set_index("manufacturer_id")
    for sp in b["suppliers"]:
        sp["syn"] = {k: clean(v) for k, v in inp.loc[sp["id"]].items()}
    rng = pd.read_csv(SYN_DIR / "reference" / "synthetic_ranges.csv")
    scms = pd.read_csv(INTERIM / "scms_shipments_clean.csv", usecols=["time_split", "vendor_inco_term", "late"], low_memory=False)
    tr = scms[scms["time_split"] == "train"]
    drawn = sorted(inp["vendor_inco_term"].unique())
    late_by_term = {t: round(float(tr.loc[tr["vendor_inco_term"] == t, "late"].mean()), 3) for t in drawn}
    return {
        "incoterm_late_rates": late_by_term,
        "matrix_sha256": hashlib.sha256(SYN_MATRIX.read_bytes()).hexdigest(),
        "suppliers": b["suppliers"], "scenarios": b["scenarios"], "modes": b["modes"], "stress": b["stress"],
        "ranges": records(rng, list(rng.columns)),
        "summary": json.loads((SYN_DIR / "outputs" / "synthetic_summary.json").read_text()),
    }


def solve_dataset(m: pd.DataFrame, tiers: pd.DataFrame, sku: pd.DataFrame, sites: pd.DataFrame) -> dict:
    """Suppliers, every scenario and every stress test for ONE score table (real or synthetic view)."""
    elig = m[m["eligible_for_ranking"].astype(bool)].sort_values("manufacturer_id").reset_index(drop=True)
    ids = elig["manufacturer_id"].tolist()
    # ---- suppliers ---------------------------------------------------------------------------------------
    suppliers = []
    for _, r in elig.iterrows():
        k = r["manufacturer_id"]
        s = sites.loc[k] if k in sites.index else pd.Series(dtype=str)
        set_ids = [x for x in str(s.get("dailymed_set_id", "") or "").split("|") if x and x != "nan"]
        suppliers.append({
            "id": k, "name": r["labeler_name_fda"],
            "factory": clean(r.get("factory_name")), "factory_fei": clean(r.get("factory_fei")),
            "factory_city": clean(s.get("factory_city")) if isinstance(s.get("factory_city"), str) else None,
            "factory_group": r["source_plant_group"], "country": r["manufacturing_country"],
            "is_probation": bool(r["is_probation"]), "country_neutral": bool(r.get("country_inputs_neutral", False)),
            "factory_neutral": bool(r.get("fda_inspection_record_neutral", False)),
            "active_shortage": bool(r["active_fda_shortage"]),
            "marks": {c: clean(r[c]) for c in CRITERIA}, "c5_crisis": clean(r["C5_route_exposure_crisis"]), "hormuz": clean(r["hormuz_air_share"]),
            "price_usd": clean(r["C1_landed_cost_usd_raw"]), "lpi": clean(r.get("lpi_score")),
            "oai": int(r["oai_count_5yr"]), "vai": int(r["vai_count_5yr"]),
            "recalls": int(r["recalls_class_i_ii_inj_5yr"]), "letters": int(r["warning_letters_5yr"]),
            "letter_severity": clean(r["nlp_warning_severity"]), "worst_letter": clean(r.get("worst_letter")),
            "note": clean(r.get("sister_plant_warning")), "own_shipments": int(r["scms_historical_shipments"]),
            "buyer_deliveries": int(r.get("internal_historical_deliveries", 0) or 0),
            "capacity": int(r["monthly_capacity_units"]),
            "medicaid_share_pct": clean(r.get("us_medicaid_2025_volume_share_pct")),
            "c2_basis": clean(r.get("c2_basis")), "shipment_profile": clean(r.get("shipment_profile")),
            "reasons": json.loads(r["shap_top3_reasons"]),
            "evidence": {"quote": clean(s.get("evidence_quote")), "note": clean(s.get("evidence_note")),
                         "label_version": clean(s.get("label_version")), "fei_evidence": clean(s.get("fei_evidence")),
                         "label_urls": [f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={x}"
                                        for x in set_ids]},
        })
    excluded = [{"name": r["labeler_name_fda"], "country": r["manufacturing_country"],
                 "reason": "Sells only the raw ingredient (bulk powder), not finished vials"}
                for _, r in m[~m["eligible_for_ranking"].astype(bool)].iterrows()]

    # ---- scenarios: solved by the real Layer 4 engine ----------------------------------------------------
    scenarios, modes = {}, {}
    for mode in MODES:
        for lam in LAMBDAS:
            for ent in ENTROPY:
                r = engine.run(m, tiers, sku, mode, lam, ent)
                rk, al = r["ranking"].reindex(ids), r["allocation"].set_index("manufacturer_id").reindex(ids)
                scenarios[f"{mode}|{lam:.2f}|{ent:.1f}"] = {
                    "w": [round(float(x), 4) for x in r["weights"]["Used for ranking"].reindex(CRITERIA)],
                    "S": [round(float(x), 4) for x in rk["S"]], "rank": [int(x) for x in rk["rank"]],
                    "gap": [[round(float(rk.loc[i, f"gap_share_{c[:2]}"]), 3) for c in CRITERIA] for i in ids],
                    "vials": [round(float(x), 1) for x in al["vials"]],
                    "cap_pct": [round(float(x), 1) for x in al["factory_cap_pct"]],
                    "spot": r["diagnostics"]["spot_buy_vials"], "status": r["diagnostics"]["solver_status"],
                    "spend": r["diagnostics"]["monthly_spend_usd"],
                    "backup": r["diagnostics"]["warm_backup_share_pct"],
                    "two_ok": r["diagnostics"]["meets_two_supplier_minimum"],
                }
                if mode not in modes:
                    modes[mode] = {
                        "ahp": [round(float(x), 4) for x in r["weights"]["AHP (board, this mode)"].reindex(CRITERIA)],
                        "entropy": [round(float(x), 4) for x in
                                    r["weights"]["Entropy (information only)"].reindex(CRITERIA)],
                        "values": [[round(float(rk.loc[i, f"value_{c}"]), 4) for c in CRITERIA] for i in ids],
                        "established_factories": r["diagnostics"]["established_factories"],
                        "probation_cap": r["diagnostics"]["probation_cap_used"], "tier_cap": r["diagnostics"]["tier_cap"],
                    }
                    ahp_check = r["ahp_consistency"]

    # ---- stress test: natural disaster takes factories offline (plan Q7 "scenario stress-testing") ----------
    # A disaster changes what can ship, not a supplier's quality: rankings stay, only the order split re-solves.
    outages = engine.stress_outages(m)
    stress = {}
    for o in outages:
        stress[o["key"]] = {}
        for mode in MODES:
            for lam in LAMBDAS:
                for ent in ENTROPY:
                    r = engine.run(m, tiers, sku, mode, lam, ent, set(o["groups"]))
                    al = r["allocation"].set_index("manufacturer_id").reindex(ids)
                    stress[o["key"]][f"{mode}|{lam:.2f}|{ent:.1f}"] = {
                        "vials": [round(float(x), 1) for x in al["vials"]], "spot": r["diagnostics"]["spot_buy_vials"],
                        "spend": r["diagnostics"]["monthly_spend_usd"], "status": r["diagnostics"]["solver_status"],
                        "backup": r["diagnostics"]["warm_backup_share_pct"],
                        "two_ok": r["diagnostics"]["meets_two_supplier_minimum"]}

    return {"elig": elig, "ids": ids, "suppliers": suppliers, "excluded": excluded, "scenarios": scenarios,
            "modes": modes, "ahp_check": ahp_check, "stress": {"outages": outages, "results": stress}}


def main() -> int:
    m, tiers, sku = engine.load_inputs()
    content = json.loads((WEB / "content" / "site_content.json").read_text())
    quality = json.loads(QUALITY.read_text())
    sites = pd.read_csv(L1_REF / "sku_manufacturing_sites.csv", dtype=str).set_index("labeler_key")
    real = solve_dataset(m, tiers, sku, sites)
    elig, ids, suppliers, scenarios, modes = real["elig"], real["ids"], real["suppliers"], real["scenarios"], real["modes"]
    excluded, ahp_check, stress, outages = real["excluded"], real["ahp_check"], real["stress"]["results"], real["stress"]["outages"]
    synthetic = synthetic_block(tiers, sku, sites, ids)

    # ---- alerts, documents, models, sources --------------------------------------------------------------
    sh = pd.read_csv(INTERIM / "fda_shortages_sku.csv")
    onc = pd.read_csv(INTERIM / "fda_shortages_oncology_current.csv")
    letters = pd.read_csv(L3 / "c4_warning_letters_classified.csv").sort_values("letter_date", ascending=False)
    contracts = pd.read_csv(L3 / "c4_contract_clauses.csv")
    c2 = json.loads((L3 / "c2_metrics.json").read_text())
    c3 = json.loads((L3 / "c3_metrics.json").read_text())
    c4 = json.loads((L3 / "c4_metrics.json").read_text())
    examples = pd.read_csv(L3 / "c3_anomaly_examples.csv")
    checks = pd.DataFrame(quality["checks"])
    matrix_file = ROOT / "data" / "processed" / "suppliers_matrix.csv"

    snapshot = {
        "meta": {
            "as_of": quality["manifest"].get("as_of"),
            "exported_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "matrix_sha256": hashlib.sha256(matrix_file.read_bytes()).hexdigest(),
            "sku_id": sku.iloc[0]["sku_id"], "demand": int(sku.iloc[0]["monthly_demand_units"]),
            "tier": int(sku.iloc[0]["criticality_tier"]), "labelers_total": int(len(m)), "rankable": len(ids),
            "factories": int(elig["source_plant_group"].nunique()),
            "lambdas": LAMBDAS, "entropy_shares": ENTROPY, "modes": list(MODES), "criteria": CRITERIA,
            "ahp_consistency": {k: clean(v) for k, v in ahp_check.items() if k != "weights_from_implied_matrix"},
        },
        "content": content, "supplier_ids": ids, "suppliers": suppliers, "excluded": excluded,
        "modes": modes, "scenarios": scenarios,
        "stress": {"outages": outages, "results": stress},
        "synthetic": synthetic,
        "alerts": {
            "sku": records(sh, ["company_name", "status", "availability", "presentation", "shortage_reason",
                                "update_date", "is_active"]),
            "oncology_by_molecule": [{"molecule": str(k).title(), "records": int(v)}
                                     for k, v in onc["generic_name"].value_counts().items()],
            "oncology_total": int(len(onc)),
        },
        "documents": {
            "letters": records(letters, ["company_name", "letter_date", "top_violation", "letter_severity",
                                         "source_url", "p_sterility", "p_data_integrity", "p_process_validation",
                                         "p_quality_unit"]),
            "classifier": c4["warning_letter_classifier"], "severity_weights": c4["severity_weights"],
            "contracts": records(contracts, ["supplier_name", "force_majeure", "lead_time_days",
                                             "late_delivery_penalty", "exclusive_share_pct", "contract_risk",
                                             "safety_stock_days", "llm_rule_agree_all_clauses"]),
        },
        "models": {
            "c2": {k: c2[k] for k in ["train_rows", "test_rows", "train_late_rate", "test_late_rate",
                                      "xgboost_test", "logistic_regression_test",
                                      "global_feature_importance_mean_abs_shap", "caveat"]},
            "c3": {"lines_total": c3["lines_total"], "lines_scored": c3["lines_scored"],
                   "lines_flagged": c3["lines_flagged"],
                   "examples": records(examples, ["vendor", "product_group", "unit_price", "line_item_value",
                                                  "freight_usd", "freight_to_value_ratio", "why_flagged"])},
        },
        "sources": [{"key": k, "label": SOURCE_LABELS.get(k, k), **{a: clean(b) for a, b in v.items()}}
                    for k, v in quality["sources"].items()],
        "quality": {"checks": int(len(checks)), "warnings": int((checks["severity"] == "warning").sum()),
                    "errors": int((checks["severity"] == "error").sum()),
                    "quarantined_rows": int(sum(quality["manifest"].get("quarantined_rows", {}).values()))},
        "glossary": glossary(ROOT / "docs" / "GLOSSARY.md"),
    }
    out = WEB / "data" / "snapshot.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot, separators=(",", ":"), default=clean))
    bad = [k for k, v in scenarios.items() if v["status"] != "Optimal"] + \
          [o + "|" + k for o, res in stress.items() for k, v in res.items() if v["status"] != "Optimal"]
    if synthetic:
        bad += ["syn|" + k for k, v in synthetic["scenarios"].items() if v["status"] != "Optimal"] + \
               ["syn|" + o + "|" + k for o, res in synthetic["stress"]["results"].items() for k, v in res.items()
                if v["status"] != "Optimal"]
    print(f"snapshot written: web/data/{out.name}  ({out.stat().st_size / 1024:.0f} KB) | suppliers {len(ids)} | "
          f"scenarios {len(scenarios)} + stress tests {sum(len(v) for v in stress.values())}"
          f"{' | synthetic view: same again' if synthetic else ' | synthetic view: not built'} (not optimal: {len(bad)}) | "
          f"glossary terms {len(snapshot['glossary'])}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
