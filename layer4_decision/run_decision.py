#!/usr/bin/env python3
"""
PharmaShield GCC - Layer 4: hybrid weights, TOPSIS ranking and PuLP dual-source order split (plan 4.2, 4.4,
5.2 steps 7-8). Runs Normal, Crisis and Cost Focus modes for the target SKU.

    python run_decision.py                    # lambda 1.0, entropy share 0 (team decisions L1, L5)
    python run_decision.py --lambda 0.5 --entropy-share 0.5

Reads   data/processed/suppliers_matrix.csv  (after Layer 1 and Layer 3)
Writes  layer4_decision/outputs/  weights_*.csv, ranking_*.csv, allocation_*.csv, summary.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from decision.engine import DEFAULT_ENTROPY_SHARE, DEFAULT_LAMBDA, load_inputs, run
from decision.weights import MODES

OUT = Path(__file__).resolve().parent / "outputs"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lambda", dest="lam", type=float, default=DEFAULT_LAMBDA)
    ap.add_argument("--entropy-share", type=float, default=DEFAULT_ENTROPY_SHARE)
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    m, tiers, sku = load_inputs()
    summary = {"lambda": a.lam, "entropy_share": a.entropy_share, "modes": {}}
    print(f"\n=== Layer 4 decision engine | lambda {a.lam} | entropy share {a.entropy_share:.0%} ===")
    for mode in MODES:
        r = run(m, tiers, sku, mode, a.lam, a.entropy_share)
        tag = mode.lower().replace(" ", "_")
        r["weights"].to_csv(OUT / f"weights_{tag}.csv")
        r["ranking"].to_csv(OUT / f"ranking_{tag}.csv")
        r["allocation"].to_csv(OUT / f"allocation_{tag}.csv", index=False)
        r["entropy_table"].to_csv(OUT / f"entropy_{tag}.csv", index=False)
        summary["modes"][mode] = {
            "weights_used": r["weights"]["Used for ranking"].to_dict(),
            "ranking": r["ranking"]["rank"].to_dict(),
            "allocation_vials": r["allocation"].set_index("manufacturer_id")["vials"].to_dict(),
            **r["diagnostics"]}
        summary["ahp_consistency"] = r["ahp_consistency"]
        d = r["diagnostics"]
        print(f"\n-- {mode} mode | solver {d['solver_status']} | factories used {d['factories_used']} | "
              f"largest factory {d['largest_factory_share_pct']}% | spot buy {d['spot_buy_vials']} vials")
        al = r["allocation"]
        al = al[al["selected"]]
        with pd.option_context("display.width", 200):
            print(al[["manufacturer_id", "factory_group", "S", "vials", "share_pct", "role"]].to_string(index=False))
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(f"\n  AHP consistency ratio (Tier weights): {summary['ahp_consistency']['CR']}  -> outputs in "
          f"layer4_decision/{OUT.name}/\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
