"""
PharmaShield GCC - Category Manager Cockpit (Layer 5, plan 5.2 step 9; Q6, Q7).

Tabs (plan): 1 Supplier Scorecard & SHAP · 2 Live openFDA Shortage Alerts · 3 One-Click Crisis Simulator & Order Split
(with "Approve & Log to Audit Trail") · 4 NLP Contract & Warning-Letter Analyser · 5 Data pipeline (team decision L4).

Deploy on Streamlit Community Cloud with main file `streamlit_app.py`. Optional secrets: OPENFDA_API_KEY,
FDA_DD_USER, FDA_DD_KEY. Every number shown follows the evidence rule in docs/DECISIONS.md.
"""
from __future__ import annotations

import json
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
for sub in ("layer1_ingestion", "layer3_engines", "layer4_decision"):
    sys.path.insert(0, str(ROOT / sub))
sys.path.insert(0, str(ROOT))

st.set_page_config(page_title="PharmaShield GCC · Cockpit", page_icon="💊", layout="wide")

from app import audit  # noqa: E402
from app import pipeline_console as console  # noqa: E402  (loads secrets into env, Layer 1 + 3 runners)
from decision import engine as L4  # noqa: E402
from decision.weights import CRITERIA, MODES  # noqa: E402
from engines import c4_compliance  # noqa: E402

MATRIX_REAL = ROOT / "data" / "processed" / "suppliers_matrix.csv"
MATRIX_SYNTHETIC = ROOT / "data" / "processed" / "suppliers_matrix_synthetic.csv"   # synthetic view (decision S4)
SYN_INPUTS = ROOT / "synthetic" / "outputs" / "synthetic_inputs.csv"
INTERIM = ROOT / "layer1_ingestion" / "data" / "interim"
L1_REF = ROOT / "layer1_ingestion" / "reference"
L3_OUT = ROOT / "layer3_engines" / "outputs"
MANIFEST = ROOT / "layer1_ingestion" / "data" / "manifest.json"
AUDIT_LOG = ROOT / "data" / "audit" / "audit_log.jsonl"
LABEL = {"C1_landed_cost": "C1 Cost", "C2_delivery_risk": "C2 Late delivery", "C3_price_integrity": "C3 Billing",
         "C4_compliance_risk": "C4 Compliance", "C5_route_exposure": "C5 Route (Hormuz)"}


# --------------------------------------------------------------------------- #
# data
# --------------------------------------------------------------------------- #
def usd(v: float) -> str:
    """Whole dollars, halves rounded up - the same rounding as the website and the docs."""
    return f"${int(Decimal(str(v)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)):,}"


def mtime(p: Path) -> float:
    return p.stat().st_mtime if p.exists() else 0.0


@st.cache_data(show_spinner=False)
def read_csv(path: str, _mtime: float) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def csv(p: Path) -> pd.DataFrame:
    return read_csv(str(p), mtime(p)) if p.exists() else pd.DataFrame()


def jload(p: Path) -> dict:
    return json.loads(p.read_text()) if p.exists() else {}


@st.cache_data(show_spinner="Ranking suppliers and solving the order split…")
def decide(matrix: str, mode: str, lam: float, ent: float, offline: tuple, _mtime: float) -> dict:
    m, tiers, sku = L4.load_inputs(Path(matrix))
    return L4.run(m, tiers, sku, mode, lam, ent, set(offline) or None)


def matrix_ready() -> tuple[bool, str]:
    if not MATRIX.exists():
        return False, "No supplier matrix yet."
    m = csv(MATRIX)
    empty = [c for c in CRITERIA if c not in m or m[c].isna().any()]
    if empty:
        return False, f"Scores {', '.join(LABEL.get(c, c) for c in empty)} are empty (Layer 3 has not run)."
    return True, ""


# --------------------------------------------------------------------------- #
# sidebar: one-click modes + governance
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("Decision controls")
    synthetic = False
    if MATRIX_SYNTHETIC.exists():
        synthetic = st.radio("Data shown", ["Real data only", "With synthetic data"], index=0,
                             help="Synthetic view (decision S4): inputs with no public evidence are filled from approved "
                                  "industry ranges (synthetic/reference/synthetic_ranges.csv). The real view never uses "
                                  "them.") == "With synthetic data"
    MATRIX = MATRIX_SYNTHETIC if synthetic else MATRIX_REAL
    mode = st.radio("Mode (one click, plan §4.2)", MODES, index=0,
                    help="Crisis: weight moves from cost to route exposure, and Hormuz exposure x1.5 (capped at 1). "
                         "Cost Focus: weight moves from route exposure to cost.")
    lam = st.slider("Risk dial λ (team decision L1)", 0.0, 3.0, 1.0, 0.1,
                    help="How strongly the order split avoids lower-ranked suppliers compared with saving money. "
                         "λ = 1: a supplier's risk can add up to 100% of the average vial cost as a penalty.")
    ent = st.slider("Entropy (data-driven) weight share", 0, 50, 0, 5, format="%d%%",
                    help="Team decision L5: the board's tier weights drive the ranking (0%). The plan's 50/50 blend "
                         "proved unstable on this panel; slide to see its effect.") / 100
    st.divider()
    st.subheader("Governance")
    st.markdown(
        "- **Human-in-the-loop:** nothing is ordered until a category manager approves in tab 3.\n"
        "- **Explainable:** every delivery score shows its top 3 drivers (SHAP).\n"
        "- **Evidence rule:** every input is backed by a cited source, or marked *no data* and given a neutral "
        "value (`docs/DECISIONS.md`). The optional synthetic view fills gaps from approved ranges, each marked.\n"
        "- **Fairness:** suppliers are scored on their own factory's record and their own history, never on "
        "country name alone or a parent company's record.\n"
        "- **UAE PDPL:** no personal data in the scores; the audit log stores approver initials only.\n"
        "- **GenAI disclosure:** code and the contract extraction were produced with Claude and reviewed by the "
        "team (prompt logs in `docs/`).")
    man = jload(MANIFEST)
    if man:
        st.caption(f"Data snapshot: as of {man.get('as_of')} · run {str(man.get('run_at_utc', ''))[:16]} UTC")

st.title("PharmaShield GCC · Category Manager Cockpit")
st.caption("Carboplatin Injection 10 mg/mL · Tier 1 (life-critical oncology) · UAE GPO · "
           "AI recommends, a human approves.")
if synthetic:
    st.info("◆ **Synthetic view.** Freight, delivery terms, past deliveries to this buyer, invoices, contracts, factory "
            "capacity and route share are invented within approved industry ranges (ranges R1-R11 with sources in "
            "`synthetic/reference/synthetic_ranges.csv`). FDA records, prices and World Bank scores stay real. "
            "Switch to *Real data only* in the sidebar for the evidence-only result.")

ready, why = matrix_ready()
r = decide(str(MATRIX), mode, lam, ent, (), mtime(MATRIX)) if ready else None
syn_in = csv(SYN_INPUTS).set_index("manufacturer_id") if synthetic and SYN_INPUTS.exists() else pd.DataFrame()
m = csv(MATRIX).set_index("manufacturer_id") if ready else pd.DataFrame()

# shortage banner (plan Q7)
sh = csv(INTERIM / "fda_shortages_sku.csv")
if len(sh) and "is_active" in sh:
    act = sh[sh["is_active"].astype(bool)]
    if len(act):
        st.error(f"🚨 openFDA shortage alert: {len(act)} active carboplatin shortage record(s) from "
                 f"{act['company_name'].nunique()} compan(ies). Details in tab 2.")

if r is not None:
    d = r["diagnostics"]
    al = r["allocation"]
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Mode", mode)
    k2.metric("Factories in the split", d["factories_used"],
              help="Plan 4.2: Tier 1 needs at least 2 suppliers. " + ("Met." if d["meets_two_supplier_minimum"] else "NOT met."))
    k3.metric("Warm-backup share", f"{d['warm_backup_share_pct']:.0f}%",
              help="Plan Q7: the part of the order placed with factories other than the main one. That supply is "
                   "already approved and shipping, so it can be scaled up at once if the main factory fails.")
    k4.metric("Largest single factory", f"{d['largest_factory_share_pct']:.0f}%")
    k5.metric("Emergency spot buy", f"{d['spot_buy_vials']:,.0f} vials")
    ctry = al.loc[al["selected"], "factory_group"].map(m["manufacturing_country"].groupby(m["source_plant_group"]).first())
    k6.metric("Countries in the split", ctry[ctry != "Unknown"].nunique(),
              help="Plus one factory whose country is not stated." if (ctry == "Unknown").any() else None)
else:
    st.warning(f"{why} Open the **Data pipeline** tab and run the pipeline (Layer 1, then Layer 3) to fill the "
               "cockpit.")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["1 · Supplier scorecard & SHAP", "2 · Live shortage alerts",
                                        "3 · Crisis simulator & order split", "4 · NLP: letters & contracts",
                                        "5 · Data pipeline"])

# --------------------------------------------------------------------------- #
# 1 Supplier scorecard
# --------------------------------------------------------------------------- #
with tab1:
    if r is None:
        st.info("No scores yet.")
    else:
        st.subheader(f"Ranking · {mode} mode")
        st.caption("All marks run 0 (best) to 1 (worst). S = TOPSIS closeness to the ideal supplier (higher is better). "
                   "Makers that share a factory are listed with the same factory.")
        rk = r["ranking"]
        flags = []
        for k in rk.index:
            f = []
            if bool(m.loc[k, "is_probation"]):
                f.append("🆕 probation")
            if bool(m.loc[k].get("country_inputs_neutral", False)):
                f.append("⚪ plant country: no data")
            if bool(m.loc[k].get("fda_inspection_record_neutral", False)):
                f.append("⚪ factory: no data")
            if bool(m.loc[k, "active_fda_shortage"]):
                f.append("🚨 in shortage")
            if synthetic and k in syn_in.index and bool(syn_in.loc[k, "established"]):
                f.append("◆ established (synthetic history)")
            flags.append(" · ".join(f))
        table = pd.DataFrame({
            "Rank": rk["rank"], "Supplier (name on box)": rk["labeler_name_fda"],
            "Factory": m.loc[rk.index, "factory_name"].fillna("not stated on label"),
            "Country": rk["manufacturing_country"], "S": rk["S"],
            **{LABEL[c]: rk[f"value_{c}"] for c in CRITERIA}, "Flags": flags})
        st.dataframe(table, hide_index=True, width="stretch", column_config={
            "S": st.column_config.ProgressColumn("S (higher = better)", min_value=0, max_value=1, format="%.3f"),
            **{LABEL[c]: st.column_config.NumberColumn(format="%.3f") for c in CRITERIA}})

        st.subheader("Why? Per-supplier explanation")
        pick = st.selectbox("Supplier", rk.index.tolist(),
                            format_func=lambda k: f"#{int(rk.loc[k, 'rank'])} {rk.loc[k, 'labeler_name_fda']}")
        row = m.loc[pick]
        a, b = st.columns(2)
        with a:
            st.markdown("**Late-delivery risk (C2): top 3 drivers (SHAP)**")
            reasons = pd.DataFrame(json.loads(row["shap_top3_reasons"]))
            if len(reasons):
                reasons["strength"] = reasons["shap_log_odds"].abs()
                st.dataframe(reasons[["feature", "value", "effect", "strength"]], hide_index=True, width="stretch",
                             column_config={"strength": st.column_config.ProgressColumn(
                                 "strength", min_value=0, max_value=float(max(1.0, reasons["strength"].max())),
                                 format="%.2f")})
            st.caption(f"C2 = {row['C2_delivery_risk']:.3f} · basis: {row.get('c2_basis', '')} · "
                       f"{row.get('shipment_profile', '')}")
        with b:
            st.markdown("**Compliance (C4): what it is made of**")
            st.markdown(
                f"- Factory: **{row.get('factory_name', 'not stated')}** (FDA no. {row.get('factory_fei', '—')})\n"
                f"- Inspections at this factory, 5 yrs: **{int(row['oai_count_5yr'])} serious (OAI)**, "
                f"{int(row['vai_count_5yr'])} minor (VAI)\n"
                f"- Injectable recalls by this seller, 5 yrs: **{int(row['recalls_class_i_ii_inj_5yr'])}**\n"
                f"- Worst warning letter (in our 50-letter sample): {row.get('worst_letter') or 'none found'}\n"
                f"- Country logistics score (World Bank LPI): {row['lpi_score']:.1f} of 5; political stability (WGI, "
                f"shown only): {row.get('wgi_political_stability', float('nan')):.2f}\n"
                + (f"- Contract risk {row['contract_risk']:.2f}, counts 20% ◆ synthetic contract (R6)"
                   if synthetic else "- Contract: not scored (synthetic contracts)"))
            note = row.get("sister_plant_warning")
            if isinstance(note, str) and note:
                st.warning(f"Note (not scored): {note}")
            share = row.get("us_medicaid_2025_volume_share_pct")
            if pd.notna(share):
                st.caption(("Real data, used to scale the synthetic capacity and pick the established suppliers: "
                            if synthetic else "Information only: ") + f"{share:.1f}% of 2025 US Medicaid carboplatin volume.")
            if synthetic and pick in syn_in.index:
                y = syn_in.loc[pick]
                st.markdown("**◆ Synthetic inputs for this supplier** (ranges on the website's Evidence & trust page)")
                st.markdown(
                    f"- Shipping: {y['shipment_mode']}, terms {y['vendor_inco_term']}, {int(y['shipment_vials']):,} vials "
                    f"({y['shipment_weight_kg']:.0f} kg) per shipment (R1-R4)\n"
                    f"- Air freight: ${y['freight_rate_usd_per_kg']:.2f}/kg = ${y['freight_usd_per_vial']:.2f} per vial (R5)\n"
                    f"- Hormuz / Gulf-airspace share: {y['hormuz_air_share']:.2f} (R9) · factory capacity "
                    f"{int(y['factory_capacity_vials']):,} vials/month (R8)\n"
                    f"- Past deliveries to this buyer: {int(y['past_deliveries'])}"
                    + (f", {100 * y['on_time_rate']:.0f}% on time (R10, R11)" if y["past_deliveries"] else " (new supplier)"))
        gaps = rk.loc[pick, [f"gap_share_{c[:2]}" for c in CRITERIA]]
        gaps.index = [LABEL[c] for c in CRITERIA]
        st.markdown("**Where this supplier loses ground against the ideal supplier**")
        st.dataframe(gaps.rename("share of the gap").to_frame().T, hide_index=True, width="stretch",
                     column_config={k: st.column_config.ProgressColumn(k, min_value=0, max_value=1, format="%.2f")
                                    for k in gaps.index})

# --------------------------------------------------------------------------- #
# 2 Shortage alerts
# --------------------------------------------------------------------------- #
with tab2:
    st.subheader("openFDA drug shortages · carboplatin")
    st.caption(f"Snapshot from the last pipeline run ({man.get('as_of', 'n/a') if man else 'n/a'}).")
    if len(sh):
        cols = [c for c in ["company_name", "status", "availability", "presentation", "shortage_reason",
                            "update_date"] if c in sh]
        st.dataframe(sh[cols], hide_index=True, width="stretch")
    onc = csv(INTERIM / "fda_shortages_oncology_current.csv")
    if len(onc):
        gcol = "generic_name" if "generic_name" in onc else onc.columns[0]
        st.markdown(f"**All current oncology shortages:** {len(onc)} record(s) across {onc[gcol].nunique()} "
                    "molecule(s)")
        st.dataframe(onc[gcol].value_counts().rename("records").to_frame(), width="stretch")
    if st.button("🔄 Check openFDA now (live)"):
        try:
            from ingestion import openfda
            from ingestion.common import HttpClient
            from ingestion.config import SETTINGS
            live, _ = openfda.shortages(HttpClient(SETTINGS.paths.raw, offline=False))
            act = live[live["is_active"].astype(bool)] if len(live) and "is_active" in live else live
            st.success(f"Live: {len(act)} active carboplatin shortage record(s) right now "
                       f"(snapshot had {int(sh['is_active'].astype(bool).sum()) if len(sh) else 0}).")
            st.dataframe(live, hide_index=True, width="stretch")
        except Exception as e:  # never break the cockpit on a network problem
            st.error(f"Live check failed ({type(e).__name__}: {e}). The snapshot above is still valid.")

# --------------------------------------------------------------------------- #
# 3 Crisis simulator + order split + approval
# --------------------------------------------------------------------------- #
with tab3:
    if r is None:
        st.info("No scores yet.")
    else:
        st.subheader(f"Recommended order split · {r['demand']:,} vials / month · {mode} mode · λ = {lam}")
        mfull = csv(MATRIX)
        outs = L4.stress_outages(mfull)
        me = m[m["eligible_for_ranking"].astype(bool)]                     # rankable makers only (8 factories)
        fac_country = me["manufacturing_country"].groupby(me["source_plant_group"]).first()
        label = {o["key"]: (f"Every factory in {o['country']} ({len(o['groups'])} of {len(fac_country)})" if o["kind"] == "country"
                            else f"{o['groups'][0]} ({fac_country.get(o['groups'][0], '?')})") for o in outs if o["kind"] != "country_worst"}
        outage = st.selectbox("Stress test: a natural disaster takes factories offline (plan Q7)", ["none"] + list(label),
                              format_func=lambda k: "Nothing (no disaster)" if k == "none" else label[k])
        base = r
        if outage != "none":
            grp = next(o["groups"] for o in outs if o["key"] == outage)
            r = decide(str(MATRIX), mode, lam, ent, tuple(grp), mtime(MATRIX))
            dd, bd = r["diagnostics"], base["diagnostics"]
            msg = (f"**{label[outage]} offline.** Scores and ranking do not change (a disaster says nothing about quality); "
                   f"only the split re-solves. Emergency purchase: **{dd['spot_buy_vials']:,.0f} vials**. Monthly cost "
                   f"{usd(bd['monthly_spend_usd'])} → **{usd(dd['monthly_spend_usd'])}** at official US prices"
                   f"{' plus synthetic freight' if synthetic else ''}. Warm-backup share {dd['warm_backup_share_pct']:.0f}%.")
            (st.error if dd["spot_buy_vials"] > 0.5 else st.warning)(msg)
            worst = next((o for o in outs if o["kind"] == "country_worst"), None)
            if outage == "COUNTRY_INDIA" and worst:
                wd = decide(str(MATRIX), mode, lam, ent, tuple(worst["groups"]), mtime(MATRIX))["diagnostics"]
                st.caption(f"Caveat: Fresenius's factory country is not stated. If it is also in India: "
                           f"{wd['spot_buy_vials']:,.0f} emergency vials and {usd(wd['monthly_spend_usd'])} a month.")
        al = r["allocation"]
        fac = (al.groupby("factory_group")
               .agg(vials=("vials", "sum"), suppliers=("manufacturer_id", lambda s: ", ".join(sorted(s))),
                    best_S=("S", "max"), cap_pct=("factory_cap_pct", "first"))
               .sort_values("vials", ascending=False).reset_index())
        fac["share_pct"] = 100 * fac["vials"] / r["demand"]
        fac["country"] = fac["factory_group"].map(m["manufacturing_country"].groupby(m["source_plant_group"]).first())
        st.dataframe(fac[fac["vials"] > 0.5][["factory_group", "country", "suppliers", "best_S", "vials",
                                               "share_pct", "cap_pct"]],
                     hide_index=True, width="stretch", column_config={
                         "factory_group": "Factory", "suppliers": "Name(s) on the box",
                         "best_S": st.column_config.NumberColumn("S", format="%.3f"),
                         "vials": st.column_config.NumberColumn("Vials", format="%,.0f"),
                         "share_pct": st.column_config.ProgressColumn("Share", min_value=0, max_value=100,
                                                                      format="%.0f%%"),
                         "cap_pct": st.column_config.NumberColumn("Cap", format="%.0f%%")})
        dg = r["diagnostics"]
        st.caption("Caps apply per factory (team decision L3). " + (
            "All rankable makers are on probation (no own delivery history with the GPO), so the plan caps each factory "
            f"at {100 * dg['probation_cap_used']:.0f}% and a chosen trial supplier gets at least 5%. "
            if dg["established_factories"] == 0 else
            f"{dg['established_factories']} factories have an established supplier (◆ synthetic delivery records), so "
            f"each may take up to {100 * dg['tier_cap']:.0f}%, a new supplier up to {100 * dg['probation_cap_used']:.0f}% "
            "(at least 5% if chosen), and each factory is limited by its ◆ synthetic monthly capacity. ")
            + "Where one factory sells under several names, the share goes to the factory; the name is interchangeable.")
        sel = al[al["selected"]][["manufacturer_id", "factory_group", "S", "vials", "share_pct", "role"]]
        with st.expander("Order lines by supplier name"):
            st.dataframe(sel, hide_index=True, width="stretch")

        st.subheader("Normal vs Crisis vs Cost Focus")
        comp = pd.DataFrame({md: decide(str(MATRIX), md, lam, ent, (), mtime(MATRIX))["ranking"]["S"] for md in MODES})
        comp.insert(0, "Supplier", r["ranking"].reindex(comp.index)["labeler_name_fda"])
        st.dataframe(comp.sort_values(mode, ascending=False), width="stretch",
                     column_config={md: st.column_config.NumberColumn(md, format="%.3f") for md in MODES})
        w = r["weights"].rename(index=LABEL)
        c1, c2 = st.columns([3, 2])
        c1.markdown("**Weights in this mode**")
        c1.dataframe(w, width="stretch")
        c2.markdown("**AHP consistency**")
        c2.write(f"CR = {r['ahp_consistency']['CR']} (must be < 0.10). "
                 f"{r['ahp_consistency']['note']}.")

        st.subheader("✅ Approve & log to audit trail")
        st.caption("No purchase order is transmitted without this sign-off (plan §6.1, UAE AI Charter).")
        with st.form("approve", clear_on_submit=True):
            who = st.text_input("Approver initials or staff ID (no full names: UAE PDPL data minimisation)",
                                max_chars=12)
            decision = st.radio("Decision", ["Approve as recommended", "Approve with override", "Reject"],
                                horizontal=True)
            note = st.text_area("Reason (required for an override or rejection)", max_chars=500)
            sent = st.form_submit_button("Sign and log", type="primary")
        if sent:
            if not who.strip():
                st.error("Enter your initials or staff ID.")
            elif decision != "Approve as recommended" and not note.strip():
                st.error("Give a reason for an override or a rejection.")
            else:
                rec = audit.append(AUDIT_LOG, {
                    "approver": who.strip(), "decision": decision, "reason": note.strip(),
                    "data_view": "synthetic" if synthetic else "real", "stress_test": outage, "mode": mode,
                    "lambda": lam, "entropy_share": ent, "demand_vials": r["demand"],
                    "weights_used": r["weights"]["Used for ranking"].round(4).to_dict(),
                    "split_vials": {k: v for k, v in sel.set_index("manufacturer_id")["vials"].items()},
                    "spot_buy_vials": r["diagnostics"]["spot_buy_vials"],
                    "warm_backup_share_pct": r["diagnostics"]["warm_backup_share_pct"],
                    "matrix_sha256": audit.file_sha256(MATRIX)})
                st.success(f"Logged as record #{rec['seq']} · fingerprint {rec['record_hash'][:16]}…")
        log = audit.read(AUDIT_LOG)
        if log:
            ok, msg = audit.verify(AUDIT_LOG)
            (st.success if ok else st.error)(f"Audit trail check: {msg}")
            lg = pd.DataFrame(log)
            st.dataframe(lg[[c for c in ["seq", "timestamp_utc", "approver", "decision", "data_view", "stress_test", "mode",
                                         "lambda", "reason", "record_hash"] if c in lg]], hide_index=True, width="stretch")
            st.download_button("Download audit log (JSONL)", AUDIT_LOG.read_bytes(), "audit_log.jsonl",
                               "application/json")

# --------------------------------------------------------------------------- #
# 4 NLP analyser
# --------------------------------------------------------------------------- #
with tab4:
    st.subheader("FDA warning letters · violation classifier (TF-IDF + logistic regression)")
    st.caption("Coverage: 50 hand-picked FDA warning letters. A supplier with no letter here means "
               "'none found in our sample', not 'none exist'.")
    met = jload(L3_OUT / "c4_metrics.json")
    if met:
        st.dataframe(pd.DataFrame(met["warning_letter_classifier"]).T, width="stretch")
        st.caption("Severity weights (team judgement, not data): " +
                   ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in met["severity_weights"].items()))
    letters = csv(L3_OUT / "c4_warning_letters_classified.csv")
    if len(letters):
        st.dataframe(letters[["company_name", "letter_date", "top_violation", "letter_severity", "source_url"]]
                     .sort_values("letter_date", ascending=False), hide_index=True, width="stretch",
                     column_config={"source_url": st.column_config.LinkColumn("FDA letter"),
                                    "letter_severity": st.column_config.ProgressColumn(
                                        "severity", min_value=0, max_value=1, format="%.2f")})
    st.subheader("Supplier contracts · clause extractor")
    if synthetic:
        st.info("◆ Synthetic view: the 11 contracts are synthetic (invented for testing) and here their risk counts for "
                "20% of the compliance mark (range R6). In the real view they are not scored (decision 7).")
    else:
        st.warning("DEMO ONLY: the 11 contracts are synthetic (invented for testing). Their results are NOT part of any "
                   "score (decision 7).")
    cl = csv(L3_OUT / "c4_contract_clauses.csv")
    if len(cl):
        st.dataframe(cl[["supplier_name", "force_majeure", "lead_time_days", "late_delivery_penalty",
                         "exclusive_share_pct", "contract_risk", "extraction_source"]], hide_index=True,
                     width="stretch")
    txt = st.text_area("Try it: paste a supply-contract text", height=150,
                       placeholder="… 8. FORCE MAJEURE 8.1 Force Majeure shall mean …")
    if txt.strip():
        res = c4_compliance.rule_extract(" ".join(txt.split()))
        st.json({k: res[k] for k in ["force_majeure", "lead_time", "late_delivery_penalty", "single_source",
                                     "contract_risk"]})
        st.caption("Live reading uses the rule-based extractor (plan's contingency cut order: no live LLM call).")

# --------------------------------------------------------------------------- #
# 5 Data pipeline
# --------------------------------------------------------------------------- #
with tab5:
    console.render()
