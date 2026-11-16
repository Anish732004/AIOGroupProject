# PharmaShield GCC — Layer 3: AI Risk Engines (C2, C3, C4)

Master Implementation Plan §2 (Layer 3), §4.3 (formulas), §5.2 steps 4–6. Owners: Member 4A (C2, C3), Member 4B (C4).

```bash
cd layer1_ingestion && python run_ingestion.py      # Layer 1 + 2 first (writes the matrix with C2-C4 empty)
cd ../layer3_engines && pip install -r requirements.txt
python run_engines.py                                # ~15 s; fills C2, C3, C4, shap_top3_reasons
python -m pytest -q                                  # 12 tests
```

**Re-run `run_engines.py` every time Layer 1 is re-run.** Layer 1 rewrites `suppliers_matrix.csv` with C2–C4 empty.

## Evidence rule changes (15 Nov 2026, see docs/DECISIONS.md)

* **C2:** shipping mode, delivery terms, freight ratio and weight are not known for 2026 UAE shipments, so each maker's
  C2 is the **average** prediction over real SCMS shipments from its plant country (all countries when fewer than 30).
  A maker whose plant country is unknown gets the median C2 of the others.
* **C3 and probation:** only the maker's **own** shipment history counts (no parent-company history). All 11
  rankable makers are therefore on probation and get C3 = 0.0 (plan default).
* **C4:** inspections and warning letters come from **the factory that makes the carboplatin** (FDA factory number);
  other plants are shown as a note and never scored. Recalls: the injectable Class I/II recalls issued by the company on
  the box, the same rule for every maker. **The contract term is 0 for every maker**, because the contracts are synthetic;
  the extraction is kept as a demo.

## What it does, in one line each

| Criterion | Question it answers | Method | Trained / built on |
|---|---|---|---|
| **C2** delivery risk | How likely is a late delivery from this maker? | XGBoost + SHAP, vs. a Logistic Regression baseline | SCMS shipments ≤ 2013, tested on 2014–15 |
| **C3** price integrity | How often does this maker's billing look abnormal? | Isolation Forest (5% contamination) per product group | SCMS invoice lines |
| **C4** compliance & contract | How risky is this maker's FDA record and contract? | FDA terms from Layer 1 + TF-IDF warning-letter classifier + LLM contract extraction | FDA inspections, recalls, 50 warning letters, 11 contracts |

All three are in [0, 1], lower is better, and are written into the locked columns of
`data/processed/suppliers_matrix.csv`. The 16 locked columns keep their names and order; supporting columns are
appended after them.

## Results (15 Nov 2026 snapshot)

**C2 — out-of-time test on 2,545 shipments from 2014–15 (14% late)**

| Model | ROC-AUC | Recall (late) | Precision (late) |
|---|---|---|---|
| XGBoost (scale_pos_weight 19.6) | **0.798** | **0.92** | 0.20 |
| Logistic Regression baseline | 0.786 | 0.86 | 0.29 |

XGBoost wins on ROC-AUC and recall, as the plan requires (catch late shipments), at the cost of more false alarms.
Tree settings were picked on the 2013 validation year by ROC-AUC, and `scale_pos_weight` by F2 (recall-weighted).
The test years were never used for choosing anything. Full grids: `outputs/c2_metrics.json`.

**C3** — 8,436 lines scored, 422 flagged (5.0%). 1,836 lines cannot be scored because SCMS has no freight figure
("Freight Included in Commodity Cost"). Three slide-ready examples are in `outputs/c3_anomaly_examples.csv`, e.g.
*"$4,117 freight on a $5.06 line: freight = 813.6× the goods value (group median 0.06×)"*.

**C4 warning-letter classifier** (out-of-fold ROC-AUC, 50 letters): sterility 0.99, data integrity 0.97, process
validation 0.79, quality unit 0.63 (46 of 50 letters cite it, so there is little to tell apart).
**C4 contracts:** the LLM extraction and the independent rule extractor agree on all 4 clauses in 11/11 contracts.

## How each engine works (and the traps it avoids)

**C2 (`engines/c2_delivery.py`)**
* Features (plan §4.3): plant country, shipping mode, freight-to-value ratio, weight, Incoterm, site delivery history.
* Site history = smoothed late rate of the plant. Training rows use out-of-fold values (no row sees its own label);
  test rows and the 2026 panel use train-period values only.
* **No-history trap, fixed:** the number of past shipments is *not* a model input. With it, the model learned
  "no history = never late" (only 19 such training rows, all on time) and ranked every new supplier safest. Now an
  unknown site gets the neutral global late rate (plan §3.1 and Q&A 5: missing history is not bad, nor good).
* `C2_delivery_risk` is the model probability corrected back to the real base rate (class weighting inflates odds by
  `scale_pos_weight`); the uncorrected score is kept as `c2_score_weighted_model`.
* `shap_top3_reasons`: XGBoost's exact TreeSHAP, grouped to the six plan features, e.g.
  `{"feature": "Site delivery history", "value": "2575 past shipments, late rate 13.8%", "effect": "raises late-delivery risk"}`.

**C3 (`engines/c3_anomaly.py`)** — `IsolationForest(contamination=0.05, random_state=42)` within each product group on
log unit price, freight ÷ line value, and line value. C3 = flagged ÷ scored lines of the maker's linked SCMS lines.
Probation suppliers = 0.0 (plan §4.3).

**C4 (`engines/c4_compliance.py`)** — `C4 = min(1, 0.30·I(OAI) + 0.10·I(VAI) + 0.20·min(1, recalls/2) + 0.20·NLP + 0.20·Contract)`
* FDA terms come from Layer 1 (`C4_fda_component_partial`): CGMP inspections at the maker's plants in its country,
  sterile-injectable recall events.
* Warning letters: labels come from the 21 CFR 211 sections each letter cites (211.113(b) sterility, 211.68 / 211.194
  data integrity, 211.100 / 211.110 process validation, 211.22 / 211.192 quality unit), plus phrase rules for API
  letters. The classifier sees the text **with every citation removed**, so it learns from the narrative, not from
  the label source. Severity weights: sterility 1.0, data integrity 1.0, process validation 0.6, quality unit 0.5.
  A maker's score is its worst linked letter in the last 5 years (`worst_letter` column says which).
* Contracts: Force Majeure (0 Hormuz excluded / 0.5 balanced / 1 supplier discretion), lead time
  ((days − 30) ÷ 60), late-delivery penalty (0 weekly damages / 0.5 after 30 days / 1 none), single-source
  (1 if the buyer is locked in). Contract risk = mean of the four. **Demo only: not part of C4 (synthetic contracts).** Source: zero-shot Claude extraction cached in
  `reference/contract_extraction_llm.json` (plan §5.2 cut order: cached JSON instead of a live call), bound to each
  contract's SHA-256; a changed or new contract falls back to the rule extractor. A contract counts only for the company
  that signed it (Apotex does not inherit Teyro's agreement).

## Outputs (`layer3_engines/outputs/`, regenerated each run)

`c2_metrics.json` · `c2_panel_predictions.csv` · `c2_feature_importance.csv` · `c2_test_predictions.csv` ·
`c3_metrics.json` · `c3_panel_scores.csv` · `c3_anomaly_examples.csv` (slide 4) · `c3_scored_lines.csv` ·
`c4_metrics.json` · `c4_panel_scores.csv` · `c4_warning_letters_classified.csv` · `c4_contract_clauses.csv` (slide 5) ·
`layer3_summary.json`

## Honest limits (say these if asked)

* **SCMS is HIV/ARV logistics (2006–15) to Africa and elsewhere, never to the Gulf.** C2 learns shipment physics, not
  oncology. Makers in the same plant country with no own history get the same C2 (the 8 Indian makers share 0.103).
* **C3 is 0.0 for every rankable maker** (all on probation). Isolation Forest still runs and finds 422 unusual lines in
  SCMS; the 3 slide examples are real.
* **Warning letters:** labels come from the regulations each letter cites, not from human labelling. 50 hand-picked
  letters; "no letter" means "none in our sample". The quality-unit class is weak (46 of 50 letters cite it).
* **Contracts are synthetic** and not scored; the extraction is GenAI-generated (red dashed outline, plan §6.1).
* **Recalls** are counted per seller: companies that sell more products tend to have more recalls.
