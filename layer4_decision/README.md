# PharmaShield GCC — Layer 4: Ranking & Dual-Source Order Split

Master Implementation Plan §4.2 (weights and modes), §4.4 (TOPSIS and linear program), §5.2 steps 7–8. Owner: Member 3.

```bash
# after Layer 1 and Layer 3 (they fill data/processed/suppliers_matrix.csv)
cd layer4_decision
pip install -r requirements.txt
python run_decision.py            # Normal, Crisis and Cost Focus modes; lambda 1.0, entropy share 0%
python run_decision.py --synthetic   # synthetic view (decision S4) -> outputs/synthetic/
python -m pytest -q               # 16 tests
```

The cockpit (`streamlit_app.py`, tab 3) runs the same engine live with the mode button and the λ and entropy sliders.

## What it does

| Step | Method | Notes |
|---|---|---|
| Weights | The board's Tier 1 weights (C1 0.10, C2 0.30, C3 0.05, C4 0.30, C5 0.25) | The pairwise matrix implied by the plan's weights is perfectly consistent (CR = 0). `ahp_from_pairwise()` accepts a real team survey. |
| Modes | Normal; Crisis = 0.10 moved from cost to route, plus Hormuz exposure ×1.5 (capped at 1); Cost Focus = 0.10 moved from route to cost | Plan §4.2 |
| Entropy | Shown for information; blended only when the slider is above 0% (max 50%) | **Team decision L5.** On this panel two standard entropy formulas gave opposite weights (cost 46%, or delivery + route 74%) and the ranking swung, so the board's weights drive the ranking. Criteria that do not vary across the makers get no entropy weight (decision 12). |
| Ranking | Zero-guarded TOPSIS; S = closeness to the ideal supplier (higher is better) | Plan §4.4 |
| Order split | PuLP mixed-integer program, solved with HiGHS (CBC fallback) | Demand 10,000 vials/month; emergency spot buy at M = 1,000,000 per vial so a solution always exists |

## Order-split rules (plan §4.4 plus team decisions)

* Objective: Σ (landed cost + λ × mean cost × (1 − S)) × vials + M × spot buy. λ default 1.0 (**L1**).
* Caps apply **per factory** (**L3**): Teyro + Apotex + Natco share one cap; Gland + BPI share one.
* Established factory: up to 70% (Tier 1). A factory whose makers are all on probation: up to 15% when at least 2
  established factories exist, otherwise 30% (plan §4.4).
* A probation maker gets **0, or between 5% and its cap** (**L2**, a yes/no variable per maker).
* Orders are in **whole vials** (integer variables): a continuous solve left orders of 0.1 vial.
* Every solve reports the **warm-backup share** (plan Q7: the order placed outside the main factory) and checks the
  Tier 1 rule of **at least 2 suppliers** (plan §4.2).
* Capacity applies **per factory** (names sharing a factory share it). In the real view it has no public data, so it is
  non-limiting (= demand, decision item 3). The synthetic view uses 1,500–8,000 vials per factory (range R8).

## Results on the 15 Nov 2026 data

All 11 rankable makers are on probation (none has its own delivery history), so each factory is capped at 30%.

| Mode | Split (vials) | Factories | Countries | Spot buy |
|---|---|---|---|---|
| Normal | Gland (BPI) 3,000 · Teyro (Apotex) 3,000 · Pharmachemie (Teva) 3,000 · Hospira Australia 1,000 | 4 | India, Netherlands, Australia | 0 |
| Crisis | same split | 4 | 3 | 0 |
| Cost Focus | same split | 4 | 3 | 0 |

Read this honestly on the slides:

* **No "70/20/10".** That split needs an established supplier, and no maker has its own delivery history with the GPO.
  The plan's own rules give 30/30/30/10 across four factories.
* **Crisis mode changes the ranking but not the split.** With cost weight at 0, Avyxa (lowest route exposure, but
  about 84 times the price) moves from rank 6 to rank 1, and Accord falls to S = 0. The split is unchanged because the
  plan's order-split objective still weighs landed cost, so Avyxa receives no order. The cockpit says so explicitly.
* **The risk penalty is scaled by the mean cost of all rankable makers** (plan formula). Avyxa's price lifts that mean
  from about $28 to about $240, so lambda = 1 already weighs risk heavily against the $28 generics.
* **Same-factory names are interchangeable.** Gland and BPI ship the same factory's product, so the 30% belongs to the
  factory. The tie between the names is broken alphabetically.
* **Plan inconsistency, no effect today:** the tier table says "5–10% probation trial", while §4.4 says a 15% cap. The
  §4.4 values are used; with no established factory, both relax to 30%.

## Synthetic view (decision S4)

`python run_decision.py --synthetic` ranks and splits on `data/processed/suppliers_matrix_synthetic.csv`. Five suppliers
have a synthetic delivery record, so caps become 70% (established) and 15% (new):

| Mode | Split (vials) |
|---|---|
| Normal | Hospira 3,700 · Fresenius 3,300 · Gland 1,500 · Apotex (Teyro factory) 1,500 |
| Crisis | Teva (Pharmachemie) 3,700 · Fresenius 3,300 · Gland 1,500 · Apotex 1,500 |
| Cost Focus | same as Normal |

Details and caveats: [synthetic/README.md](../synthetic/README.md).

## Natural-disaster stress test (decision S1)

`engine.run(..., offline_factories={"TEYRO_ORAGADAM", ...})` gives the named factory groups zero capacity and re-solves the
split. The ranking is unchanged. If the remaining factories cannot cover demand, the shortfall is an emergency purchase.

| What goes offline | Covered by approved suppliers? | Monthly cost (official US prices) |
|---|---|---|
| Nothing | yes | $279,546 |
| Any one factory | yes; the others absorb it | unchanged |
| Every factory in India (4 of 8) | yes, but Avyxa takes 1,000 vials | $2,607,054 (9.3 times) |
| India plus Fresenius (country not stated on its label) | no: 1,000 vials bought in an emergency | $7,234,115 |

The tie-break between equal suppliers now holds the emergency purchase and the supply cost separately and falls back
to the first solve if it cannot finish, so it works even when an emergency purchase is needed.

## Outputs (`layer4_decision/outputs/`, regenerated each run)

`weights_<mode>.csv` · `entropy_<mode>.csv` · `ranking_<mode>.csv` · `allocation_<mode>.csv` · `summary.json`
