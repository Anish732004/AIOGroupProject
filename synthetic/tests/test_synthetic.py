"""Tests for the synthetic view (decision S4).   cd synthetic && python -m pytest -q"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "synthetic"))
import build_synthetic as bs  # noqa: E402


@pytest.fixture(scope="module")
def real():
    return pd.read_csv(bs.MATRIX_REAL)


@pytest.fixture(scope="module")
def inputs(real):
    return bs.draw_inputs(real, bs.ranges())


@pytest.fixture(scope="module")
def built(real, inputs):
    before = hashlib.sha256(bs.MATRIX_REAL.read_bytes()).hexdigest()
    m = real.copy()
    res = bs.build(m, inputs, bs.invoice_lines(inputs),
                   pd.read_csv(bs.INTERIM / "scms_shipments_clean.csv", low_memory=False),
                   pd.read_csv(bs.INTERIM / "panel_inference_features.csv"))
    res["real_untouched"] = m.equals(real) and hashlib.sha256(bs.MATRIX_REAL.read_bytes()).hexdigest() == before
    return res


def test_same_seed_same_values(real, inputs):
    pd.testing.assert_frame_equal(inputs, bs.draw_inputs(real, bs.ranges()))


def test_every_value_inside_its_approved_range(inputs):
    r = bs.ranges()
    inside = lambda col, rid: inputs[col].dropna().between(float(r.at[rid, "low"]), float(r.at[rid, "high"])).all()
    assert (inputs["shipment_mode"] == "Air").all()                                     # R1
    assert set(inputs["vendor_inco_term"]) <= set(bs.INCOTERMS)                         # R2
    assert inside("kg_per_vial", "R3") and inside("shipment_vials", "R4")
    for country, rid in bs.FREIGHT_RANGE_BY_COUNTRY.items():                            # R5a-c
        sub = inputs[inputs["country"] == country]
        assert sub["freight_rate_usd_per_kg"].between(float(r.at[rid, "low"]), float(r.at[rid, "high"])).all()
    assert inside("invoice_error_rate", "R7") and inside("factory_capacity_vials", "R8")
    assert inside("hormuz_air_share", "R9")
    est = inputs[inputs["established"]]
    assert est["past_deliveries"].between(6, 24).all() and est["on_time_rate"].between(0.80, 0.95).all()   # R10, R11
    assert (inputs.loc[~inputs["established"], "past_deliveries"] == 0).all()


def test_established_suppliers_are_the_big_us_sellers(real, inputs):
    share = real.set_index("manufacturer_id")["us_medicaid_2025_volume_share_pct"]
    expected = {k for k, v in share.items() if pd.notna(v) and v >= bs.ESTABLISHED_MIN_US_SHARE
                and k in set(inputs["manufacturer_id"])}
    assert set(inputs.loc[inputs["established"], "manufacturer_id"]) == expected
    assert expected == {"HOSPIRA", "TEVA PARENTERAL MEDICINES", "EUGIA US", "FRESENIUS KABI USA", "ACCORD HEALTHCARE"}


def test_names_sharing_a_factory_share_its_physical_values(inputs):
    for _, g in inputs.groupby("factory_group"):
        for c in ["kg_per_vial", "freight_rate_usd_per_kg", "hormuz_air_share", "factory_capacity_vials"]:
            assert g[c].nunique() == 1, c


def test_real_table_is_never_changed(built):
    assert built["real_untouched"]


def test_new_cost_formula_equals_the_plan_result_on_real_data(real):
    e = real[real["eligible_for_ranking"].astype(bool)]
    assert np.allclose(bs.cost_mark(e["C1_landed_cost_usd_raw"].astype(float)), e["C1_landed_cost"])


def test_scores_follow_the_plan_formulas(real, built):
    s = built["matrix"]
    e, r = s[s["eligible_for_ranking"].astype(bool)], real.set_index("manufacturer_id")
    for _, x in e.iterrows():
        k = x["manufacturer_id"]
        assert x["C4_compliance_risk"] == pytest.approx(min(1.0, r.at[k, "C4_compliance_risk"] + 0.20 * r.at[k, "contract_risk_demo_only"]), abs=1e-4)
        assert x["C5_route_exposure"] == pytest.approx(min(1.0, x["hormuz_air_share"]) * (1 - x["lpi_score"] / 5), abs=1e-4)
        if x["is_probation"]:
            assert x["C3_price_integrity"] == 0.0                                       # plan 4.3 default
    for c in ["C1_landed_cost", "C2_delivery_risk", "C3_price_integrity", "C4_compliance_risk", "C5_route_exposure"]:
        assert e[c].between(0, 1).all() and e[c].notna().all()


def test_locked_schema_kept(real, built):
    assert list(built["matrix"].columns[:16]) == list(real.columns[:16])


def test_models_are_not_trained_on_synthetic_data(built):
    # the late-delivery model is trained on the same real data, so its test score is unchanged
    assert built["summary"]["c2_model_test_roc_auc_unchanged"] == pytest.approx(0.797, abs=0.001)
    # the billing model finds most planted invoice errors
    s = built["summary"]
    assert s["c3_injected_errors"] > 0 and s["c3_injected_errors_caught"] >= 0.75 * s["c3_injected_errors"]
