# Layer 1 vs. the Master Implementation Plan — line-by-line check

Status key: ✅ implemented, tested and confirmed by the live run of 15 Nov 2026 · ⬜ not a Layer 1 output (owner named)

## §5.1 Locked schema — `data/processed/suppliers_matrix.csv` (repository root)

Column names, order and types are enforced in code (`scenario.LOCKED_SCHEMA`) and by a test that compares against the plan's list.

| # | Column | Type | Filled by Layer 1? | How |
|---|---|---|---|---|
| 1 | `sku_id` | str | ✅ | `CARBOPLATIN_INJ_10MG_ML` |
| 2 | `criticality_tier` | int | ✅ | 1 (Life-Critical) |
| 3 | `manufacturer_id` | str | ✅ | canonical name after suffix normalisation; links listed in `entity_match_candidates.csv` for manual verification |
| 4 | `labeler_name_fda` | str | ✅ | exact `labeler_name` from openFDA NDC |
| 5 | `manufacturing_country` | str | ✅ | official drug label, checked by hand on DailyMed (`reference/sku_manufacturing_sites.csv`, 10 of 11); not stated → `Unknown` with neutral values |
| 6 | `is_probation` | bool | ✅ | fewer than 5 of the maker's **own** historical shipments in SCMS (no parent-company history; decision 9) |
| 7 | `monthly_capacity_units` | int | ✅ | no public data → non-limiting (= demand, 10,000) for every maker (decision 3) |
| 8 | `C1_landed_cost` | float [0,1] | ✅ | official CMS price + insurance per vial (freight: no data, excluded; decision 4), min-max; raw USD in `C1_landed_cost_usd_raw` |
| 9 | `C2_delivery_risk` | float [0,1] | Layer 3 ✅ | XGBoost `predict_proba`, averaged over real shipments from the plant country (decision 6) |
| 10 | `C3_price_integrity` | float [0,1] | Layer 3 ✅ | Isolation Forest share of flagged lines; 0.0 for probation makers (plan default) |
| 11 | `C4_compliance_risk` | float [0,1] | Layer 3 ✅ | FDA inspections + warning letters of the SKU's factory, seller's injectable recalls; contract term 0 (synthetic contracts, decision 7) |
| 12 | `C5_route_exposure` | float [0,1] | ✅ | `min(1, 1.0 × hormuz_air_share) × (1 − LPI ÷ 5)` (Normal mode); one evidence-based share 0.85 for every origin (decision 5) |
| 13 | `hormuz_air_share` | float [0,1] | ✅ | 0.85 for every origin, from UAE port volumes (`reference/scenario_corridor_assumptions.csv`) |
| 14 | `active_fda_shortage` | bool | ✅ | any active openFDA shortage record linked to the labeler |
| 15 | `oai_count_5yr` | int | ✅ | distinct OAI CGMP inspections of the SKU's factory (FDA factory number), last 5 years |
| 16 | `shap_top3_reasons` | str (JSON) | Layer 3 ✅ | top 3 SHAP drivers of C2, in plain English |

Supporting columns are appended after column 16, never between the locked ones.
The schema, with the plan's definitions and a pass / fail per column, is shown in the dashboard tab **Data schema (§5.1)**
(visible before a run) and re-checked in the notebook.

## Other plan items that touch data ingestion

| Plan reference | Requirement | Status | Where |
|---|---|---|---|
| §2 rubric, Q2 | "360° profile of one manufacturer fused across SCMS, FDA, World Bank & NLP" | ✅ | dashboard tab **360° manufacturer profile** |
| §2 rubric, Q7 | Live openFDA shortage feed / alert banner | ✅ 35 carboplatin records (live run 15 Nov 2026) | `fda_shortages_sku.csv`, banner on the website and in Streamlit, live check button |
| §3 item 2 | Report labelers, carboplatin shortage records and active oncology shortages | ✅ plan figure vs live figure | `plan_vs_live_reconciliation.csv` |
| §3.1 | Feature-based inference rows for every Carboplatin maker: plant country, shipping-mode profile, freight parameters, site delay priors where available | ✅ | `panel_inference_features.csv` |
| §3.1 | Probation badge: fewer than 5 historical deliveries | ✅ | `is_probation` |
| §4.1 | C4 = worst severity across all plants → needs plant-level inspections | ✅ | `panel_facility_inspections.csv` |
| §4.2 | SKU criticality tier from the WHO Essential Medicines List; tier rules and baseline weights | ✅ reference data | `reference/sku_master.csv`, `reference/criticality_tiers.csv` |
| §4.2 | Crisis mode: corridor exposure × 1.5, capped at 1.0 | ✅ supporting column | `C5_route_exposure_crisis` |
| §4.3 | C4 FDA terms `0.30·I(OAI) + 0.10·I(VAI) + 0.20·min(1, recalls ÷ 2)` | ✅ supporting column (NLP terms are Member 4B's) | `C4_fda_component_partial` |
| §4.3 | `quotes_2026_carboplatin.csv` | ✅ | `data/processed/` |
| §4.4 | Monthly capacity as a hard LP bound; demand D = 10,000 | ✅ | `monthly_capacity_units`, `reference/sku_master.csv` |
| §5.2 step 2 | Site **and corridor** features | ✅ | `scms_site_features_train.csv`, `scms_corridor_features_train.csv` |
| §5.2 step 3 | Manual check on top 20 | ✅ shortlist + decisions file honoured on the next run | `entity_match_top20_manual_check.csv`, `reference/entity_match_decisions.csv` |
| §5.2 step 10 | Notebook re-runnable top to bottom | ✅ | `notebooks/01_layer1_data_ingestion.ipynb` |
| §6.1 | PDPL: contact details minimised | ✅ e-mails, phones, salutation names redacted | `ingestion/documents.py` |
| §6.1 | GenAI disclosure + prompt log | ✅ | `docs/GENAI_PROMPT_LOG_layer1.md` |

Other layers: XGBoost + SHAP, Isolation Forest, warning-letter and contract readers (`layer3_engines/`); AHP, entropy,
TOPSIS, PuLP and the disaster stress test (`layer4_decision/`); the showcase website (`web/`, Vercel) and the Streamlit
operator tool (`streamlit_app.py`); the synthetic view (`synthetic/`). Every plan item is traced in
`docs/PLAN_TRACEABILITY.md`; every deliberate difference, with its reason, is in `docs/DECISIONS.md` and on the website's
Evidence & trust page.

## §3.2 Dataset inventory

| Plan dataset | Status | Where |
|---|---|---|
| USAID SCMS Delivery History | ✅ real file, 10,324 rows | `ingestion/scms.py` |
| openFDA NDC Directory API | ✅ 18 labelers (live run 15 Nov 2026) | `ingestion/openfda.py` |
| openFDA Drug Shortages API | ✅ 35 records (live run 15 Nov 2026) | `ingestion/openfda.py` |
| openFDA Drug Enforcement API | ✅ 4,961 recall records, 5 years (live run 15 Nov 2026) | `ingestion/openfda.py` |
| FDA Data Dashboard Inspections (bulk) | ✅ manual export (the automatic link returned 404 on 15 Nov 2026), 9,262 drug inspections loaded | `ingestion/fda_inspections.py` |
| FDA CGMP Warning Letters | ✅ 50 letters read (1 of the 51 URLs was a duplicate; live run 15 Nov 2026) | `data/manual/warning_letters/urls.csv` |
| World Bank LPI & WGI | ✅ 217 countries (live run 15 Nov 2026) | `ingestion/worldbank.py` |
| USAID GHSC-PSM (optional stretch) | ✅ optional loader; skipped if no file (first item in the plan's cut order) | `ingestion/optional_sources.py` |
| Supplier MSAs (synthetic) | ✅ 11 shipped | `data/manual/contracts/` |
| Internal GPO ERP / delivery logs / Tatmeen scans (§2) | ✅ optional loader; SCMS is the proxy per §3 | `ingestion/optional_sources.py` |
| Scenario layer: 2026 quotes + corridor shares (§3 item 3) | ✅ labelled SCENARIO | `reference/`, `data/processed/quotes_2026_carboplatin.csv` |

## §5.2 Build steps owned by data engineering

| Step | Plan wording | Status |
|---|---|---|
| 1 | Parse both dates with `errors='coerce'`, dropping text such as "See ASN" | ✅ |
| 1 | Coerce non-numeric `Freight Cost (USD)` to numeric | ✅ `freight_cost_usd_coerced` (plan-literal) + `freight_usd` (shared shipments allocated) |
| 1 | `late = delivered > scheduled` | ✅ |
| 1 | Print shape and class balance at every step | ✅ 8 `STEP` lines, also in the quality report |
| 2 | On-time rate, mean and p90 delay, freight-to-value ratio, unit price variance, air share per site; corridor features | ✅ train period only |
| 3 | Live openFDA NDC + Shortages for Carboplatin Injection labelers | ✅ 18 labelers, 35 shortage records |
| 3 | Normalise corporate suffixes; `rapidfuzz token_sort_ratio ≥ 88` + manual check | ✅ candidates file flags every non-exact link |
| 3 | Link to inspections, recalls, World Bank LPI/WGI | ✅ |
| 4 | Chronological split: train ≤ 2013, test 2014–2015 | ✅ `time_split` (7,771 / 2,545) |

## One point where the plan and the live data disagree

The plan says the NDC directory returned **18 labelers including Cipla and Hetero**. The live run on 15 Nov 2026
confirms **18**: **11** sell finished carboplatin vials and **7** (including Cipla and Hetero) list only the bulk
ingredient. All 18 are kept in `suppliers_matrix.csv`; only the 11 finished-vial makers (`eligible_for_ranking`) are
ranked and receive orders, because a bulk-powder seller cannot supply hospital vials (plan §4.1).
