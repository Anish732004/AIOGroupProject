# PharmaShield GCC — Decisions Log

**Why this file exists.** While building Layers 1–3, Claude made choices without asking the team. Each one is listed here
with what was chosen, where it lives, and why it matters. **Nothing in the "Claude's choice" column is confirmed until
someone fills in "Your decision".** Terms are explained in [GLOSSARY.md](GLOSSARY.md).

How to fill it in: write **Keep**, **Change to …**, or **Ask team** in the last column, then tell Claude.

Importance: **High** = changes the final ranking or rests on an unchecked fact. **Med** = changes numbers a little.
**Low** = a technical setting.

---

## The evidence rule (approved by the team lead, 15 Nov 2026)

Every number that feeds a score must fall into one of three levels:

1. **Real data exists:** use it and cite the source.
2. **Only a stand-in exists:** use it, labelled "stand-in", with its source and limits.
3. **Nothing exists:** every supplier gets the same neutral value, shown as "no data", so it cannot affect the ranking.
   For a single supplier with a missing fact, "neutral" means the median of the rankable suppliers whose fact is known.

### Progress applying the rule

| Step | Item | Result | Status |
|---|---|---|---|
| 1 | Plant country | 10 of 11 rankable makers now come from the official drug label (quotes in `layer1_ingestion/reference/sku_manufacturing_sites.csv`). Fresenius's label does not say, so it is **Unknown** and gets neutral values (my earlier "India" was unsupported and is removed). No score changed except Fresenius's C4 (0.675 → 0.775), because with no known country all of its company plants are counted until step 2 is decided. Hospira's country is inferred from its registered factory's name (FDA registry address: Mulgrave, Victoria, Australia). | **Done** |
| 2 | Same-factory suppliers and factory-level FDA record | Evidence found: Teyro Labs makes the carboplatin sold by Teyro, Apotex **and Natco**; Gland Pharma (Visakhapatnam) makes Gland's **and BPI's**. FDA's establishment registry gives the exact factory number for 9 of 11 makers. **Decision (15 Nov 2026): "A with the warning note"**: only the factory that makes the carboplatin is scored; problems at the company's other plants are shown as a note and never scored. Applied: Eugia C4 0.938 → 0.488, Gland 0.112 → 0.012, BPI 0.188 → 0.088, Natco 0.310 → 0.212. Fresenius and Avyxa (factory not named anywhere) get the neutral inspection and letter terms: Fresenius 0.775 → 0.325, Avyxa 0.150 → 0.250. New matrix columns: `factory_name`, `factory_fei`, `source_plant_group`, `sister_plants_oai_5yr`, `sister_plant_warning`. Recalls are still counted per labeler company (reviewed under A8). | **Done** |
| 3 | Capacity | No public source. **Decision (15 Nov 2026): option A**: every maker gets the same non-limiting capacity (= monthly demand, 10,000). The plan's capacity rule stays in the order split but never binds; the per-factory 70% cap and probation caps still apply. My invented capacities (B1) are removed. The 2025 US Medicaid volume share is shown as information only (`us_medicaid_2025_volume_share_pct`, evidence file `reference/us_medicaid_sdud_2025_carboplatin.csv`). No score changed. | **Done** |
| 4 | Cost mark (C1) | Official CMS October 2026 Part B file: ONE price for all generic carboplatin (J9045 $3.101 / 50 mg = $27.91 per 450 mg vial; Teva, Accord, Eugia, Apotex, Pfizer/Hospira, Fresenius listed by name) and a separate price for Avyxa's Kyxata (J9278 $5.226 / mg = $2,351.70 per vial). Freight to the UAE: no evidence, so excluded (same for all). Result: the 10 generic makers all C1 = 0, Avyxa = 1. Also fixed a bug: with identical generic prices the old code would have given Avyxa 0. | **Done** |
| 5 | Hormuz / Gulf-air share | One evidence-based share, 0.85, for every origin and mode (UAE port volumes: Jebel Ali about 15.6m TEU in 2025 vs Khor Fakkan never above about 3m). My invented country differences are removed. C5 now differs only by the World Bank logistics score (real data): India 0.272, Australia 0.221, Netherlands / Switzerland 0.153. | **Done** |
| 6 | Shipping terms, mode, freight ratio, weight (C2 inputs) | No evidence for 2026 UAE shipments, so each maker's C2 is the AVERAGE prediction over real SCMS shipments from its plant country (all countries when fewer than 30), keeping only its real facts (country, own history). The "reasons" now say "not known for UAE shipments: averaged over real shipments from India". C2 now: India makers 0.103, Hospira 0.068, Teva 0.029, Avyxa 0.026, Fresenius neutral 0.103. Model quality unchanged (test ROC-AUC 0.797 vs baseline 0.786). | **Done** |
| 7 | Contract mark | The contracts are synthetic, so the contract term is 0 for every maker. The extraction is kept as a demo only (`contract_risk_demo_only`, `outputs/c4_contract_clauses.csv`). | **Done** |
| 8 | Recalls | (a) Bug fixed: eye drops were counted as injectables because their labels say "sterile" (Apotex's 2 recalls were eye drops). (b) An injectable recall counts only if its text names the company running the carboplatin factory. Result: Accord 4 counted (texts say "Manufactured by Intas"); Eugia 0 of 13, Hospira 0 of 14 and Teva 0 of 5 counted, because their texts name only the seller. Fresenius (factory unknown): neutral. **Re-decided (15 Nov 2026): same rule for every maker** - count the injectable Class I/II recalls issued by the company on the box (plan 3.2 "recall records by recalling firm"); a recall filed by a parent company counts only if the product text names this seller. Result: Hospira 13 (+1 Pfizer recall not naming Hospira, shown only), Eugia 13, Fresenius 7, Accord 5, Teva 5, others 0. Known bias: companies selling more products have more recalls. | **Done** |
| 9 | "Experienced" (probation) | Only the maker's own shipment history counts, not its parent's. Result: all 11 rankable makers are now "new" (probation), including Eugia. C3 is 0.0 for all of them (the plan's default for new makers). **Consequence for Layer 4:** with no established maker, the plan's rule caps every maker at 30% of demand, so the "70/20/10" example split cannot occur. | **Done** |
| 10 | Warning-letter severity weights | Kept (sterility 1.0, data integrity 1.0, process validation 0.6, quality unit 0.5). Labelled as a **team judgement**, not data. | **Done** |
| 11 | Warning-letter coverage | Only 50 hand-picked FDA letters were read. A score of 0 on letters means "none found in our sample", not "none exist". To be shown on the dashboard (Layer 5). | **Done (shown in Layer 5)** |
| 12 | Automatic (entropy) weights hijacked by near-empty marks | Applied in Layer 4: marks with no real variation across the rankable makers are left out of the automatic weighting. | **Layer 4** |


### Layer 4 and 5 decisions (team lead, 15 Nov 2026)

| ID | Question | Decision |
|---|---|---|
| L1 | Risk dial λ in the order-split cost (the plan gives no value) | Slider in the cockpit, default 1.0; every approval records the λ used |
| L2 | 5% minimum for a "new" (probation) supplier | Only if chosen: a maker gets 0, or between 5% and its cap (yes/no choice inside the maths) |
| L3 | Per-supplier caps for shared factories | Per factory: Teyro + Apotex + Natco share one cap; Gland + BPI share one cap |
| L4 | What the Streamlit link opens | The plan's 4-tab cockpit, with the Layer 1 data console as a fifth "Data pipeline" tab |
| V1 | Where approvals are stored on the Vercel website (it has no disk of its own) | In the viewer's browser: fingerprinted, chained, tamper-checked and downloadable; labelled "demo storage" |
| V2 | What happens to the Streamlit app | Kept as the local operator tool for re-running the pipeline; the Vercel site is the showcase |
| L6 | Ties between interchangeable suppliers (found while building the website) | The solver's tolerance let the chosen name flip between equal suppliers (e.g. Gland vs BPI) as the risk dial moved. Fixed: zero optimality gap, and ties are broken in a second solve by name, so equal suppliers always resolve the same way. No split changed by factory. |
| L5 | Entropy (data-driven) weights | The board's tier weights drive the ranking; the plan's "live entropy slider" defaults to 0% (max 50%). Reason: on this panel two standard entropy formulas gave opposite weights (cost 46% vs delivery + route 74%) and the ranking swung (Avyxa 2nd vs 11th). |

---

## A. Choices that change the results

| ID | Area | Claude's choice (not confirmed) | Where | Importance | Your decision |
|---|---|---|---|---|---|
| A1 | Layer 2: name matching | Wrote the "manual check on the top 20 matches" itself: rejected *Gland Chemicals* (said to be a separate API company) and *Fresenius Kabi Compounding* (a US compounding business). **Neither fact was verified.** | `layer1_ingestion/reference/entity_match_decisions.csv` | High | **Keep both rejections** (decided 15 Nov 2026). Checked: Fresenius Kabi Compounding is a US sterile-compounding facility (Canton, MA; warning letter May 2026), not a carboplatin plant. Gland Chemicals is a heparin/API maker; its relationship to Gland Pharma is **still unconfirmed**. |
| A2 | Layer 2: sister companies | Counted Fresenius's Austrian, German and Italian plants towards Fresenius USA, and Apotex's India plants towards Apotex. (Apotex's carboplatin is actually made by Teyro Labs.) | same file | High | **Only the company itself and the factory that makes the product** (decided 15 Nov 2026). Applied: Apotex's 2 research/chemical plants and Fresenius's European plants (Austria, Germany, Italy, Sweden) are now rejected. Result: Apotex's inspections 3 → 1 (only Teyro Labs, the real factory); no C4 score changed. **Follow-up decided:** the Canadian parent's (Apotex Inc.) sterility warning letter and plants do **not** count; Apotex's C4 fell 0.534 → 0.400. **Still open from this rule:** Apotex's 3 "injectable" recalls are really **eye drops** (my filter matched the word "sterile": bug, to be fixed under A8), and Fresenius's reliance on the Baddi, India plant (see B3). |
| A3 | Layer 2: how strict the matching is | Added a rule that the distinctive part of a name must agree (threshold 85). This removed false links such as Teva↔Sun. | `ingestion/scenario.py` (`CORE_MATCH_MIN`) | Med | |
| A4 | Layer 3 / C4: warning-letter severity | Sterility = 1.0, data integrity = 1.0, process validation = 0.6, quality unit = 0.5 | `layer3_engines/engines/c4_compliance.py` | High | |
| A5 | Layer 3 / C4: warning-letter sorting | There are no human-labelled letters, so the "answer key" is which FDA regulations each letter cites, plus a few phrase rules for raw-ingredient letters | `c4_compliance.py` (`CFR_RULES`) | High | |
| A6 | Layer 3 / C4: contract risk scale | Each clause scored 0, 0.5 or 1 (lead time = (days − 30) ÷ 60, capped at 0 to 1). Four clauses weighted equally. A supplier with no contract gets a neutral 0.5. | `c4_compliance.py` | High | |
| A7 | Layer 3 / C4: who read the contracts | Claude read the 11 contracts in a chat session and saved the result; there was no live AI call. A rule-based reader agrees on all 11. | `layer3_engines/reference/contract_extraction_llm.json` | High | |
| A8 | Layer 3 / C4: which recalls and inspections count | Only sterile-injectable recalls; only manufacturing-quality inspections; only at plants in the maker's own country (falls back to all plants, flagged). The plan says "Class I/II recalls" and "worst plant". | `ingestion/scenario.py` | High | |
| A9 | Layer 3 / C2: "no history" input | Removed the number-of-past-shipments input, because it made brand-new suppliers look safest. Unknown history now gets the overall average late rate. | `layer3_engines/engines/c2_delivery.py` | High | |
| A10 | Layer 3 / C2: scale of the score | Converted the model's inflated answer back to a true chance. C2 is about 0.24, not about 0.9. The plan does not say to do this. | `c2_delivery.py` (`prior_correct`) | Med | |
| A11 | Layer 3 / C2: tuning | Picked tree settings on the 2013 data by ROC-AUC, and picked the catch-late-shipments weight by F2 (recall counts double). Test years (2014–15) were never used for choosing. | `c2_delivery.py` | Med | |
| A12 | Layer 3 / C3: which lines are scored | Skipped 1,836 billing lines with no freight figure; only the ARV and HRDT product groups are modelled; a supplier with history but no scorable lines gets C3 = 0.0. | `layer3_engines/engines/c3_anomaly.py` | Med | |

## B. Data values Claude chose for Layer 1 (feed Layers 2 and 3)

These were applied after you said "fix it", but **you did not see the actual numbers first.**

| ID | Item | Claude's choice (not confirmed) | Where | Importance | Your decision |
|---|---|---|---|---|---|
| B1 | Monthly capacity per maker | Hospira 8,000 · Fresenius 7,000 · Teva 6,000 · Accord 5,000 · Eugia 5,000 · Gland 4,000 · Apotex 3,000 · Natco 2,500 · Teyro 1,500 · BPI 1,500 · Avyxa 1,000. **Made up** to reflect company size. | `reference/manufacturer_overrides.csv` | High | ~~Keep~~ **Replaced** by the evidence rule, item 3 (15 Nov 2026): no data, so non-limiting for all makers. |
| B2 | Share of cargo passing Hormuz, by origin country | India 0.545 · China 0.75 · USA 0.85 · EU about 0.89 · Japan/Korea 0.64 · Australia 0.53 · South Africa 0.50. **Geographic reasoning, not data.** | `reference/scenario_corridor_assumptions.csv` | High | |
| B3 | Plant country for BPI Labs and Fresenius Kabi | India. Thin evidence (a shortage-list note and a Singapore register entry). Verify on DailyMed. | `manufacturer_overrides.csv` | Med | |
| B4 | Plant country for Hospira and Avyxa | Australia and Switzerland. **Checked on DailyMed**; Hospira's is inferred from the registered factory's name. | `manufacturer_overrides.csv` | Low | |
| B5 | Cost mark for the branded Avyxa product | Capped at 1.0 and left out of the scaling (price about 84× the generics). | `ingestion/scenario.py` | Med | |
| B6 | Shipping contract terms, vial weight, freight per vial for every maker | DDP terms, 0.12 kg per vial, freight by origin. **Same assumption for all makers.** | `ingestion/config.py`, corridor file | High | |

## C. Technical settings

| ID | Setting | Value | Where |
|---|---|---|---|
| C1 | Smoothing strength for factory late-rates | 20 shipments | `c2_delivery.py` |
| C2 | Countries with fewer than N shipments are pooled as "Other" | 30 | `c2_delivery.py` |
| C3 | Minimum lines to model a product group | 50 | `c3_anomaly.py` |
| C4 | Number of trees in the unusual-lines model | 300 | `c3_anomaly.py` |
| C5 | Look-back window for warning letters | 5 years | `c4_compliance.py` |
| C6 | Cut-off for the right/wrong table | 0.5 | `c2_delivery.py` |
| C7 | A letter to a parent or sister company counts against the maker | yes | `c4_compliance.py` |
| C8 | A contract counts only for the company that signed it | yes | `c4_compliance.py` |

## D. Things Claude did that were not requested

| ID | What | Your decision |
|---|---|---|
| D1 | Marked Layer 2 and Layer 3 as "done" in the README | |
| D2 | `run_engines.py` overwrites `data/processed/suppliers_matrix.csv` in place. Re-running Layer 1 wipes C2–C4, so Layer 3 must be re-run after it. | |
| D3 | Added `xgboost` and `scikit-learn` to the root `requirements.txt` | |
| D4 | Added the Layer 3 notebook and the second prompt log (`GENAI_PROMPT_LOG_layer2_3.md`) | |
| D5 | Git-ignored the 25 MB FDA inspections file and the Layer 3 outputs folder | |

---

## Open problems (found in the audit of 15 Nov 2026)

| # | Problem | Plain meaning | Status |
|---|---|---|---|
| P1 | Entropy weights hijacked | The billing-oddities mark is 0 for 10 of 11 makers, so the data-driven weighting gives it about 33% (the board wants 5%) | Open |
| P2 | Unknown plant country was punished | Hospira and Avyxa got worse cost and route marks only because the country was unknown | **Fixed** (countries verified, see B4) |
| P3 | Cost mark is an "is it India?" switch | A $0.45 gap on $28 is stretched across the full 0–1 scale | Open |
| P4 | C2 depends on an invented shipping term | Changing the assumed terms moves C2 a lot and can swap suppliers' order | Open |
| P5 | Two labelers can be one factory | Apotex's product is made by Teyro; splitting orders between them is not real dual sourcing | Open |
| P6 | Only one maker counts as "experienced" | Eugia is the only established maker, and only through its parent company's history. It also has the worst compliance record. | Open |
| P7 | "No warning letter" may mean "not in our sample of 50" | Several makers score 0 because we did not look, not because they are clean | Open |
