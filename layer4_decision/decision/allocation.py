"""
Dual-source order split (plan 4.4), solved with PuLP (CBC).

  minimise   sum_i [ LandedCost_i + lambda * MeanCost * (1 - S_i) ] * x_i  +  M * u
  subject to sum_i x_i + u = D                                   demand (u = emergency spot buy, M = 1e6)
             x_i <= MonthlyCapacity_i                            plant capacity
             sum_{i in factory g} x_i <= cap_g * D               concentration cap PER FACTORY (team decision L3)
             probation maker i:  0.05*D*y_i <= x_i <= pcap*D*y_i  y_i in {0,1}: 0 or a trial share (decision L2)
             pcap = 0.15 when at least 2 established factories exist, else 0.30 (plan 4.4)

Tier concentration cap for established factories: 0.70 (Tier 1), 0.80 (Tier 2), 1.00 (Tier 3).
A factory whose makers are all on probation is capped at pcap.

Ties are resolved exactly, in two solves (lexicographic), with the solver's optimality gap set to zero:
  1. minimise the plan's cost objective                      -> best cost z*
  2. among the splits that cost z*, prefer suppliers in alphabetical order of their name
So makers that are truly interchangeable (same factory and score) always resolve the same way, whatever the risk
dial. Without this, the solver's default 0.01% tolerance let the chosen name flip between equal suppliers.
"""
from __future__ import annotations

import pandas as pd
import pulp

BIG_M = 1e6
PROBATION_FLOOR = 0.05
PROBATION_CAP_WITH_2_ESTABLISHED = 0.15
PROBATION_CAP_RELAXED = 0.30


def _var(prob: pulp.LpProblem, name: str, **kw):
    """PuLP 3.3+ prefers prob.add_variable (direct LpVariable(...) is deprecated for PuLP 4); older PuLP lacks it."""
    if hasattr(prob, "add_variable"):
        return prob.add_variable(name, **kw)
    return pulp.LpVariable(name, **kw)


def solve(prob: pulp.LpProblem) -> str:
    """Use whichever MILP solver runs on this machine: HiGHS (pip package 'highspy', works on Apple-silicon and
    Linux) first, then PuLP's bundled CBC (its binary is Intel-only on macOS)."""
    errors = []
    for name, make in (("HiGHS", lambda: pulp.HiGHS(msg=False, gapRel=0, gapAbs=0)),
                       ("CBC", lambda: pulp.PULP_CBC_CMD(msg=0, gapRel=0, gapAbs=0))):
        try:
            solver = make()
            if not solver.available():
                errors.append(f"{name}: not available")
                continue
            prob.solve(solver)
            return name
        except Exception as e:  # e.g. 'Bad CPU type in executable' for the Intel CBC binary
            errors.append(f"{name}: {type(e).__name__}: {e}")
    raise RuntimeError("no MILP solver could run: " + " | ".join(errors) + " - pip install highspy")


def allocate(df: pd.DataFrame, demand: int, tier_cap: float, lam: float, offline: set | None = None) -> dict:
    """df: one row per rankable maker with manufacturer_id, landed_cost_usd, S, is_probation, factory_group,
    monthly_capacity_units. `offline`: factory groups that cannot ship this month (stress test: natural disaster).
    Their makers get 0 vials; scores and caps of the other factories are unchanged. Returns allocation + diagnostics."""
    d = df.sort_values("manufacturer_id").reset_index(drop=True).copy()
    offline = set(offline or ())
    unknown = offline - set(d["factory_group"])
    if unknown:
        raise ValueError(f"unknown factory group(s): {sorted(unknown)}")
    d["offline"] = d["factory_group"].isin(offline)
    mean_cost = float(d["landed_cost_usd"].mean())             # plan 4.4: mean landed cost of the qualified makers
    groups = d.groupby("factory_group")["is_probation"].all()
    online_groups = groups[~groups.index.isin(offline)]
    n_established = int((~online_groups).sum())                # a factory that cannot ship does not count
    pcap = PROBATION_CAP_WITH_2_ESTABLISHED if n_established >= 2 else PROBATION_CAP_RELAXED
    d["unit_objective"] = d["landed_cost_usd"] + lam * mean_cost * (1 - d["S"])

    prob = pulp.LpProblem("pharmashield_order_split", pulp.LpMinimize)
    x = {i: _var(prob, f"x_{i}", lowBound=0) for i in d.index}
    y = {i: _var(prob, f"y_{i}", cat="Binary") for i in d.index if bool(d.at[i, "is_probation"])}
    u = _var(prob, "spot_buy", lowBound=0)
    supply_cost = pulp.lpSum(float(d.at[i, "unit_objective"]) * x[i] for i in d.index)
    prob += supply_cost + BIG_M * u
    prob += pulp.lpSum(x.values()) + u == demand, "demand"
    for i in d.index:
        prob += x[i] <= (0.0 if d.at[i, "offline"] else float(d.at[i, "monthly_capacity_units"])), f"capacity_{i}"
        if i in y:
            prob += x[i] >= PROBATION_FLOOR * demand * y[i], f"trial_floor_{i}"
            prob += x[i] <= pcap * demand * y[i], f"trial_cap_{i}"
    group_cap = {}
    for g, members in d.groupby("factory_group").groups.items():
        cap = pcap if bool(groups[g]) else tier_cap
        group_cap[g] = cap
        prob += pulp.lpSum(x[i] for i in members) <= cap * demand, f"factory_cap_{len(group_cap)}"
    solver_name = solve(prob)
    status = prob.status
    best_cost = pulp.value(prob.objective) or 0.0
    tie_break = "not needed"
    if pulp.LpStatus[status] == "Optimal":
        # stage 2: keep the optimal outcome, then prefer alphabetically earlier names (d is sorted by name).
        # The emergency amount and the supply cost are held SEPARATELY: holding their sum is numerically fragile
        # because the emergency penalty (1e6 per vial) dwarfs the supply cost.
        stage1 = {i: x[i].value() or 0.0 for i in d.index}
        u1, c1 = u.value() or 0.0, pulp.value(supply_cost) or 0.0
        prob += u <= u1 + 1e-6, "keep_emergency_amount"
        prob += supply_cost <= c1 + max(1e-4, 1e-7 * abs(c1)), "keep_supply_cost"
        prob.setObjective(pulp.lpSum(float(i) * x[i] for i in d.index))
        solve(prob)
        if pulp.LpStatus[prob.status] == "Optimal":
            tie_break = "applied"
        else:                                    # stage 1 is already optimal: keep it, and say so
            for i in d.index:
                x[i].varValue = stage1[i]
            u.varValue = u1
            tie_break = f"not applied (second solve: {pulp.LpStatus[prob.status]}); first optimal solution kept"
        status = 1                               # the reported result is the stage-1 optimum or an equal-cost one

    d["vials"] = [round(x[i].value() or 0.0, 1) for i in d.index]
    d["share_pct"] = (100 * d["vials"] / demand).round(2)
    d["factory_cap_pct"] = d["factory_group"].map(group_cap) * 100
    d["selected"] = d["vials"] > 0.5
    order = d.loc[d["selected"]].sort_values(["vials", "S"], ascending=False).index.tolist()
    roles = {}
    for k, i in enumerate(order):
        roles[i] = "Primary" if k == 0 else "Backup" if k == 1 else "Additional source"
    d["role"] = [roles.get(i, "Not selected") for i in d.index]
    d["probation_badge"] = d["is_probation"].astype(bool)
    spot = round(u.value() or 0.0, 1)
    by_factory = d.groupby("factory_group")["vials"].sum()
    return {
        "allocation": d.drop(columns=["unit_objective"]).sort_values(["vials", "S"], ascending=False),
        "diagnostics": {
            "solver_status": pulp.LpStatus[status], "solver": solver_name, "demand": demand, "spot_buy_vials": spot,
            "lambda": lam, "mean_cost_usd": round(mean_cost, 4), "tier_cap": tier_cap,
            "established_factories": n_established, "probation_cap_used": pcap,
            "factories_used": int((by_factory > 0.5).sum()), "makers_used": int(d["selected"].sum()),
            "largest_factory_share_pct": round(100 * float(by_factory.max()) / demand, 2),
            "objective_value": round(best_cost, 2),
            "offline_factories": sorted(offline), "tie_break": tie_break,
            "monthly_spend_usd": round(float((d["vials"] * d["landed_cost_usd"]).sum()), 2),
        },
    }
