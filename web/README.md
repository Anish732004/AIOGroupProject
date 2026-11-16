# PharmaShield GCC — Showcase website (Vercel)

The public face of the project: a 9-page static website that presents the pipeline's results so that anyone can
understand them without running Python.

| Page | What the reader gets |
|---|---|
| Overview | The recommended order at a glance, **8 key findings in plain words (computed from the data, each linked to its evidence)**, the problem, how it works, the five marks, why the numbers can be trusted |
| Suppliers | The ranked list for the chosen situation; click a supplier for its delivery-risk reasons, its compliance record, and the label evidence of where it is made |
| Compare | Any two suppliers side by side; "✓ better" marks the stronger side; flags suppliers made in the same factory |
| Order split | The split by factory, a natural-disaster stress test, the weights in use, scores in every situation, and **Approve & log** |
| Alerts | FDA shortage records, plus a live check against the FDA's public database |
| Documents | The warning-letter reader's results and the contract reader (demo; contracts are synthetic) |
| Models | How good the predictions are, tested on data the models never saw |
| Evidence & trust | Every input with its evidence level and source, known limits, governance |
| Glossary | All 222 plain-English terms, searchable |

## How it works

The site is plain HTML, CSS and JavaScript: no framework, no build step, no packages. It cannot run Python, so
`tools/export_web_snapshot.py` runs the **real** Layer 4 engine for every setting the reader can choose (3 situations ×
13 risk-dial steps × 6 data-weight steps = 234 scenarios), plus the natural-disaster stress test for each of them (10 outages, 2,340 more results), and stores
the results in `web/data/snapshot.json` (about 560 KB). The site only looks results up, so every number matches the Python pipeline exactly.

Team decisions for the website (docs/DECISIONS.md, V1–V2):

* **Approvals are stored in the viewer's browser** (localStorage). Each record carries the SHA-256 fingerprint of the
  previous one, so an edited or deleted record is detected. The log can be downloaded. A production system would
  write to the buyer's own database.
* **Streamlit stays** as the local operator tool for re-running the data pipeline; Vercel is the showcase.

Privacy and security: no personal data in the snapshot (checked by the tests); approver initials only; a strict
Content-Security-Policy in `vercel.json` (scripts only from the site itself, network calls only to the site and
`api.fda.gov`, no framing).

Links can open a setting directly, for example `#/split?outage=COUNTRY_INDIA` (stress test: every factory in India
offline) or `#/compare?a=APOTEX&b=TEYRO LABS`.

## Deploy on Vercel

1. Push the repository to GitHub.
2. In Vercel: **Add New → Project →** import the repository. Leave the framework as **Other**; `vercel.json` already sets
   the output folder to `web` and turns off install and build steps.
3. Deploy. `.vercelignore` makes sure only `web/` and `vercel.json` are uploaded (the pipeline and its data stay out).

## Refresh the numbers

After re-running the pipeline (Layer 1 → Layer 3), regenerate the snapshot and redeploy:

```bash
python tools/export_web_snapshot.py     # runs Layer 4 for all 234 scenarios + stress tests -> web/data/snapshot.json
node tools/test_web.mjs                 # 6 checks on the snapshot and the browser-side logic
python tools/check_consistency.py       # 51 checks: plan vs pipeline vs website
```

## Test locally

```bash
node tools/serve_web.mjs                # http://127.0.0.1:8766/ with the same security headers as Vercel
node tools/e2e_web.mjs                  # 58 checks in headless Chrome (CHROME=... to point at another browser)
```

If you change the small script inside `index.html`, update its `sha256-…` value in `vercel.json`;
`tools/test_web.mjs` fails and prints the new value if they disagree.

Handy links for a presentation: add the situation to the address, e.g.
`/#/split?mode=Crisis`, `/#/split?mode=Cost Focus&dial=2`, `/#/suppliers?supplier=ACCORD HEALTHCARE`,
`/#/compare?a=APOTEX&b=TEYRO LABS`, `?theme=dark`. The site is tested in Chrome.
