"""Layer 4 tests: weights (AHP, modes, entropy), TOPSIS and the PuLP order split."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from decision import engine  # noqa: E402
from decision.allocation import allocate  # noqa: E402
from decision.topsis import topsis  # noqa: E402
from decision.weights import (CRITERIA, ahp_from_pairwise, blend, entropy_weights, implied_pairwise,  # noqa: E402
                              mode_weights, tier_weights)

TIERS = pd.read_csv(engine.TIERS)


def test_tier1_weights_and_modes_match_the_plan():
    w = tier_weights(TIERS, 1)
    assert w.round(4).tolist() == [0.10, 0.30, 0.05, 0.30, 0.25]
    assert mode_weights(w, "Crisis").round(4).tolist() == [0.0, 0.30, 0.05, 0.30, 0.35]      # plan 4.2
    assert mode_weights(w, "Cost Focus").round(4).tolist() == [0.20, 0.30, 0.05, 0.30, 0.15]
    for mode in ("Normal", "Crisis", "Cost Focus"):
        assert mode_weights(w, mode).sum() == pytest.approx(1.0)


def test_ahp_implied_matrix_is_consistent_and_returns_plan_weights():
    w = tier_weights(TIERS, 1)
    got, chk = ahp_from_pairwise(implied_pairwise(w))
    assert got.values == pytest.approx(w.values, abs=1e-6) and chk["CR"] == 0 and chk["consistent (CR < 0.10)"]


def test_ahp_detects_inconsistent_judgements():
    a = pd.DataFrame([[1, 9, 1 / 9], [1 / 9, 1, 9], [9, 1 / 9, 1]], index=list("abc"), columns=list("abc"))
    _, chk = ahp_from_pairwise(a)
    assert chk["CR"] > 0.10 and not chk["consistent (CR < 0.10)"]


def test_entropy_ignores_criteria_that_do_not_vary():
    x = pd.DataFrame({"C1": [0.0, 0.0, 0.0], "C2": [0.1, 0.5, 0.9], "C3": [0.2, 0.2, 0.8]})
    w, table = entropy_weights(x)
    assert w["C1"] == 0 and w.sum() == pytest.approx(1.0)
    assert not table.set_index("criterion").loc["C1", "varies_across_makers"]
    b = blend(pd.Series({"C1": 0.2, "C2": 0.4, "C3": 0.4}), w, 0.0)
    assert b.tolist() == pytest.approx([0.2, 0.4, 0.4])                     # share 0 = board weights only


def test_topsis_zero_guard_and_dominance():
    x = pd.DataFrame({"C1": [0.0, 0.0, 0.0], "C2": [0.1, 0.5, 0.9], "C3": [0.0, 0.3, 0.6]}, index=["best", "mid", "worst"])
    r = topsis(x, pd.Series({"C1": 0.2, "C2": 0.4, "C3": 0.4}))
    assert not r.isna().any().any()
    assert r.loc["best", "rank"] == 1 and r.loc["worst", "rank"] == 3
    assert r.loc["best", "S"] == pytest.approx(1.0) and r.loc["worst", "S"] == pytest.approx(0.0)


def _panel(n=6, probation=True, cap=10000):
    return pd.DataFrame({"manufacturer_id": [f"M{i}" for i in range(n)], "S": np.linspace(0.9, 0.4, n),
                         "landed_cost_usd": 28.0, "is_probation": probation,
                         "factory_group": [f"F{i}" for i in range(n)], "monthly_capacity_units": cap})


def test_split_meets_demand_and_respects_probation_rules():
    r = allocate(_panel(), 10000, 0.70, 1.0)
    a, d = r["allocation"], r["diagnostics"]
    assert d["solver_status"] == "Optimal" and d["spot_buy_vials"] == 0
    assert a["vials"].sum() == pytest.approx(10000)
    s = a["share_pct"]
    assert ((s == 0) | ((s >= 5 - 1e-6) & (s <= 30 + 1e-6))).all()        # 0, or 5%..30% (no established maker)
    assert d["probation_cap_used"] == 0.30


def test_cap_is_per_factory_not_per_name():
    p = _panel(4)
    p["factory_group"] = ["SAME", "SAME", "SAME", "OTHER"]
    p.loc[3, "S"] = 0.1
    r = allocate(p, 10000, 0.70, 1.0)
    a = r["allocation"]
    assert a.groupby("factory_group")["vials"].sum()["SAME"] <= 3000 + 1e-6
    assert r["diagnostics"]["spot_buy_vials"] > 0          # 2 factories x 30% cannot cover demand -> spot buy


def test_established_makers_use_tier_cap_and_tighter_trial_cap():
    p = _panel(5)
    p.loc[[0, 1], "is_probation"] = False                  # two established factories
    r = allocate(p, 10000, 0.70, 1.0)
    a = r["allocation"].set_index("manufacturer_id")
    assert r["diagnostics"]["probation_cap_used"] == 0.15
    assert a.loc["M0", "share_pct"] <= 70 + 1e-6 and a.loc["M0", "share_pct"] > 30
    assert (a.loc[a["is_probation"], "share_pct"] <= 15 + 1e-6).all()


def test_split_is_deterministic():
    a1 = allocate(_panel(), 10000, 0.70, 1.0)["allocation"]
    a2 = allocate(_panel(), 10000, 0.70, 1.0)["allocation"]
    assert a1["vials"].tolist() == a2["vials"].tolist()


@pytest.mark.skipif(not engine.MATRIX.exists(), reason="run Layers 1 and 3 first")
def test_end_to_end_on_real_matrix():
    m, tiers, sku = engine.load_inputs()
    for mode in ("Normal", "Crisis", "Cost Focus"):
        r = engine.run(m, tiers, sku, mode)
        a, d = r["allocation"], r["diagnostics"]
        assert d["solver_status"] == "Optimal"
        assert a["vials"].sum() + d["spot_buy_vials"] == pytest.approx(r["demand"])
        assert a.groupby("factory_group")["vials"].sum().max() <= r["demand"] * d["probation_cap_used"] + 1e-6 \
            or d["established_factories"] > 0
        assert r["weights"]["Used for ranking"].sum() == pytest.approx(1.0)
        assert set(r["ranking"].index) == set(m.loc[m["eligible_for_ranking"].astype(bool), "manufacturer_id"])


def test_equal_suppliers_resolve_the_same_way_for_every_risk_dial():
    """Two names from one factory with identical scores are interchangeable. The chosen name must not flip when
    lambda changes (it did, before the solver gap was set to zero and ties were broken in a second solve)."""
    p = _panel(5)
    p["manufacturer_id"] = ["ZED", "ALPHA", "M2", "M3", "M4"]
    p["factory_group"] = ["SHARED", "SHARED", "F2", "F3", "F4"]
    p.loc[[0, 1], "S"] = 0.9
    for lam in (0.25, 0.5, 1.0, 1.75, 3.0):
        a = allocate(p, 10000, 0.70, lam)["allocation"].set_index("manufacturer_id")
        assert a.loc["ALPHA", "vials"] == pytest.approx(3000) and a.loc["ZED", "vials"] == 0, lam


def test_offline_factory_gets_nothing_and_others_cover():
    """Stress test (natural disaster): an offline factory ships nothing; the others cover demand within their caps."""
    p = _panel(6)
    r = allocate(p, 10000, 0.70, 1.0, offline={"F0"})
    a = r["allocation"].set_index("manufacturer_id")
    assert a.loc["M0", "vials"] == 0 and r["diagnostics"]["offline_factories"] == ["F0"]
    assert a["vials"].sum() + r["diagnostics"]["spot_buy_vials"] == pytest.approx(10000)
    assert (a["share_pct"] <= 30 + 1e-6).all()


def test_too_many_offline_factories_forces_an_emergency_purchase():
    p = _panel(6)
    r = allocate(p, 10000, 0.70, 1.0, offline={"F0", "F1", "F2", "F3"})   # 2 factories x 30% left
    assert r["diagnostics"]["spot_buy_vials"] == pytest.approx(4000)
    assert r["diagnostics"]["tie_break"] == "applied"


def test_unknown_offline_factory_is_rejected():
    with pytest.raises(ValueError):
        allocate(_panel(3), 10000, 0.70, 1.0, offline={"NO_SUCH_FACTORY"})


@pytest.mark.skipif(not engine.MATRIX.exists(), reason="run Layers 1 and 3 first")
def test_disaster_changes_the_split_not_the_ranking():
    m, tiers, sku = engine.load_inputs()
    base = engine.run(m, tiers, sku, "Normal")
    top = base["allocation"].sort_values("vials", ascending=False)["factory_group"].iloc[0]
    hit = engine.run(m, tiers, sku, "Normal", offline_factories={top})
    assert hit["ranking"]["S"].equals(base["ranking"]["S"])                      # quality unchanged
    assert hit["allocation"].groupby("factory_group")["vials"].sum()[top] == 0  # that factory ships nothing


def test_tier1_two_supplier_minimum_and_warm_backup_share():
    """Plan 4.2: Tier 1 needs at least 2 qualified makers; plan Q7: warm-backup share = order outside the primary factory."""
    for path in (engine.MATRIX, engine.MATRIX_SYNTHETIC):
        if not path.exists():
            continue
        m, tiers, sku = engine.load_inputs(path)
        for mode in ("Normal", "Crisis", "Cost Focus"):
            d = engine.run(m, tiers, sku, mode)["diagnostics"]
            assert d["meets_two_supplier_minimum"]
            assert d["warm_backup_share_pct"] == pytest.approx(100 - d["largest_factory_share_pct"], abs=0.01)
