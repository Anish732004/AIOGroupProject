# Plan traceability — every requirement of the Master Implementation Plan, and where it is met

One row per requirement in the plan (13 pages, 14 Nov 2026), in the plan's order. Status:
**Done** = built and checked · **Done, differs** = built, with a deliberate difference listed on the website's Evidence &
trust page ("Where this differs from the project plan") and in `docs/DECISIONS.md` · **Team** = a presentation or
submission task for the team, not code.

Automatic checks: `python tools/check_consistency.py` (plan constants vs code vs website), the test suites of each layer,
`node tools/e2e_web.mjs` (website in Chrome). Numbers for the slides: last table of `notebooks/03_layer4_decision.ipynb`.

## §1 Executive overview

| Plan requirement | Status | Where |
|---|---|---|
| Profile qualified manufacturers per SKU on five risk dimensions | Done | `data/processed/suppliers_matrix.csv` (C1–C5) |
| ML predicts shipment delays and pricing anomalies | Done | `layer3_engines/engines/c2_delivery.py`, `c3_anomaly.py` |
| NLP extracts compliance and contract risks | Done | `layer3_engines/engines/c4_compliance.py` |
| Hybrid MCDM (AHP + entropy TOPSIS) | Done, differs | entropy is a 0–50% slider, default 0% (decision L5) |
| Risk-hedged dual-source order split by LP | Done | `layer4_decision/decision/allocation.py` |
| Every recommendation needs human approval | Done | Approve & log (website and Streamlit), hash-chained log |
| §1.2 crisis evidence figures | Done (cited, not re-checked) | website Overview "Why this matters"; slide 1 (Team) |
| §1.3 category manager: shortage alerts, SHAP reasons, one-click Normal/Crisis, approve an auditable split | Done | website and Streamlit; split is 30/30/30/10, not 70/20/10 (Done, differs) |
| §1.3 economic buyer KPIs (switching time, dual-source coverage, cost, compliance) | Done | warm-backup share and factory count on the split page; `docs/QA_DEFENSE.md` Q9; slide 7 (Team) |
| §1.3 build on Tatmeen and the GPO ERP | Done | optional loader `layer1_ingestion/ingestion/optional_sources.py`; SCMS is the proxy (plan §3) |

## §2 Five-layer architecture and rubric

| Plan requirement | Status | Where |
|---|---|---|
| Layer 1: internal data, regulatory feeds, macro and corridor data, documents | Done | `layer1_ingestion/` (catalogue in `DATA_SOURCES.md`) |
| Layer 2: only makers authorised for the SKU; entity resolution | Done | `ingestion/scenario.py`; 18 labelers, 11 ranked (Done, differs: 7 sell only raw powder) |
| Layer 3: C1–C5, all 0 to 1, lower is better | Done | checked by `check_consistency.py` A16 |
| Layer 4: hybrid weights, edge-case-safe TOPSIS, PuLP split | Done, differs | entropy slider (L5); caps per factory (L3) |
| Layer 5: manager reviews SHAP, approves, immutable log | Done | website Order split, Streamlit tab 3, `app/audit.py` |
| Layer 5: monthly model retraining | Done, differs | not built; part of the pilot (plan-differences row) |
| Q1 ranked table with criterion breakdown | Done | website Suppliers; Streamlit tab 1 |
| Q2 360° profile of one manufacturer across SCMS, FDA, World Bank and NLP | Done | website supplier detail (late-delivery reasons, FDA record, World Bank score, letters); Streamlit "360° manufacturer profile" |
| Q3 time-split ROC-AUC and recall vs logistic regression; 3 worked outliers | Done | website Models; notebook 02 |
| Q4 violation severity tags; Force Majeure and SLA clauses | Done | website Documents; Streamlit tab 4 |
| Q5 live ranking and split under Normal vs Crisis | Done, differs | split is 30/30/30/10 and unchanged by Crisis in the real view; changes in the synthetic view |
| Q6 SHAP bars, probation badge, timestamped log, PDPL and AI Charter | Done | website and Streamlit; governance notes |
| Q7 live shortage feed, stress testing, dual-source buffering, warm-backup share KPI | Done | alerts and live check; natural-disaster stress test; warm-backup share (website split page, Streamlit KPI row) |
| Q7 30-second live demo video | Team | record the Streamlit or website demo |

## §3 Data strategy

| Plan requirement | Status | Where |
|---|---|---|
| Training layer: SCMS, about 10,300 shipments | Done | 10,316 clean lines (`plan_vs_live_reconciliation.csv`) |
| Scoring layer: 18 labelers, 35 shortage records, 84 active oncology shortages | Done | all three match the live run of 15 Nov 2026 |
| Scenario layer: World Bank LPI and WGI | Done, differs | LPI scored; WGI fetched and shown, not scored (plan formula §4.3 uses only LPI) |
| Scenario layer: 2026 tender quotes (C1) and corridor shares (C5) | Done, differs | no public quotes or per-country shares: official US price and one share 0.85 (real view); synthetic values in the synthetic view |
| §3.1 C2 by feature-based inference for all 18 makers | Done | all 18 rows have C2; real view averages over real shipments by country (decision item 6) |
| §3.1 probation badge below 5 deliveries | Done | `is_probation`; badge on website and Streamlit |
| §3.1 mandatory 5–10% trial share for 3–6 months | Done, differs | §4.4 rules followed (0, or 5% up to the cap); duration not modelled |
| §3.2 every listed dataset | Done | SCMS, NDC, shortages, recalls, inspections, warning letters, World Bank (`DATA_SOURCES.md`) |
| §3.2 shortage penalty in C4 | Done, differs | shown as alerts and badges, not scored (plan formula §4.3 has no shortage term) |
| §3.2 GHSC-PSM optional check | Done, differs | cut, as the plan's own cut order allows |

## §4 Mathematics

| Plan requirement | Status | Where |
|---|---|---|
| §4.1 one SKU, only authorised makers | Done | Carboplatin Injection 10 mg/mL, 11 finished-vial makers |
| §4.1 C1 volume-weighted landed cost per vial | Done, differs | one official price per vial; freight has no data (real view) |
| §4.1 C4 worst severity across plants registered for the SKU | Done | scored for the factory that makes the product (decision item 2) |
| §4.2 tier table: weights, 70/80/100% caps | Done | `reference/criticality_tiers.csv`; checks A3, A6 |
| §4.2 Tier 1: at least 2 qualified makers | Done | `meets_two_supplier_minimum` in every solve; Layer 4 test |
| §4.2 Tier 1: highest safety stock | Done, differs | not modelled (the plan gives no number) |
| §4.2 AHP pairwise once per tier, CR < 0.10 | Done | CR = 0 from the pairwise matrix implied by the plan's weights (no team survey) |
| §4.2 Crisis: 0.10 from C1 to C5, route ×1.5 capped at 1; Cost Focus reverse | Done | checks A4, A5, A14 |
| §4.2 50/50 blend with entropy weights | Done, differs | slider 0–50%, default 0% (L5) |
| §4.2 non-duplication: C2 single delivery criterion; capacity only in the LP | Done | C2 is the only delivery criterion; capacity is an LP bound |
| §4.3 C1–C5 formulas | Done, differs | as written; contract term 0 in the real view; cost mark "% above cheapest" in the synthetic view |
| §4.3 C2 trained ≤2013, tested 2014–15, scale_pos_weight for recall | Done | check A10; recall 92% |
| §4.3 C3 Isolation Forest, contamination 0.05, seed 42, per product group, 0 for probation | Done | check A11, A17 |
| §4.4 zero-guarded TOPSIS | Done | `layer4_decision/decision/topsis.py`, tests |
| §4.4 LP objective, demand with M = 10⁶, capacity, tier cap, probation floor and cap 15%/30% | Done, differs | caps per factory (L3); trial share only if chosen (L2); whole vials |

## §5 Engineering

| Plan requirement | Status | Where |
|---|---|---|
| §5.1 locked 16-column schema | Done | check A15; synthetic table keeps it (E2) |
| Step 1 clean SCMS, print shape and class balance | Done | notebook 01, `ingestion/scms.py` |
| Step 2 site and corridor features | Done | `scms_site_features_train.csv`, `scms_corridor_features_train.csv` |
| Step 3 live openFDA panel, rapidfuzz ≥88, manual check of top 20 | Done | check A12; `entity_match_decisions.csv` |
| Step 4 XGBoost vs logistic regression, ROC-AUC, recall, confusion matrix, SHAP, all 18 makers | Done | notebook 02; website Models |
| Step 5 Isolation Forest, 3 audit examples | Done | `c3_anomaly_examples.csv`; website Models |
| Step 6a 50–100 warning letters classified | Done | 50 letters, 4 violation types |
| Step 6b LLM JSON extractor over synthetic contracts | Done, differs | cached extraction (the plan's cut order item 2), checked by a rule-based reader |
| Step 7 hybrid TOPSIS under Normal, Crisis, Cost Focus | Done | notebook 03 |
| Step 8 order split for 10,000 vials | Done | notebook 03; `layer4_decision/outputs/` |
| Step 9 4-tab Streamlit cockpit with Approve & Log | Done | `streamlit_app.py` (4 tabs plus a data-pipeline tab) |
| Step 9 30-second fallback video | Team | record it |
| Step 10 re-run the notebooks top to bottom | Done | notebooks 01–03 run on 16 Nov 2026 with no errors (01 on the cached data of 15 Nov; identical outputs) |
| Step 10 cross-check every slide metric against the notebook | Team | use the last table of notebook 03 |
| Step 10 GenAI Prompt Log PDF | Done | `docs/GenAI_Prompt_Log.pdf` (rebuild: `python tools/build_prompt_log_pdf.py`) |
| Contingency cut order (GHSC-PSM, live LLM, entropy slider) | Done | first two cut; entropy slider kept |

## §6 Governance and delivery

| Plan requirement | Status | Where |
|---|---|---|
| UAE PDPL: contact details minimised | Done | redaction in `ingestion/documents.py`; initials only in approval logs |
| UAE AI Charter: top-3 SHAP drivers, no order without sign-off | Done | late-delivery reasons on every supplier; Approve & log |
| Fairness: plant-level evidence, no country blacklisting; probation pathway | Done | factory-level scoring (decision item 2); probation rules |
| GenAI disclosure: red dashed outlines on slides | Team | mark AI-generated content on the deck |
| GenAI disclosure: separate Prompt Log PDF | Done | `docs/GenAI_Prompt_Log.pdf` |
| §6.2 seven slides, owners and speakers | Team | |
| §6.3 deliverables: deck, notebook/code, prompt log PDF | Team (deck); Done (code, notebooks, PDF) | |
| §6.4 scripted Q&A | Done, differs | `docs/QA_DEFENSE.md`: answers rewritten where the results differ (Q2, Q4, Q5) |

## Added beyond the plan

| Addition | Why | Where |
|---|---|---|
| Evidence rule: real data, a labelled stand-in, or "no data" with a neutral value | Team decision (15 Nov 2026) | `docs/DECISIONS.md` |
| Synthetic view | Course professor's advice (16 Nov 2026) | `synthetic/`; switch on the website and in Streamlit |
| Showcase website | Readers without Python | `web/` (Vercel) |
| Plan-vs-code-vs-website consistency check | So the plan, pipeline and website never silently disagree | `tools/check_consistency.py` |
