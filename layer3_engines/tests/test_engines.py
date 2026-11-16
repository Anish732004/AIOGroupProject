"""Layer 3 tests. Unit tests use synthetic data; the integration test runs only if Layer 1 output exists."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engines import c2_delivery as c2, c3_anomaly as c3, c4_compliance as c4  # noqa: E402
from engines.io import P  # noqa: E402

CONTRACTS = ROOT.parent / "layer1_ingestion" / "data" / "manual" / "contracts"


# ---------------- C2 ----------------
def test_site_prior_is_out_of_fold():
    """A training row must never see its own label: a site with one late shipment encodes to the global rate."""
    tr = pd.DataFrame({"site": ["A"] + ["B"] * 49, "late": [1] + [0] * 49})
    rate, n = c2.site_prior_oof(tr, folds=5)
    g = tr["late"].mean()
    assert n[0] == 0 and rate[0] == pytest.approx(g)


def test_prior_correction_inverts_class_weight():
    # weighting positives by w multiplies the odds by w; correcting must divide them back
    p_true = np.array([0.05, 0.2, 0.5])
    w = 9.0
    odds_w = w * p_true / (1 - p_true)
    p_weighted = odds_w / (1 + odds_w)
    assert c2.prior_correct(p_weighted, w) == pytest.approx(p_true)


def test_site_history_count_is_not_a_model_input():
    raw = pd.DataFrame({"manufacturing_country": ["India"], "shipment_mode": ["Air"], "vendor_inco_term": ["DDP"],
                        "log_freight_to_value": [0.1], "log_weight_kg": [5.0], "site_prior_late_rate": [0.1],
                        "log_site_prior_n": [0.0]})
    assert "log_site_prior_n" not in c2.encode(raw).columns    # no-history must stay neutral (plan 3.1)


def test_shap_json_is_plain_english_top3():
    s = pd.Series({"site_prior": 0.2, "vendor_inco_term": -0.5, "weight_kg": 0.05, "shipment_mode": 0.01})
    raw = pd.Series({"site_prior_late_rate": 0.1, "log_site_prior_n": 0.0, "vendor_inco_term": "DDP",
                     "log_weight_kg": np.log1p(1200), "shipment_mode": "Air"})
    out = json.loads(c2.top3_json(s, raw))
    assert len(out) == 3 and out[0]["feature"] == "Delivery terms (Incoterm)"
    assert out[0]["effect"] == "lowers late-delivery risk" and out[1]["effect"] == "raises late-delivery risk"


# ---------------- C3 ----------------
def _scms_lines(n=200, seed=0):
    rng = np.random.default_rng(seed)
    d = pd.DataFrame({"id": range(n), "vendor": ["V1"] * (n // 2) + ["V2"] * (n - n // 2),
                      "manufacturing_site": "S", "product_group": "ARV",
                      "unit_price": rng.lognormal(0, .2, n), "line_item_value": rng.lognormal(10, .2, n),
                      "freight_to_value_ratio": rng.lognormal(-2.5, .2, n), "freight_usd": 1.0})
    d.loc[0, "freight_to_value_ratio"] = 500.0          # obvious freight outlier
    return d


def test_isolation_forest_flags_about_five_percent_and_the_outlier():
    d, _ = c3.score_lines(_scms_lines())
    assert d["c3_scored"].all()
    assert d["c3_flagged"].mean() == pytest.approx(0.05, abs=0.02)
    assert bool(d.loc[0, "c3_flagged"])


def test_c3_probation_defaults_to_zero_and_share_for_established():
    lines = _scms_lines()
    matrix = pd.DataFrame({"manufacturer_id": ["NEW", "OLD"], "is_probation": [True, False]})
    links = pd.DataFrame({"labeler_key": ["NEW", "OLD"], "external_name": ["V2", "V1"]})
    out = c3.run(lines, matrix, links)["panel"].set_index("manufacturer_id")
    assert out.loc["NEW", "C3_price_integrity"] == 0.0                   # plan 4.3 probation default
    old = out.loc["OLD"]
    assert old["C3_price_integrity"] == pytest.approx(old["c3_flagged_lines"] / old["c3_scored_lines"], abs=1e-4)


def test_missing_freight_lines_are_not_scored():
    d = _scms_lines()
    d.loc[1, "freight_to_value_ratio"] = np.nan
    s, _ = c3.score_lines(d)
    assert not s.loc[1, "c3_scored"] and s.loc[1, "c3_unscored_reason"] == "missing_or_zero_price_or_freight"


# ---------------- C4 ----------------
def test_weak_labels_from_cfr_citations_and_citations_stripped():
    t = pd.Series(["violation of 21 CFR 211.113(b) aseptic", "21 CFR 211.68(b) and 211.194(a)"])
    y = c4.weak_labels(t)
    assert y.loc[0, "sterility"] == 1 and y.loc[1, "data_integrity"] == 1 and y.loc[1, "sterility"] == 0
    assert "211" not in c4.strip_citations(t[1]) and "CFR" not in c4.strip_citations(t[1])


@pytest.mark.skipif(not CONTRACTS.exists(), reason="contracts not present")
def test_rule_extractor_on_real_contracts():
    def read(f):   # Layer 1 collapses whitespace; mimic it
        return " ".join((CONTRACTS / f).read_text().split())
    eu = c4.rule_extract(read("eugia_us_llc_msa.txt"))
    assert eu["force_majeure"]["risk"] == 1.0 and eu["lead_time"]["days"] == 75
    assert eu["late_delivery_penalty"]["category"] == "none" and eu["single_source"]["exclusive_share_pct"] == 80
    gl = c4.rule_extract(read("gland_pharma_limited_msa.txt"))
    assert gl["force_majeure"]["category"] == "hormuz_disruption_excluded" and gl["lead_time"]["days"] == 45
    assert gl["late_delivery_penalty"]["risk"] == 0.0 and gl["single_source"]["risk"] == 0.0
    assert gl["contract_risk"] == pytest.approx((0 + 0.25 + 0 + 0) / 4)


def test_llm_cache_is_bound_to_contract_hash(tmp_path):
    cache = {"contracts": [{"text_sha256": "abc", "contract_risk": 0.9,
                            **{c: {"risk": 1.0, "category": "x", "days": 90, "exclusive_share_pct": None}
                               for c in c4.CLAUSES},
                            "other_clauses": {}}]}
    (tmp_path / "c.json").write_text(json.dumps(cache))
    txt = "2. FORECASTS deliver within 30 calendar days of order acceptance 3. LATE DELIVERY 3.1 per week of delay"
    ct = pd.DataFrame({"supplier_name": ["X"], "source_file": ["x.txt"], "text": [txt], "text_sha256": ["CHANGED"]})
    out, rep = c4.extract_contracts(ct, tmp_path / "c.json")
    assert rep["llm_cache_hits"] == 0 and out.loc[0, "extraction_source"].startswith("rule_extractor")


def test_c4_formula_and_cap():
    matrix = pd.DataFrame({"manufacturer_id": ["A", "B"], "C4_fda_component_partial": [0.6, 0.9]})
    letters = pd.DataFrame({"doc_id": ["1"], "company_name": ["A Ltd"], "letter_date": ["2026-01-01"],
                            "source_url": [""], "text": ["21 CFR 211.113(b) aseptic"]})
    contracts = pd.DataFrame({"supplier_name": ["A Ltd"], "source_file": ["a.txt"], "text_sha256": ["h"],
                              "text": ["2. LEAD within 90 calendar days 3. LATE DELIVERY 3.1 estimates only"]})
    ll = pd.DataFrame({"labeler_key": ["A"], "external_name": ["A Ltd"], "relationship": ["self"]})
    out = c4.run(matrix, letters, contracts, ll, ll, Path("/nonexistent.json"), pd.Timestamp("2026-11-15"))
    p = out["panel"].set_index("manufacturer_id")
    expect_a = min(1.0, 0.6 + 0.20 * p.loc["A", "nlp_warning_severity"] + 0.20 * p.loc["A", "contract_risk"])
    assert p.loc["A", "C4_compliance_risk"] == pytest.approx(expect_a, abs=1e-4)
    # team decision item 7: contracts are synthetic -> the contract term is 0 for every maker (kept as demo only)
    assert (p["contract_risk"] == 0).all()
    assert p.loc["A", "contract_risk_demo_only"] > 0                                   # extraction still shown
    assert p.loc["B", "C4_compliance_risk"] == pytest.approx(0.9)
    assert p.loc["B", "contract_risk_source"].startswith("NOT SCORED")


# ---------------- end to end ----------------
@pytest.mark.skipif(not (P.processed / "suppliers_matrix.csv").exists() or not (P.interim / "scms_shipments_clean.csv")
                    .exists(), reason="run Layer 1 first")
def test_end_to_end_fills_locked_columns():
    import run_engines
    assert run_engines.main(["--log-level", "WARNING"]) == 0
    m = pd.read_csv(P.processed / "suppliers_matrix.csv")
    locked = pd.read_csv(P.l1_reference / "locked_schema.csv")["column"].tolist()
    assert list(m.columns[:16]) == locked
    for c in ["C2_delivery_risk", "C3_price_integrity", "C4_compliance_risk"]:
        assert m[c].notna().all() and m[c].between(0, 1).all()
    assert (m.loc[m["is_probation"], "C3_price_integrity"] == 0).all()
    known = m["manufacturing_country"].ne("Unknown")
    assert all(len(json.loads(s)) == 3 for s in m.loc[known, "shap_top3_reasons"])
    # evidence rule: unknown plant country -> neutral C2 (median of rankable makers with a known country)
    unk = m[~known & m["eligible_for_ranking"]]
    ref = m[known & m["eligible_for_ranking"]]
    for v in unk["C2_delivery_risk"]:
        assert v == pytest.approx(round(ref["C2_delivery_risk"].median(), 4), abs=1e-4)
    elig = m[m["eligible_for_ranking"]]
    assert elig["C2_delivery_risk"].nunique() > 1 and elig["C4_compliance_risk"].nunique() > 1
