# PharmaShield GCC

AI-driven pharmaceutical supplier selection, multi-source risk profiling and dual-source order allocation
for a UAE healthcare GPO. Group 3 · AI in Operations · SP Jain MAIB.

Demonstration SKU: **Carboplatin Injection 10 mg/mL** (Tier 1, life-critical oncology).

## Architecture (Master Implementation Plan §2)

| Layer | Folder | Owner | Status |
|---|---|---|---|
| 1. Multi-source data ingestion | [`layer1_ingestion/`](layer1_ingestion/) | Member 2A | ✅ done |
| 2. Unified manufacturer × SKU risk profile (rapidfuzz entity resolution → `suppliers_matrix.csv`) | built inside [`layer1_ingestion/`](layer1_ingestion/) (`ingestion/scenario.py`); manual check in `reference/entity_match_decisions.csv` | Member 2B | ✅ done — top-20 decisions proposed, team to confirm |
| 3. AI risk engines C2–C4 (XGBoost + SHAP, Isolation Forest, NLP); C1 and C5 come from Layer 1 | [`layer3_engines/`](layer3_engines/) | Members 4A, 4B | ✅ done |
| 4. Weights (AHP, modes, entropy), TOPSIS and PuLP order split | [`layer4_decision/`](layer4_decision/) | Member 3 | ✅ done |
| 4b. Synthetic view: fills gaps with values from approved industry ranges (professor's advice, decision S4) | [`synthetic/`](synthetic/) | Member 3 | ✅ done |
| 5. Showcase website (Vercel) | [`web/`](web/) | Member 5 | ✅ done |
| 5b. Operator cockpit (Streamlit, local): re-run the pipeline, approve and log | [`streamlit_app.py`](streamlit_app.py), [`app/`](app/) | Member 5 | ✅ done (30-second video still to record) |

## The showcase website (Vercel)

A 9-page website for any reader: eight key findings in plain words, the problem, the ranked suppliers with their reasons and evidence, a side-by-side compare view, the recommended
order split with the one-click situations and a natural-disaster stress test, shortage alerts with a live FDA check, the document readers, model quality,
the evidence behind every input, and a searchable glossary. A side-bar switch shows **Real data only** or **With synthetic
data** (every invented value marked). It is static (no build step) and shows results the Python pipeline computed for
all 234 settings a reader can choose, in both views. Deploy: import the repo in Vercel; `vercel.json` does the
rest. Details, refresh steps and tests: [web/README.md](web/README.md).

## Operator cockpit (Streamlit, local)

The Streamlit app is the operator's tool for re-running the data pipeline and refreshing the numbers; the Vercel site
is what readers see. It can also be deployed on Streamlit Community Cloud with main file `streamlit_app.py`.
Optional secrets (App settings → Secrets):

```toml
OPENFDA_API_KEY = "..."      # higher openFDA quota
FDA_DD_USER = "you@example.com"  # FDA Data Dashboard inspections API
FDA_DD_KEY = "..."
```

**Locally:** `pip install -r requirements.txt` then `streamlit run streamlit_app.py`.

**The cockpit** (plan §5.2 step 9) opens with a live shortage banner and five tabs:

1. **Supplier scorecard & SHAP**: ranking, the five marks, "no data" flags, and per supplier the top-3 delivery-risk
   drivers, what the compliance mark is made of, and notes about the company's other plants (never scored).
2. **Live shortage alerts**: openFDA carboplatin shortages (snapshot plus a live check button).
3. **Crisis simulator & order split**: one-click Normal / Crisis / Cost Focus, the entropy slider, the natural-disaster
   stress test, the split by factory with the warm-backup share, and **Approve & log** to a tamper-evident audit trail (each record carries the previous record's fingerprint).
4. **NLP: letters & contracts**: warning-letter classifier results, and the contract clause reader (demo only; the
   contracts are synthetic and not scored).
5. **Data pipeline**: the original Layer 1 console. Its run button now runs Layer 1, then Layer 3.

The sidebar holds the data switch (real or synthetic view), the mode button, the sliders and the governance notes (human sign-off, explainability, evidence
rule, fairness, UAE PDPL, GenAI disclosure). The audit log is written to `data/audit/audit_log.jsonl`. On Streamlit
Community Cloud that disk is temporary, so download the log after each session.

Notebooks (all run top to bottom, 16 Nov 2026): `notebooks/01_layer1_data_ingestion.ipynb` (replays the cached data of 15 Nov 2026 by
default; set `OFFLINE = False` for a live pull, then re-run notebook 02), `02_layer3_risk_engines.ipynb`,
`03_layer4_decision.ipynb` (ends with the numbers for the slides). GenAI prompt logs: `docs/GENAI_PROMPT_LOG_layer1.md`,
`docs/GENAI_PROMPT_LOG_layer2_3.md`, `docs/GENAI_PROMPT_LOG_layer4_5.md`, combined in `docs/GenAI_Prompt_Log.pdf`.
Every plan requirement and where it is met: [docs/PLAN_TRACEABILITY.md](docs/PLAN_TRACEABILITY.md). Q&A answers that match
the results: [docs/QA_DEFENSE.md](docs/QA_DEFENSE.md).
Line-by-line plan check: `layer1_ingestion/PLAN_COMPLIANCE.md`.

## Quick start (Layer 1, command line)

```bash
cd layer1_ingestion
pip install -r requirements.txt
python run_ingestion.py          # live pull: openFDA + World Bank + SCMS
python run_ingestion.py --offline   # replay cached snapshots, no network
python -m pytest -q
cd ../layer3_engines
python run_engines.py               # Layer 3: fills C2, C3, C4 and shap_top3_reasons in the matrix
python -m pytest -q
cd ../layer4_decision
python run_decision.py              # Layer 4: ranking + order split for Normal / Crisis / Cost Focus
python -m pytest -q
cd ..
python synthetic/build_synthetic.py # synthetic view: data/processed/suppliers_matrix_synthetic.csv (real table untouched)
(cd layer4_decision && python run_decision.py --synthetic)   # Layer 4 on the synthetic view -> outputs/synthetic/
python tools/export_web_snapshot.py # website data: Layer 4 for all 234 reader settings, both views -> web/data/snapshot.json
node tools/test_web.mjs             # checks on the snapshot and the website's browser-side logic
python tools/check_consistency.py   # plan vs pipeline vs website (69 checks)
python tools/build_prompt_log_pdf.py # GenAI Prompt Log PDF for Blackboard -> docs/GenAI_Prompt_Log.pdf
```

**Evidence rule.** In the real view, every number that feeds a score is backed by a cited source, or marked "no data" and
given the same neutral value for every supplier. The synthetic view fills those gaps from approved ranges, each with its
source ([synthetic/README.md](synthetic/README.md)). All team decisions and their effects: [docs/DECISIONS.md](docs/DECISIONS.md).
Plain-English terms: [docs/GLOSSARY.md](docs/GLOSSARY.md).

FDA inspections: FDA retired its direct download link, so save the dashboard export
(*Entire Inspections Dataset*) into `layer1_ingestion/data/manual/fda_inspections/` before running Layer 1.

The locked-schema hand-off is `data/processed/suppliers_matrix.csv` at the repo root (plan §5.1); other tables are in `layer1_ingestion/data/interim/`. See the
[Layer 1 README](layer1_ingestion/README.md) and the [data source catalogue](layer1_ingestion/DATA_SOURCES.md).

## Conventions

* A **data snapshot** (15 Nov 2026) is committed: `data/processed`, `layer1_ingestion/data/{interim,quality,quarantine,manifest.json}`, `layer3_engines/outputs`, `layer4_decision/outputs`, `synthetic/outputs`, `web/data/snapshot.json`. The website and the cockpit use it directly. Re-running the pipeline overwrites it; commit again to share new numbers. Not committed: raw API responses (`layer1_ingestion/data/raw`), the 25 MB FDA inspections export and audit logs (`data/audit`).
* Every layer reads the previous layer's `data/interim/` tables; don't edit them by hand.
* GenAI disclosure (plan §6.1): AI-assisted code is marked and logged in the GenAI Prompt Log.
