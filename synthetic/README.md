# PharmaShield GCC — Synthetic view

The course professor advised filling the inputs that have no public evidence with synthetic data. This folder does that
**in a second, clearly marked view**. The real view (`data/processed/suppliers_matrix.csv`) is never changed.
Team decision S4 in [docs/DECISIONS.md](../docs/DECISIONS.md).

```bash
python synthetic/build_synthetic.py                        # after Layer 1 and Layer 3
(cd layer4_decision && python run_decision.py --synthetic)  # order split for the synthetic view
cd synthetic && python -m pytest -q                        # 9 tests
```

## What is invented, and from what

Every value is drawn **once**, with a fixed random seed (42), from a range in
[`reference/synthetic_ranges.csv`](reference/synthetic_ranges.csv). Each range has its basis and source next to it.

| Range | What | Range used | Based on |
|---|---|---|---|
| R1 | Shipment mode for UAE orders | Air | 64–71% of real USAID shipments by air; Emirates SkyCargo pharma volumes |
| R2 | Delivery terms | EXW 58%, DDP 26%, FCA 8%, CIP 8% | Real mix on USAID shipments sent directly by the supplier |
| R3 | Weight per vial | 0.10–0.14 kg | Estimate (vial + liquid + carton); weakest basis |
| R4 | Vials per shipment | 1,000–3,000 | Real median USAID air shipment (357 kg) |
| R5a–c | Air freight per kg | India $2.5–3.5, Europe $2.8–3.7, Australia $3.5–5.0 | Freightos and Loadstar 2026; cross-checked with McKinsey (transport about 1.4% of sales) |
| R6 | Contract risk | the 11 synthetic contracts already in the repo | Plan §4.3 formula, contract term switched on |
| R7 | Invoice lines with an error | 1–4% | APQC and accounts-payable benchmarks; real USAID median 2.3% flagged |
| R8 | Monthly vials a factory can give this buyer | 1,500–8,000, scaled by real US market share | CMS Medicaid 2025 shares; vial lines run 100–400 vials a minute |
| R9 | Share of air cargo exposed to Hormuz or Gulf airspace | 0.90–1.00 | All main UAE cargo airports are inside the Gulf; 2026 airspace closures |
| R10 | Past deliveries to this buyer | 6–24 for the 5 suppliers with at least 9% US market share; others 0 | Real US market share as the sign of an established supplier |
| R11 | On-time rate of those deliveries | 80–95% | USAID GHSC-PSM 86–87%; real USAID data 89%; industry target 95% |

Same-factory names (Apotex, Natco, Teyro; Gland, BPI) share the factory's weight, freight, route share and capacity.
Fresenius's factory country is still unknown, so its freight rate and route share are the middle value of the others.

## How it is scored

The same code as the real pipeline, with the synthetic values as inputs:

* **Late delivery (C2):** the trained XGBoost model predicts on the synthetic shipping profile and delivery record.
  It is trained on the same real USAID data as always; its test score (ROC-AUC 0.797) is unchanged.
* **Billing (C3):** Isolation Forest (plan settings) on 258 synthetic invoice lines of the 5 established suppliers.
  Errors were planted at each supplier's drawn rate; the model flagged all 8 planted errors. New suppliers keep 0.
* **Compliance (C4):** the real FDA terms plus 0.20 × contract risk.
* **Cost (C1):** real price + real insurance + synthetic freight. The mark is "% more expensive than the cheapest,
  capped at 1", because min-max scaling would stretch a 30-cent difference over the whole scale. On the real data it
  gives exactly the plan's marks.
* **Route (C5):** plan formula with the synthetic share.
* **Order split:** probation comes from the synthetic delivery record, and capacity applies per factory.

## Result (Normal mode, risk dial 1)

5 established factories, so the plan's caps are 70% for an established factory and 15% for a new supplier:
Hospira 37%, Fresenius 33% (its full capacity), Gland 15%, Apotex (Teyro factory) 15%. With every Indian factory
offline, Hospira and Fresenius cover the whole order at almost no extra cost.

**Read with care:** the drawn delivery term moves the late-delivery mark most (in the real USAID data EXW shipments
were late 5% of the time, DDP 13%), so two names from the same factory can score differently. That is why the real view
averages over real shipments instead.

## Outputs

`outputs/synthetic_inputs.csv` (one row per ranked supplier) · `outputs/synthetic_invoice_lines.csv` ·
`outputs/synthetic_summary.json` · `../data/processed/suppliers_matrix_synthetic.csv` (locked schema)
