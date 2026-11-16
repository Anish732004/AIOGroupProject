#!/usr/bin/env python3
"""
PharmaShield GCC - Layer 3: AI risk engines C2, C3, C4 (plan section 2 Layer 3, 4.3, 5.2 steps 4-6).

    python run_engines.py            # after Layer 1:  cd ../layer1_ingestion && python run_ingestion.py

Reads    layer1_ingestion/data/interim/*  (SCMS, panel features, entity links, letters, contracts)
         data/processed/suppliers_matrix.csv  (locked schema, C1 + C5 filled by Layer 1)
Writes   data/processed/suppliers_matrix.csv  with C2_delivery_risk, C3_price_integrity, C4_compliance_risk and
         shap_top3_reasons filled (locked 16 columns unchanged; supporting columns appended after them)
         layer3_engines/outputs/*  metrics, SHAP drivers, anomaly examples, classified letters, contract clauses

Re-run this every time Layer 1 is re-run (Layer 1 rewrites the matrix with C2-C4 empty).
"""
from __future__ import annotations

import argparse
import logging
import sys
import time

import pandas as pd

from engines import c2_delivery, c3_anomaly, c4_compliance
from engines.io import P, as_of, links_for, load_matrix, read_interim, save_matrix, write_output

log = logging.getLogger("pharmashield.layer3")
SUPPORTING = {  # extra columns appended after the locked 16 (never between them)
    "c2": ["c2_score_weighted_model", "site_prior_shipments", "shipment_profile", "c2_basis"],
    "c3": ["c3_basis", "c3_scored_lines", "c3_flagged_lines"],
    "c4": ["nlp_warning_severity", "warning_letters_5yr", "worst_letter", "letters_basis", "unscored_letters_5yr",
           "sister_plant_warning", "contract_risk", "contract_risk_demo_only", "contract_risk_source"],
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--log-level", default="INFO")
    a = ap.parse_args(argv)
    logging.basicConfig(level=a.log_level, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    t0 = time.time()

    m = load_matrix()
    scms = read_interim("scms_shipments_clean")
    inf = read_interim("panel_inference_features")
    run_date = as_of()

    # ---- C2: XGBoost + SHAP ------------------------------------------------------------------------------
    c2 = c2_delivery.run(scms, inf)
    c2["panel"] = c2_delivery.neutralise_unknown_country(c2["panel"], m)
    write_output(c2["metrics"], "c2_metrics")
    write_output(c2["panel"], "c2_panel_predictions")
    write_output(c2["importance"], "c2_feature_importance")
    write_output(c2["test_predictions"], "c2_test_predictions")

    # ---- C3: Isolation Forest ----------------------------------------------------------------------------
    scms_links = links_for("scms")
    c3 = c3_anomaly.run(scms, m, scms_links[scms_links["relationship"].eq("self")])   # item 9: own history only
    write_output(c3["metrics"], "c3_metrics")
    write_output(c3["panel"], "c3_panel_scores")
    write_output(c3["examples"], "c3_anomaly_examples")
    write_output(c3["lines"], "c3_scored_lines")

    # ---- C4: FDA + warning-letter NLP + contract LLM -----------------------------------------------------
    c4 = c4_compliance.run(m, read_interim("warning_letters_corpus"), read_interim("contracts_corpus"),
                           links_for("warning_letters"), links_for("contracts"),
                           P.reference / "contract_extraction_llm.json", run_date)
    write_output(c4["metrics"], "c4_metrics")
    write_output(c4["panel"], "c4_panel_scores")
    write_output(c4["letters"], "c4_warning_letters_classified")
    write_output(c4["contracts"], "c4_contract_clauses")

    # ---- fill the locked columns + append supporting columns ---------------------------------------------
    m = m.drop(columns=[c for cols in SUPPORTING.values() for c in cols if c in m.columns])
    for res, cols in ((c2["panel"], ["C2_delivery_risk", "shap_top3_reasons"] + SUPPORTING["c2"]),
                      (c3["panel"], ["C3_price_integrity"] + SUPPORTING["c3"]),
                      (c4["panel"], ["C4_compliance_risk"] + SUPPORTING["c4"])):
        idx = res.set_index("manufacturer_id")
        for c in cols:
            mapped = m["manufacturer_id"].map(idx[c])
            if c in m.columns:
                m[c] = mapped
            else:
                m[c] = mapped
    path = save_matrix(m)

    summary = {
        "as_of": str(run_date.date()), "runtime_s": round(time.time() - t0, 1),
        "matrix": str(path.relative_to(P.root)),   # relative: no local machine paths in shared outputs
        "c2_xgboost_test": c2["metrics"]["xgboost_test"], "c2_logreg_test": c2["metrics"]["logistic_regression_test"],
        "c3_lines_flagged": c3["metrics"]["lines_flagged"], "c3_lines_scored": c3["metrics"]["lines_scored"],
        "c4_letter_classifier": c4["metrics"]["warning_letter_classifier"],
        "c4_contract_agreement": c4["metrics"]["contract_extraction"]["clause_agreement_llm_vs_rules"],
    }
    write_output(summary, "layer3_summary")

    x, lr = c2["metrics"]["xgboost_test"], c2["metrics"]["logistic_regression_test"]
    print("\n=== Layer 3 engines summary ===")
    print(f"  C2 XGBoost  test ROC-AUC {x['roc_auc']:.3f} | recall {x['recall_late']:.2f} | precision "
          f"{x['precision_late']:.2f}   (scale_pos_weight {c2['metrics']['scale_pos_weight_chosen']})")
    print(f"  C2 LogReg   test ROC-AUC {lr['roc_auc']:.3f} | recall {lr['recall_late']:.2f} | precision "
          f"{lr['precision_late']:.2f}   (baseline)")
    print(f"  C3 IsolationForest: {c3['metrics']['lines_flagged']} of {c3['metrics']['lines_scored']} scored lines flagged")
    for k, v in c4["metrics"]["warning_letter_classifier"].items():
        print(f"  C4 letters  {k:20s} {v['positives']:2d}/{v['letters']} positive | "
              f"{'OOF ROC-AUC ' + str(v['oof_roc_auc']) if 'oof_roc_auc' in v else v['method']}")
    print(f"  C4 contracts LLM vs rules agreement: {c4['metrics']['contract_extraction']['clause_agreement_llm_vs_rules']}")
    cols = ["manufacturer_id", "eligible_for_ranking", "is_probation", "C1_landed_cost", "C2_delivery_risk",
            "C3_price_integrity", "C4_compliance_risk", "C5_route_exposure"]
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print("\n" + m.loc[m["eligible_for_ranking"].astype(bool), cols].to_string(index=False))
    print(f"\n  matrix written: {path.relative_to(P.root)}\n  outputs: {P.outputs.relative_to(P.root)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
