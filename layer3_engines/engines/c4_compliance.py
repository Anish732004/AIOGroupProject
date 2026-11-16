"""
C4 - Regulatory Compliance & Contract Clause Risk (plan 4.3, 5.2 step 6; Q4).

    C4_i = min(1.0, 0.30*I(OAI_5yr>0) + 0.10*I(VAI_5yr>0) + 0.20*min(1, Recalls_I/II / 2)
                    + 0.20*NLP_WarningSev_i + 0.20*LLM_ContractRisk_i)

The first three terms come from Layer 1 (`C4_fda_component_partial`, plant-scoped CGMP inspections and
sterile-injectable recall events). This module adds the two document terms.

(a) Warning-letter classifier (plan 6a): TF-IDF + Logistic Regression, one model per violation class
    (Data Integrity, Sterility, Process Validation, Quality Unit).
    Labels: the 21 CFR 211 sections each letter cites (e.g. 211.113(b) = sterile-process controls), plus a few
    phrase rules for API letters that cite ICH Q7 instead of 21 CFR 211.
    Features: the letter text with every regulation citation and number REMOVED, so the classifier must learn
    the violation from the narrative, not from the citation that produced the label.
    Scores are out-of-fold probabilities (each letter scored by a model that never saw it).
    Severity per letter = max over classes of weight x probability; sterility and data integrity weigh most.
    NLP_WarningSev_i = worst letter linked to manufacturer i in the last 5 years.

(b) Contract clause extractor (plan 6b): Force Majeure, Lead-Time, Late-Delivery Penalty, Single-Source.
    Primary: zero-shot LLM JSON extraction (Claude), cached in reference/contract_extraction_llm.json, as the plan's
    contingency cut order allows. Each cached record is tied to the contract's SHA-256; if a contract changes or is
    new, the deterministic rule extractor below is used instead. Both are compared clause by clause.
    LLM_ContractRisk_i = mean of the four clause risks (0 = buyer-protective, 1 = supplier-favourable).
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline

log = logging.getLogger("pharmashield.layer3.c4")
SEED = 42
LOOKBACK_YEARS = 5

# ----------------------------------------------------------------------------------------------------------- #
# (a) Warning letters
# ----------------------------------------------------------------------------------------------------------- #
CLASSES = ["data_integrity", "sterility", "process_validation", "quality_unit"]
SEVERITY_WEIGHT = {"sterility": 1.0, "data_integrity": 1.0, "process_validation": 0.6, "quality_unit": 0.5}
CFR_RULES = {   # 21 CFR Part 211 sections -> violation class
    "sterility": r"211\.113\s*\(b\)|211\.42\s*\(c\)",
    "data_integrity": r"211\.68|211\.194",
    "process_validation": r"211\.100|211\.110",
    "quality_unit": r"211\.22\b|211\.22\s*\(|211\.192",
}
PHRASE_RULES = {   # for API (ICH Q7) letters, which do not cite 21 CFR 211
    "sterility": r"aseptic|media fill|sterility assurance",
    "data_integrity": r"data integrity|audit trail",
    "process_validation": r"process validation",
    "quality_unit": r"quality unit",
}
CITATION_RE = re.compile(r"21\s*C\.?F\.?R\.?[^.;)]*|\b\d+(\.\d+)*(\s*\([a-z0-9]+\))*|ICH\s*Q\d+|section\s+\d+\S*",
                         re.I)


def weak_labels(text: pd.Series) -> pd.DataFrame:
    out = {}
    for c in CLASSES:
        out[c] = (text.str.contains(CFR_RULES[c], case=False, regex=True)
                  | text.str.contains(PHRASE_RULES[c], case=False, regex=True)).astype(int)
    return pd.DataFrame(out, index=text.index)


def strip_citations(text: str) -> str:
    return CITATION_RE.sub(" ", text)


def classify_letters(letters: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    y = weak_labels(letters["text"].fillna(""))
    X = letters["text"].fillna("").map(strip_citations)
    probs, report = pd.DataFrame(index=letters.index), {}
    for c in CLASSES:
        pos = int(y[c].sum())
        k = min(5, pos, len(y) - pos)
        if k < 2:   # cannot cross-validate a class that is (almost) always or never present
            probs[c] = y[c].astype(float)
            report[c] = {"positives": pos, "letters": len(y), "method": "rule label (too few of one class)"}
            continue
        oof = np.zeros(len(y))
        for tr, va in StratifiedKFold(k, shuffle=True, random_state=SEED).split(X, y[c]):
            mdl = make_pipeline(
                TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True, stop_words="english",
                                max_features=20000),
                LogisticRegression(class_weight="balanced", C=2.0, max_iter=3000, random_state=SEED))
            mdl.fit(X.iloc[tr], y[c].iloc[tr])
            oof[va] = mdl.predict_proba(X.iloc[va])[:, 1]
        probs[c] = oof
        report[c] = {"positives": pos, "letters": len(y), "method": f"TF-IDF + LogisticRegression, {k}-fold OOF",
                     "oof_roc_auc": round(roc_auc_score(y[c], oof), 3),
                     "oof_f1_at_0.5": round(f1_score(y[c], (oof >= 0.5).astype(int)), 3)}
    sev = pd.concat([probs[c] * SEVERITY_WEIGHT[c] for c in CLASSES], axis=1).max(axis=1)
    out = letters[["doc_id", "company_name", "letter_date", "source_url"]].copy()
    out["fei_number"] = letters["fei_number"].values if "fei_number" in letters else np.nan
    for c in CLASSES:
        out[f"label_{c}"] = y[c].values
        out[f"p_{c}"] = probs[c].round(3).values
    out["letter_severity"] = sev.round(3).values
    out["top_violation"] = probs.mul(pd.Series(SEVERITY_WEIGHT)).idxmax(axis=1).values
    return out, report


def _fei(v) -> str:
    """FDA factory number as a clean string ('' when missing)."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ""
    s = re.sub(r"\.0+$", "", str(v).strip())
    return "" if s.lower() in ("", "nan", "none") else s


def _co(name) -> str:
    """Company name without legal suffixes / punctuation, for 'same company, other plant' checks."""
    s = re.sub(r"\(.*?\)", " ", str(name).upper())
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = re.sub(r"\b(LIMITED|LTD|PRIVATE|PVT|LLC|INC|CORP|CO|BV|B V|GMBH|PTY)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def manufacturer_letter_severity(matrix: pd.DataFrame, scored: pd.DataFrame, links: pd.DataFrame,
                                 as_of: pd.Timestamp) -> pd.DataFrame:
    """Warning-letter term per maker (team decision 'A with the warning note', 15 Nov 2026).

      * factory known (matrix.factory_fei): only letters addressed to THAT factory number count
      * factory unknown (matrix.fda_inspection_record_neutral): no data -> median of the rankable makers whose
        factory is known
      * makers without a factory row (bulk-only, not ranked): letters linked by company name, as before
    Letters to OTHER plants of the same manufacturing company are counted for the warning note, never scored.
    """
    cutoff = as_of - pd.DateOffset(years=LOOKBACK_YEARS)
    recent = scored[pd.to_datetime(scored["letter_date"], errors="coerce") >= cutoff].copy()
    recent["_fei"] = recent["fei_number"].map(_fei) if "fei_number" in recent else ""
    recent["_co"] = recent["company_name"].map(_co)
    by_lab = links.groupby("labeler_key")["external_name"].agg(set)
    has = lambda c: c in matrix.columns  # noqa: E731
    rows = []
    for _, r in matrix.iterrows():
        k = r["manufacturer_id"]
        fei = _fei(r["factory_fei"]) if has("factory_fei") else ""
        neutral = bool(r["fda_inspection_record_neutral"]) if has("fda_inspection_record_neutral") else False
        by_name = recent[recent["company_name"].astype(str).isin(by_lab.get(k, set()))]
        sister_n = 0
        if fei:
            mine, basis = recent[recent["_fei"] == fei], "factory_only"
            sister_n = int(((recent["_co"] == _co(r["factory_name"])) & (recent["_fei"] != fei)).sum())
        elif neutral:
            mine, basis = recent.iloc[0:0], "neutral: factory unknown"
            sister_n = int(len(by_name))          # letters to the company, shown in the note, not scored
        else:
            mine, basis = by_name, "company_name_link"
        if mine.empty:
            rows.append({"manufacturer_id": k, "nlp_warning_severity": 0.0, "warning_letters_5yr": 0,
                         "worst_letter": "", "letters_basis": basis, "unscored_letters_5yr": sister_n})
            continue
        w = mine.sort_values("letter_severity", ascending=False).iloc[0]
        rows.append({"manufacturer_id": k, "nlp_warning_severity": float(w["letter_severity"]),
                     "warning_letters_5yr": int(len(mine)),
                     "worst_letter": f"{w['company_name']} {str(w['letter_date'])[:10]} ({w['top_violation']})",
                     "letters_basis": basis, "unscored_letters_5yr": sister_n})
    out = pd.DataFrame(rows)
    if has("eligible_for_ranking"):
        ref = (out["letters_basis"].eq("factory_only")
               & matrix["eligible_for_ranking"].astype(bool).to_numpy())
        nt = out["letters_basis"].str.startswith("neutral")
        if nt.any() and ref.any():
            out.loc[nt, "nlp_warning_severity"] = round(float(out.loc[ref, "nlp_warning_severity"].median()), 4)
    return out


def warning_note(row: pd.Series) -> str:
    """Plain-English note shown next to the score. It never changes the score."""
    oai = int(row.get("sister_plants_oai_5yr", 0) or 0)
    letters = int(row.get("unscored_letters_5yr", 0) or 0)
    if str(row.get("letters_basis", "")).startswith("neutral"):
        extra = f" The company itself received {letters} warning letter(s) in the last 5 years." if letters else ""
        return ("Factory not named on the drug label: inspection and warning-letter terms are neutral (no data)."
                + extra + " Not scored.")
    if row.get("letters_basis") == "factory_only" and (oai or letters):
        return (f"Other plants of {row.get('factory_name')}: {oai} serious (OAI) inspection(s) and {letters} "
                f"warning letter(s) in the last 5 years. Not scored: the score covers only the factory that makes "
                f"this product.")
    return ""


# ----------------------------------------------------------------------------------------------------------- #
# (b) Contracts
# ----------------------------------------------------------------------------------------------------------- #
CLAUSES = ["force_majeure", "lead_time", "late_delivery_penalty", "single_source"]


def lead_time_risk(days: int | None) -> float:
    """30 days or less = 0 (best), 90 days or more = 1; missing lead time = 1."""
    if days is None:
        return 1.0
    return float(np.clip((days - 30) / 60, 0, 1))


def _section(text: str, heading: str) -> str:
    """Body of a numbered section ('8. FORCE MAJEURE 8.1 ...') up to the next numbered heading. Works on text whose
    line breaks were collapsed by Layer 1 (headings are upper-case and followed by 'n.1')."""
    m = re.search(rf"\b\d+\.\s*{heading}\b(.*?)(?=\s\d+\.\s+[A-Z][A-Z ,&]{{3,}}\s+\d+\.\d|\Z)", text, flags=re.S)
    return m.group(1) if m else ""


def rule_extract(text: str) -> dict:
    """Deterministic clause extractor (fallback and cross-check for the LLM extraction)."""
    fm = _section(text, "FORCE MAJEURE")
    if re.search(r"FORESEEABLE|do NOT constitute Force Majeure", fm):
        fm_cat, fm_risk = "hormuz_disruption_excluded", 0.0
    elif re.search(r"Supplier considers|without limit|no obligation to re-route", fm, re.I):
        fm_cat, fm_risk = "supplier_discretion_unlimited", 1.0
    elif re.search(r"maximum of \d+ days", fm, re.I):
        fm_cat, fm_risk = "balanced_capped", 0.5
    else:
        fm_cat, fm_risk = ("missing" if not fm.strip() else "unclassified"), 1.0 if not fm.strip() else 0.5
    m = re.search(r"within (\d+) calendar days", text, re.I)
    days = int(m.group(1)) if m else None
    late = _section(text, "LATE DELIVERY")
    if re.search(r"not be liable for any penalty|estimates only", late, re.I) or not late.strip():
        pen_cat, pen_risk = "none", 1.0
    elif re.search(r"per week of delay", late, re.I):
        pen_cat, pen_risk = "weekly_ld_with_substitute_right", 0.0
    else:
        pen_cat, pen_risk = "ld_after_delay_threshold_low_cap", 0.5
    ex = _section(text, "EXCLUSIVITY")
    pct = re.search(r"not less than (\d+)%", ex)
    blocks = bool(re.search(r"shall not qualify an alternative source|sole-source commitment", ex, re.I))
    ss_risk = 1.0 if (pct or blocks) else 0.0
    cont = _section(text, "SUPPLY CONTINUITY")
    alloc = ("supplier_discretion" if re.search(r"sole discretion", cont, re.I) else
             "buyer_priority" if re.search(r"with priority", cont, re.I) else
             "pro_rata" if re.search(r"pro-rata", cont, re.I) else "unspecified")
    ss = re.search(r"safety stock equal to (\d+) days", cont, re.I)
    rec = {
        "force_majeure": {"category": fm_cat, "risk": fm_risk},
        "lead_time": {"days": days, "risk": lead_time_risk(days)},
        "late_delivery_penalty": {"category": pen_cat, "risk": pen_risk},
        "single_source": {"exclusive_share_pct": int(pct.group(1)) if pct else None,
                          "blocks_second_source": blocks, "risk": ss_risk},
        "other_clauses": {"shortage_allocation": alloc, "safety_stock_days": int(ss.group(1)) if ss else 0,
                          "surcharges_uncapped": bool(re.search(r"not capped", text, re.I)),
                          "supplier_can_terminate_for_convenience":
                              bool(re.search(r"Supplier may terminate this Agreement for convenience", text, re.I))},
    }
    rec["contract_risk"] = round(float(np.mean([rec[c]["risk"] for c in CLAUSES])), 4)
    return rec


def extract_contracts(contracts: pd.DataFrame, cache_path: Path) -> tuple[pd.DataFrame, dict]:
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {"contracts": []}
    by_hash = {c["text_sha256"]: c for c in cache.get("contracts", [])}
    rows, agree = [], {c: 0 for c in CLAUSES}
    compared = 0
    for _, r in contracts.iterrows():
        rule = rule_extract(r["text"])
        llm = by_hash.get(r["text_sha256"])
        if llm is not None:
            compared += 1
            for c in CLAUSES:
                agree[c] += int(abs(llm[c]["risk"] - rule[c]["risk"]) < 1e-9)
        use = llm if llm is not None else rule
        rows.append({
            "supplier_name": r["supplier_name"], "source_file": r["source_file"],
            "extraction_source": "llm_cache" if llm is not None else "rule_extractor (no matching LLM cache entry)",
            "contract_risk": use["contract_risk"],
            **{f"{c}_risk": use[c]["risk"] for c in CLAUSES},
            "force_majeure": use["force_majeure"]["category"], "lead_time_days": use["lead_time"]["days"],
            "late_delivery_penalty": use["late_delivery_penalty"]["category"],
            "exclusive_share_pct": use["single_source"]["exclusive_share_pct"],
            **{k: v for k, v in use["other_clauses"].items()},
            "rule_contract_risk": rule["contract_risk"],
            "llm_rule_agree_all_clauses": (llm is not None and all(abs(llm[c]["risk"] - rule[c]["risk"]) < 1e-9
                                                                   for c in CLAUSES)),
        })
    report = {"contracts": len(contracts), "llm_cache_hits": compared,
              "llm_model": cache.get("model"), "llm_extracted_on": cache.get("extracted_on"),
              "clause_agreement_llm_vs_rules": {c: f"{agree[c]}/{compared}" for c in CLAUSES}}
    return pd.DataFrame(rows), report


# ----------------------------------------------------------------------------------------------------------- #
def run(matrix: pd.DataFrame, letters: pd.DataFrame, contracts: pd.DataFrame, letter_links: pd.DataFrame,
        contract_links: pd.DataFrame, cache_path: Path, as_of: pd.Timestamp) -> dict:
    scored, nlp_report = classify_letters(letters)
    sev = manufacturer_letter_severity(matrix, scored, letter_links, as_of)
    ct, ct_report = extract_contracts(contracts, cache_path)
    # a contract belongs to the company that signed it: only direct ('self') links, never parent / contract-
    # manufacturer aliases (e.g. Apotex must not inherit Teyro Labs' own supply agreement)
    own = contract_links[contract_links["relationship"].eq("self")] if "relationship" in contract_links else contract_links
    by_lab = own.groupby("labeler_key")["external_name"].agg(set)
    crisk, csrc = [], []
    for k in matrix["manufacturer_id"]:
        mine = ct[ct["supplier_name"].isin(by_lab.get(k, set()))]
        if mine.empty:
            crisk.append(0.5)
            csrc.append("no contract on file - neutral 0.5")
        else:
            crisk.append(float(mine["contract_risk"].max()))
            csrc.append(mine.iloc[0]["extraction_source"])
    panel = sev.copy()
    for c_ in ("factory_name", "sister_plants_oai_5yr"):
        panel[c_] = matrix[c_].to_numpy() if c_ in matrix.columns else None
    panel["sister_plant_warning"] = panel.apply(warning_note, axis=1)
    panel = panel.drop(columns=["factory_name", "sister_plants_oai_5yr"])
    # Team decision item 7 (15 Nov 2026): the 11 contracts are SYNTHETIC (invented terms for real company names),
    # so they are not evidence. The contract term is excluded from the score (0 for every maker); the extraction
    # result is kept only as a demonstration of the NLP contract reader (plan step 6b).
    panel["contract_risk_demo_only"] = crisk
    panel["contract_risk_source"] = [f"NOT SCORED (synthetic contract) - {s}" for s in csrc]
    panel["contract_risk"] = 0.0
    fda = pd.to_numeric(matrix["C4_fda_component_partial"], errors="coerce").fillna(0).to_numpy()
    panel["c4_fda_part"] = fda
    panel["C4_compliance_risk"] = np.round(np.minimum(
        1.0, fda + 0.20 * panel["nlp_warning_severity"] + 0.20 * panel["contract_risk"]), 4)
    return {"panel": panel, "letters": scored, "contracts": ct,
            "metrics": {"warning_letter_classifier": nlp_report, "severity_weights": SEVERITY_WEIGHT,
                        "letter_lookback_years": LOOKBACK_YEARS, "contract_extraction": ct_report,
                        "formula": "min(1, 0.30*I(OAI) + 0.10*I(VAI) + 0.20*min(1, recalls/2) "
                                   "+ 0.20*NLP_WarningSev + 0.20*LLM_ContractRisk); contract term = 0 for all "
                                   "makers because the contracts are synthetic (team decision item 7)"}}
