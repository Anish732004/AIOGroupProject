# PharmaShield GCC - Layer 1 Data Quality Report

Generated (UTC): 2026-11-15T18:09:04Z

## Source status

| Source | Status | Rows out | Notes |
|---|---|---|---|
| scms | OK | 10316 | late rate 11.5%; 7771 train / 2545 test |
| ghsc_psm | SKIPPED |  | optional stretch dataset (plan 3.2) not supplied |
| internal_gpo | PROXY |  | confidential GPO ERP / Tatmeen data not supplied - SCMS is the proxy (plan 3) |
| openfda_ndc | OK | 18 | 18 labelers in panel (11 finished injection, 7 bulk API only) |
| openfda_label | OK | 13 |  |
| openfda_recalls | OK | 4961 |  |
| openfda_shortages | OK | 35 | 35 SKU records (35 active); oncology current: 84 records / 8 molecules |
| fda_inspections | OK | 9262 | mode=manual_export |
| worldbank | OK | 217 | 169 countries with LPI |
| warning_letters | OK | 50 |  |
| contracts | OK | 11 |  |
| scenario | OK | 18 | quotes + entity links built |
| suppliers_matrix | OK | 18 | locked schema (plan 5.1); 15 probation; C2/C4 pending Layer 3 |

## Checks (non-passing first)

| Source | Check | Affected | % | Severity | Action | Detail |
|---|---|---|---|---|---|---|
| scms | exact_duplicate_lines | 4/10324 | 0.04 | warning | quarantined (kept lowest ID) |  |
| scms | date_order_violation(delivered<PO or PO<PQ) | 10/10320 | 0.1 | warning | kept + flagged (exclude in ML if desired) |  |
| scms | implausible_delay_abs_gt_365d | 4/10324 | 0.04 | warning | quarantined (likely keying error) |  |
| openfda_ndc | duplicate_product_ndc | 7/48 | 14.58 | warning | kept latest listing |  |
| openfda_label | labels_without_country | 10/13 | 76.92 | warning | manual override via reference/manufacturer_overrides.csv |  |
| openfda_recalls | missing_key_fields | 1/4962 | 0.02 | warning | quarantined |  |
| openfda_recalls | unparseable_classification | 1/4961 | 0.02 | warning |  |  |
| worldbank | wgi_political_stability_out_of_range | 24/3904 | 0.61 | warning | quarantined |  |
| scenario | labelers_without_plant_country | 4/18 | 22.22 | warning | NEUTRAL values used (median of rankable makers with a known country), flagged | Fresenius Kabi USA, LLC, Sicor de Mexico S.A. de C.V, Umicore Agrentina s.A., Veranova, L.P. |
| scenario | labelers_missing_lpi | 4/18 | 22.22 | warning | neutral value 3.40 (median of rankable makers with a known country) + flagged |  |
| scenario | c1_price_outliers_capped_at_1.0 | 1/18 | 5.56 | warning | min-max scaled on inliers only; raw USD kept in C1_landed_cost_usd_raw | AVYXA Pharma, LLC |
| scms | rows_read | 10324 |  | info |  | SCMS_Delivery_History_Dataset.csv sha256=918b992dd3e8 |
| scms | step:1 raw file read | 10324 |  | info |  | shape=(10324, 33); target not built yet |
| scms | step:2 blank rows + duplicates removed | 10320 |  | info |  | shape=(10320, 33); target not built yet |
| scms | date_unparseable:scheduled_delivery_date | 0/10320 | 0.0 | info | set NaT | [] |
| scms | date_unparseable:delivered_to_client_date | 0/10320 | 0.0 | info | set NaT | [] |
| scms | date_unparseable:delivery_recorded_date | 0/10320 | 0.0 | info | set NaT | [] |
| scms | date_unparseable:pq_first_sent_to_client_date | 0/10320 | 0.0 | info | set NaT | [] |
| scms | date_sentinel:pq_first_sent_to_client_date | 2678/10320 | 25.95 | info | set NaT + status column | {'pre_pq': 2473, 'not_captured': 205} |
| scms | date_unparseable:po_sent_to_vendor_date | 0/10320 | 0.0 | info | set NaT | [] |
| scms | date_sentinel:po_sent_to_vendor_date | 5729/10320 | 55.51 | info | set NaT + status column | {'from_rdc': 5401, 'not_captured': 328} |
| scms | step:3 dates parsed (errors=coerce) + target late built | 10320 |  | info |  | shape=(10320, 40); late=1186 (11.49%) on_time=9134 |
| scms | step:4 numeric fields coerced + impossible values removed | 10320 |  | info |  | shape=(10320, 40); late=1186 (11.49%) on_time=9134 |
| scms | zero_value_or_zero_price_lines | 103/10320 | 1.0 | info | kept + flagged (donations/samples; excluded from price features) |  |
| scms | line_value_vs_qty_x_pack_price_mismatch | 1/10320 | 0.01 | info | flagged |  |
| scms | freight_text_values | 4122/10320 | 39.94 | info | categorised | {'numeric': 6198, 'reference': 2441, 'included_in_commodity': 1442, 'captured_separately': 239} |
| scms | weight_text_values | 3948/10320 | 38.26 | info | categorised | {'numeric': 6372, 'reference': 2441, 'captured_separately': 1507} |
| scms | freight_references_to_non_numeric_line | 105/2441 | 4.3 | info | NaN; status inherited from referenced line (e.g. invoiced separately) |  |
| scms | freight_shared_shipment_allocated | 3577/10320 | 34.66 | info | allocated by line-value share |  |
| scms | weight_references_to_non_numeric_line | 126/2441 | 5.16 | info | NaN; status inherited from referenced line (e.g. invoiced separately) |  |
| scms | weight_shared_shipment_allocated | 3549/10320 | 34.39 | info | allocated by line-value share |  |
| scms | insurance_missing_imputed | 287/10320 | 2.78 | info | imputed = line value x same-year median insurance rate (flagged) |  |
| scms | step:5 freight/weight coerced, shared shipments allocated, insurance imputed | 10320 |  | info |  | shape=(10320, 56); late=1186 (11.49%) on_time=9134 |
| scms | shipment_mode_missing | 360/10320 | 3.49 | info | category 'Unknown' (not imputed - avoids inventing air/sea) |  |
| scms | site_country_unmapped | 0/10320 | 0.0 | info | country='Unknown' - add row to reference/scms_site_country.csv | [] |
| scms | site_country_low_or_no_confidence | 61/10320 | 0.59 | info | kept; verify rows marked low/none in reference file | {'Bio-Rad Laboratories': 40, 'Not Applicable': 12, 'INVERNESS ANY': 3, 'Human Diagnostic': 3, 'ABBSP': 1, 'BUNDI INTERNATIONAL DIAGNOSTICS LTD': 1, 'INVERNESS ORGENICS LINE': 1} |
| scms | step:6 categoricals standardised + plant country mapped | 10320 |  | info |  | shape=(10320, 64); late=1186 (11.49%) on_time=9134 |
| scms | class_balance_late | 1186/10316 | 11.5 | info |  | by split: {'test': {'size': 2545, 'mean': 0.1399}, 'train': {'size': 7771, 'mean': 0.1068}} |
| scms | step:7 implausible delays removed + chronological split assigned | 10316 |  | info |  | shape=(10316, 66); late=1186 (11.50%) on_time=9130 |
| scms | freight_to_value_ratio_gt_10x | 50/10316 | 0.48 | info | kept + flagged (tiny-value lines) |  |
| scms | robust_outlier:unit_price | 651/10316 | 6.31 | info | FLAGGED only - retained as Isolation Forest signal |  |
| scms | robust_outlier:freight_to_value_ratio | 1160/10316 | 11.24 | info | FLAGGED only - retained as Isolation Forest signal |  |
| scms | robust_outlier:weight_kg_per_unit | 825/10316 | 8.0 | info | FLAGGED only - retained as Isolation Forest signal |  |
| scms | robust_outlier:line_item_value | 35/10316 | 0.34 | info | FLAGGED only - retained as Isolation Forest signal |  |
| scms | step:8 features engineered + outliers flagged (final) | 10316 |  | info |  | shape=(10316, 74); late=1186 (11.50%) on_time=9130 |
| scms | rows_out_clean | 10316/10324 | 99.92 | info |  | retained 10316/10324 |
| scms | site_features_low_history_sites | 29/83 | 34.94 | info | flagged (use country prior; probation logic in Layer 4) |  |
| openfda_ndc | records_fetched_union_of_queries | 48 |  | info |  | generic_name:carboplatin / active_ingredients.name:carboplatin / brand_name:paraplatin |
| openfda_ndc | excluded:not_human_rx | 7/41 | 17.07 | info | excluded from SKU gate |  |
| openfda_ndc | excluded:not_finished_dosage_form | 7/41 | 17.07 | info | excluded from SKU gate |  |
| openfda_ndc | excluded:not_injection | 7/41 | 17.07 | info | excluded from SKU gate |  |
| openfda_ndc | excluded:concentration_mismatch | 7/41 | 17.07 | info | excluded from SKU gate |  |
| openfda_ndc | excluded:unapproved_marketing_category | 7/41 | 17.07 | info | excluded from SKU gate |  |
| openfda_ndc | products_in_scoring_panel | 41/41 | 100.0 | info |  | panel_scope=all_ndc_labelers; {'finished_injection': 34, 'bulk_api': 7} |
| openfda_ndc | labelers_bulk_api_only | 7/18 | 38.89 | info | kept in panel + flagged (no finished-injection authorization) | Cipla Ltd., Heraeus Precious Metals GmbH & Co. KG, Hetero Labs Limited, Sicor de Mexico S.A. de C.V, SUN PHARMACEUTICAL INDUSTRIES, INC., Umicore Agrentina s.A., Veranova, L.P. |
| openfda_ndc | qualified_labelers | 18 |  | info |  | Accord Healthcare, Inc., Apotex Corp., AVYXA Pharma, LLC, BPI Labs LLC, Cipla Ltd., Eugia US LLC, Fresenius Kabi USA, LLC, Gland Pharma Limited, Heraeus Precious Metals GmbH & Co. KG, Hetero Labs Limi |
| openfda_label | labels_mentioning_multiple_countries | 1/13 | 7.69 | info | first 'manufactured by' country used; review snippet |  |
| openfda_recalls | emails_redacted | 8 |  | info | replaced by [EMAIL] (PDPL data minimisation) |  |
| openfda_shortages | emails_redacted | 1 |  | info | replaced by [EMAIL] (PDPL data minimisation) |  |
| openfda_shortages_oncology | distinct_active_oncology_molecules | 8/84 | 9.52 | info |  |  |
| fda_inspections | duplicate_rows | 38/9300 | 0.41 | info | removed (multi project-area rows kept) |  |
| fda_inspections | classification_mix | 880/9262 | 9.5 | info |  | {'VAI': 4470, 'NAI': 3912, 'OAI': 880} |
| worldbank | aggregates_removed | 79/296 | 26.69 | info | removed (regions/income groups) |  |
| worldbank | countries_missing_lpi_score | 48/217 | 22.12 | info | left NaN - Layer 2 should fall back to regional median and flag |  |
| worldbank | countries_missing_wgi_political_stability | 10/217 | 4.61 | info | left NaN - Layer 2 should fall back to regional median and flag |  |
| worldbank | lpi_older_than_6y | 31/169 | 18.34 | info | flagged | WGI series used: GOV_WGI_PV.EST (source=3) |
| warning_letters | duplicate_documents(url/marcs/text-hash) | 1/51 | 1.96 | info | quarantined |  |
| warning_letters | pii_redactions | 152 |  | info | redacted (UAE PDPL) |  |
| warning_letters | documents_collected | 50 |  | info |  | cgmp=50 sterility=28 data_integrity=14 |
| contracts | documents_collected | 11 |  | info |  |  |
| scenario | plant_country_from_hq_hint | 4/18 | 22.22 | info | flagged - verify plant | Cipla Ltd., Heraeus Precious Metals GmbH & Co. KG, Hetero Labs Limited, SUN PHARMACEUTICAL INDUSTRIES, INC. |
| scenario | entity_links_rejected_by_reviewer | 17 |  | info | removed before counting | 15 decision row(s) in reference/entity_match_decisions.csv |
| scenario | entity_links_found | 138 |  | info |  | {'fda_inspections': 65, 'openfda_recalls': 23, 'scms': 15, 'warning_letters': 14, 'contracts': 12, 'openfda_shortages': 9} |
| scenario | entity_links_needing_manual_check | 66/138 | 47.83 | info | review entity_match_candidates.csv (plan 5.2 step 3) |  |
| scenario | makers_scored_on_their_factory_only | 9/18 | 50.0 | info |  | neutral (factory unknown): ['AVYXA PHARMA', 'FRESENIUS KABI USA'] |
| scenario | injectable_recalls_by_seller | 58 |  | info |  | parent-company recalls not naming the seller (shown, not scored): 1 |
| scenario | labelers_inspections_scoped_to_all_company_plants | 2/18 | 11.11 | info | no plant in the maker's country (or country unknown): all company plants used - verify | Sicor de Mexico S.A. de C.V, Umicore Agrentina s.A. |
| scenario | probation_labelers(<5 historical shipments) | 15/18 | 83.33 | info |  | Cipla Ltd., Hetero Labs Limited, SUN PHARMACEUTICAL INDUSTRIES, INC. have history |
| scenario | c2_inference_rows_without_site_prior | 15/18 | 83.33 | info | use country / corridor prior (plan 3.1 'where available') |  |
| suppliers_matrix | C2_delivery_risk_pending_downstream_engine | 18/18 | 100.0 | info | left empty for Layer 3 (not a Layer 1 output) |  |
| suppliers_matrix | C4_compliance_risk_pending_downstream_engine | 18/18 | 100.0 | info | left empty for Layer 3 (not a Layer 1 output) |  |
| scms | missing_critical_columns | 0 |  | pass |  |  |
| scms | blank_rows | 0/10324 | 0.0 | pass | quarantined |  |
| scms | duplicate_primary_key_id | 0/10324 | 0.0 | pass | quarantined (kept first) |  |
| scms | missing_scheduled_or_delivered_date | 0/10324 | 0.0 | pass | quarantined (no label) |  |
| scms | non_numeric:line_item_quantity | 0/10320 | 0.0 | pass | NaN |  |
| scms | non_numeric:line_item_value | 0/10320 | 0.0 | pass | NaN |  |
| scms | non_numeric:pack_price | 0/10320 | 0.0 | pass | NaN |  |
| scms | non_numeric:unit_price | 0/10320 | 0.0 | pass | NaN |  |
| scms | non_numeric:unit_of_measure_per_pack | 0/10320 | 0.0 | pass | NaN |  |
| scms | non_numeric:line_item_insurance_usd | 0/10320 | 0.0 | pass | NaN |  |
| scms | impossible_qty_or_value | 0/10324 | 0.0 | pass | quarantined |  |
| scms | unit_price_vs_pack_price_mismatch(>50%) | 0/10320 | 0.0 | pass | flagged (small gaps are 2-dp rounding) |  |
| scms | freight_references_unresolved | 0/2441 | 0.0 | pass | NaN |  |
| scms | weight_references_unresolved | 0/2441 | 0.0 | pass | NaN |  |
| scms | schema_contract | 0 |  | pass |  |  |
| openfda_ndc | excluded:combination_or_wrong_molecule | 0/41 | 0.0 | pass | excluded from SKU gate |  |
| openfda_ndc | excluded:listing_expired | 0/41 | 0.0 | pass | excluded from SKU gate |  |
| openfda_ndc | excluded:marketing_ended | 0/41 | 0.0 | pass | excluded from SKU gate |  |
| openfda_ndc | labelers_with_multiple_name_spellings | 0/18 | 0.0 | pass | collapsed on normalised key |  |
| openfda_ndc | schema_contract | 0 |  | pass |  |  |
| openfda_recalls | duplicate_recall_number | 0/4962 | 0.0 | pass | kept last |  |
| openfda_recalls | schema_contract | 0 |  | pass |  |  |
| openfda_shortages | emails_redacted | 0 |  | pass | replaced by [EMAIL] (PDPL data minimisation) |  |
| openfda_shortages_sku | duplicates_removed | 0/35 | 0.0 | pass | kept latest update_date per company+package |  |
| openfda_shortages_sku | unparseable_update_date | 0/35 | 0.0 | pass |  |  |
| openfda_shortages_sku | update_date_in_future | 0/35 | 0.0 | pass |  |  |
| openfda_shortages_oncology | duplicates_removed | 0/84 | 0.0 | pass | kept latest update_date per company+package |  |
| openfda_shortages_oncology | unparseable_update_date | 0/84 | 0.0 | pass |  |  |
| openfda_shortages_oncology | update_date_in_future | 0/84 | 0.0 | pass |  |  |
| fda_inspections | missing_fei/classification/date | 0/9300 | 0.0 | pass | quarantined |  |
| fda_inspections | non_drug_rows_removed | 0/9300 | 0.0 | pass |  |  |
| fda_inspections | older_than_5y_removed | 0/9300 | 0.0 | pass |  |  |
| fda_inspections | future_dated_inspections | 0/9262 | 0.0 | pass |  |  |
| fda_inspections | schema_contract | 0 |  | pass |  |  |
| worldbank | lpi_score_out_of_range | 0/1379 | 0.0 | pass | quarantined |  |
| worldbank | schema_contract | 0 |  | pass |  |  |
| warning_letters | letters_unreachable | 0/51 | 0.0 | pass |  |  |
| warning_letters | too_short_documents | 0/51 | 0.0 | pass | quarantined |  |
| contracts | too_short_documents | 0/11 | 0.0 | pass | quarantined |  |
| contracts | duplicate_documents(url/marcs/text-hash) | 0/11 | 0.0 | pass | quarantined |  |
| contracts | pii_redactions | 0 |  | pass | redacted (UAE PDPL) |  |
| scenario | corridor_assumption_validation | 0 |  | pass |  |  |
| scenario | schema_contract | 0 |  | pass |  |  |
| scenario | rapidfuzz_available | 0 |  | pass |  |  |
| suppliers_matrix | schema_contract | 0 |  | pass |  |  |
| scenario | plan_figures_that_differ_from_live_data | 0/6 | 0.0 | pass | quote the live figure on slides |  |
