# GenAI Prompt Log — Layer 1 fixes, Layer 2 (entity resolution) and Layer 3 (AI risk engines)

Plan §6.1 disclosure protocol. Tool: Claude Code (Anthropic; Claude Sonnet 5.5, then Claude Opus 5.5), 15 November 2026.
Everything under `layer3_engines/`, `notebooks/02_layer3_risk_engines.ipynb` and the Layer 1 / Layer 2 changes listed
below is GenAI-generated and should carry the red dashed outline on slides. Prompts are verbatim.

| # | Prompt (verbatim) | What was generated |
|---|---|---|
| 1 | "yes resolve the errors." | Recall feed no longer crashes on a record without a recall number (quarantined instead); clear message that FDA retired the inspections download link; `inspection_data_available` column |
| 2 | "yes i included the file in the specified folder. i guess you are going to filter outs to drugs part of it right?? also fix the other changes." | Drug-only, 5-year streaming filter for the manual inspections export; C1 normalisation robust to the branded AVYXA price; maker-specific SCENARIO capacities; origin-specific Hormuz / Gulf-air shares; `eligible_for_ranking` filter for bulk-powder labelers |
| 3 | "fix the remaning weakness" | Inspections scoped to CGMP ("Drug Quality Assurance") inspections at plants in the maker's country, counted as distinct inspections; recalls counted as distinct events, sterile-injectable recalls for C4; real-quote template for C1; large inspections export git-ignored |
| 4 | "is layer 2 complete? if yes, then build the entire remaining layer 3.." | Layer 2: fuzzy-match guard (distinctive name cores must agree; fixed Teva↔Sun and Accord↔Kindos/Inga/Ionis false links) and proposed top-20 manual-check decisions. Layer 3: C2 XGBoost + SHAP with Logistic Regression baseline, C3 Isolation Forest with audit examples, C4 warning-letter TF-IDF classifier + contract clause extraction, tests, README, notebook |
| 5 | "any errors? in terms of like, something not well defined, any flaws that might cause an avalanche effect?" | Audit of flaws (weights, unknown countries, invented inputs, shared factories, probation, letter coverage) |
| 6 | "identify these types (not just specific to the ones i mentioned) and make a list and help me understand" / "before that save the Glossary" | `docs/GLOSSARY.md` |
| 7 | "were there any assumptions made without asking me in the layer 2 and layer 3?" / "ok" | `docs/DECISIONS.md` |
| 8 | "we have to solve this, whatever assumptions we make that they have to backed by evidence and data" / "yes, approved. apply it one by one." | Evidence rule: DailyMed label evidence (`reference/sku_manufacturing_sites.csv`), FDA establishment registry factory numbers, factory-only scoring with warning notes, Medicaid information file, neutral "no data" values, recall bug fix, contracts removed from the score |
| 9 | "A with the warning note." / "but what ever we are doing now, it wont affect our whole mvp's pipeline in the negative way rigth? if yes, then continue with A." / "all as recommended" | Items 2–11 applied; recall re-decision; tests updated |

Layer 4, Layer 5 (cockpit and website), the stress test and the synthetic view continue in
[GENAI_PROMPT_LOG_layer4_5.md](GENAI_PROMPT_LOG_layer4_5.md).

## What is and is not AI-generated data

* **AI-generated, must be disclosed:** `layer3_engines/reference/contract_extraction_llm.json` — Claude read the 11
  synthetic contracts and returned clause JSON (zero-shot, cached per the plan's contingency cut order). An independent
  rule extractor agrees on all 4 clauses in 11/11 contracts.
* **AI-researched, evidence cited in the file:** `layer1_ingestion/reference/sku_manufacturing_sites.csv` (DailyMed label
  quotes, FDA factory numbers), `us_medicaid_sdud_2025_carboplatin.csv` (CMS data), the single Hormuz share in
  `scenario_corridor_assumptions.csv` (port volumes). Decisions taken by the team lead are recorded in `docs/DECISIONS.md`.
* **Earlier invented values, now removed:** per-maker capacities, per-country Hormuz shares and freight per vial.
* **Real data:** SCMS, openFDA, FDA inspections export, World Bank, FDA warning letters. Model outputs (C2, C3, C4)
  are computed from these by code.
