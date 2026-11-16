"""
C2 - Delivery Disruption Risk (plan 4.3, 5.2 step 4; Q3).

    C2_i = P_XGB(Delivered > Scheduled | Country_i, ShipmentMode_i, FreightRatio_i, Weight_i, IncoTerm_i, SitePrior_i)

* Trained on USAID SCMS shipments scheduled <= 2013, evaluated out-of-time on 2014-2015 (no leakage).
* Compared with a LogisticRegression baseline: ROC-AUC, PR-AUC, Recall, Precision, Confusion Matrix.
* scale_pos_weight is tuned for late-shipment recall on an inner time split (fit <= 2012, validate 2013), using
  F2 (recall counts twice as much as precision) so the model is not rewarded for flagging everything.
* Site prior = smoothed historical late rate of the manufacturing site. Train rows get out-of-fold values (a row
  never sees its own label); test rows and the 2026 panel get values computed on the train period only.
* Feature-based inference for every carboplatin maker (plan 3.1) from its plant country, shipping mode, freight
  ratio, weight and site history; the weighted-training probability is corrected back to the true base rate.
* SHAP values: XGBoost's exact TreeSHAP (pred_contribs), grouped back to the plan's six features; top 3 per maker
  become `shap_top3_reasons` (JSON).
"""
from __future__ import annotations

import json
import logging

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, confusion_matrix, f1_score, fbeta_score, precision_score,
                             recall_score, roc_auc_score)
from sklearn.model_selection import KFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

log = logging.getLogger("pharmashield.layer3.c2")
SEED = 42
PRIOR_ALPHA = 20          # smoothing: a site needs ~20 shipments before its own rate dominates the global rate
MIN_COUNTRY_ROWS = 30     # rarer countries are pooled as "Other"
FEATURE_LABELS = {        # plan 4.3 feature -> plain-English label for SHAP explanations
    "manufacturing_country": "Plant country",
    "shipment_mode": "Shipping mode",
    "freight_to_value_ratio": "Freight-to-value ratio",
    "weight_kg": "Shipment weight",
    "vendor_inco_term": "Delivery terms (Incoterm)",
    "site_prior": "Site delivery history",
}
XGB_PARAMS = dict(n_estimators=400, max_depth=4, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
                  min_child_weight=5, reg_lambda=1.0, eval_metric="auc", random_state=SEED, n_jobs=4)


# --------------------------------------------------------------------------- #
# Features
# --------------------------------------------------------------------------- #
def smoothed_rate(late_sum, n, global_rate: float, alpha: float = PRIOR_ALPHA):
    return (np.asarray(late_sum, float) + alpha * global_rate) / (np.asarray(n, float) + alpha)


def site_prior_oof(train: pd.DataFrame, folds: int = 5) -> tuple[np.ndarray, np.ndarray]:
    """Out-of-fold smoothed site late-rate for training rows (a row never sees its own label)."""
    g = train["late"].mean()
    rate, cnt = np.empty(len(train)), np.empty(len(train))
    for tr, va in KFold(folds, shuffle=True, random_state=SEED).split(train):
        st = train.iloc[tr].groupby("site")["late"].agg(["sum", "count"])
        s = train.iloc[va]["site"].map(st["sum"]).fillna(0).to_numpy()
        n = train.iloc[va]["site"].map(st["count"]).fillna(0).to_numpy()
        rate[va], cnt[va] = smoothed_rate(s, n, g), n
    return rate, cnt


def raw_features(df: pd.DataFrame, countries: list[str]) -> pd.DataFrame:
    """The plan's six features before encoding (shared by SCMS rows and panel rows)."""
    out = pd.DataFrame(index=df.index)
    c = df["manufacturing_country"].fillna("Other").astype(str)
    out["manufacturing_country"] = c.where(c.isin(countries), "Other")
    out["shipment_mode"] = df["shipment_mode"].fillna("Unknown").astype(str)
    out["vendor_inco_term"] = df["vendor_inco_term"].fillna("Unknown").astype(str)
    out["log_freight_to_value"] = np.log1p(pd.to_numeric(df["freight_to_value_ratio"], errors="coerce").clip(lower=0))
    out["log_weight_kg"] = np.log1p(pd.to_numeric(df["weight_kg"], errors="coerce").clip(lower=0))
    out["site_prior_late_rate"] = df["site_prior_late_rate"].astype(float)
    out["log_site_prior_n"] = np.log1p(df["site_prior_n"].astype(float))
    return out


CAT_COLS = ["manufacturing_country", "shipment_mode", "vendor_inco_term"]
GROUP_OF = {"log_freight_to_value": "freight_to_value_ratio", "log_weight_kg": "weight_kg",
            "site_prior_late_rate": "site_prior"}
# Kept for the explanation text only, NOT a model input: in SCMS only 19 training rows had no site history and all
# were on time, so the model learned "no history = never late" and scored every new supplier as safest. Without
# the count, an unknown site gets the smoothed global late rate, i.e. missing history is neutral (plan 3.1, Q&A 5).
EXPLAIN_ONLY = ["log_site_prior_n"]
# small grid, chosen on the 2013 validation year (never on the 2014-15 test set)
PARAM_GRID = [dict(max_depth=4, n_estimators=400, learning_rate=0.05, min_child_weight=5),
              dict(max_depth=3, n_estimators=300, learning_rate=0.05, min_child_weight=10),
              dict(max_depth=2, n_estimators=300, learning_rate=0.05, min_child_weight=10),
              dict(max_depth=3, n_estimators=600, learning_rate=0.02, min_child_weight=20)]


def encode(raw: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    X = pd.get_dummies(raw.drop(columns=[c for c in EXPLAIN_ONLY if c in raw]), columns=CAT_COLS,
                       prefix_sep="=", dtype=float)
    if columns is not None:
        X = X.reindex(columns=columns, fill_value=0.0)
    return X


def feature_group(col: str) -> str:
    return col.split("=")[0] if "=" in col else GROUP_OF.get(col, col)


# --------------------------------------------------------------------------- #
# Training data
# --------------------------------------------------------------------------- #
def training_frames(scms: pd.DataFrame):
    d = scms[scms["time_split"].isin(["train", "test"])].copy()
    d["site"] = d["manufacturing_site"].fillna("UNKNOWN_SITE").astype(str)
    train, test = d[d["time_split"] == "train"].copy(), d[d["time_split"] == "test"].copy()
    g = train["late"].mean()
    train["site_prior_late_rate"], train["site_prior_n"] = site_prior_oof(train)
    st = train.groupby("site")["late"].agg(["sum", "count"])
    s, n = test["site"].map(st["sum"]).fillna(0), test["site"].map(st["count"]).fillna(0)
    test["site_prior_late_rate"], test["site_prior_n"] = smoothed_rate(s, n, g), n.to_numpy()
    vc = train["manufacturing_country"].value_counts()
    countries = sorted(vc[vc >= MIN_COUNTRY_ROWS].index)
    return train, test, countries, g


def metrics(y, p, thr: float = 0.5) -> dict:
    yhat = (p >= thr).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, yhat, labels=[0, 1]).ravel()
    return {"roc_auc": round(roc_auc_score(y, p), 4), "pr_auc": round(average_precision_score(y, p), 4),
            "recall_late": round(recall_score(y, yhat, zero_division=0), 4),
            "precision_late": round(precision_score(y, yhat, zero_division=0), 4),
            "f1_late": round(f1_score(y, yhat, zero_division=0), 4),
            "f2_late": round(fbeta_score(y, yhat, beta=2, zero_division=0), 4),
            "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}, "threshold": thr}


def tune(train: pd.DataFrame, countries: list[str]) -> tuple[dict, float, list[dict], list[dict]]:
    """Inner time split inside the training period: fit <= 2012, validate on 2013.
    1) tree settings: best validation ROC-AUC;  2) scale_pos_weight: best validation F2 (late-shipment recall)."""
    yr = train["scheduled_year"]
    fit, val = train[yr <= 2012], train[yr == 2013]
    Xf = encode(raw_features(fit, countries))
    Xv = encode(raw_features(val, countries), list(Xf.columns))
    ratio = (fit["late"] == 0).sum() / max(1, (fit["late"] == 1).sum())
    keep = ("roc_auc", "recall_late", "precision_late", "f2_late")
    p_rows = []
    for g in PARAM_GRID:
        mdl = xgb.XGBClassifier(**{**XGB_PARAMS, **g}, scale_pos_weight=ratio).fit(Xf, fit["late"])
        p_rows.append({**g, **{k: v for k, v in metrics(val["late"], mdl.predict_proba(Xv)[:, 1]).items()
                               if k in keep}})
    best_p = max(p_rows, key=lambda r: r["roc_auc"])
    params = {k: best_p[k] for k in PARAM_GRID[0]}
    w_grid = sorted({1.0, round(0.5 * ratio, 2), round(ratio, 2), round(1.5 * ratio, 2), round(2 * ratio, 2)})
    w_rows = []
    for w in w_grid:
        mdl = xgb.XGBClassifier(**{**XGB_PARAMS, **params}, scale_pos_weight=w).fit(Xf, fit["late"])
        w_rows.append({"scale_pos_weight": w, **{k: v for k, v in metrics(val["late"], mdl.predict_proba(Xv)[:, 1])
                                                 .items() if k in keep}})
    best_w = max(w_rows, key=lambda r: (r["f2_late"], r["roc_auc"]))
    return params, float(best_w["scale_pos_weight"]), p_rows, w_rows


def prior_correct(p: np.ndarray, w: float) -> np.ndarray:
    """Undo the odds inflation of scale_pos_weight = w so C2 is a probability on the real base rate."""
    p = np.clip(np.asarray(p, float), 1e-9, 1 - 1e-9)
    return p / (p + (1 - p) * w)


# --------------------------------------------------------------------------- #
# SHAP explanations
# --------------------------------------------------------------------------- #
def grouped_shap(booster: xgb.Booster, X: pd.DataFrame) -> pd.DataFrame:
    contrib = booster.predict(xgb.DMatrix(X), pred_contribs=True)[:, :-1]     # last column = bias
    df = pd.DataFrame(contrib, columns=X.columns, index=X.index)
    return df.T.groupby(feature_group).sum().T


def describe_value(group: str, row: pd.Series) -> str:
    if group == "manufacturing_country":
        return str(row["manufacturing_country"])
    if group == "shipment_mode":
        return str(row["shipment_mode"])
    if group == "vendor_inco_term":
        return str(row["vendor_inco_term"])
    if group == "freight_to_value_ratio":
        return f"{np.expm1(row['log_freight_to_value']):.4f}"
    if group == "weight_kg":
        return f"{np.expm1(row['log_weight_kg']):,.0f} kg"
    if group == "site_prior":
        n = int(round(np.expm1(row["log_site_prior_n"])))
        return f"{n} past shipments, late rate {row['site_prior_late_rate']:.1%}" if n else "no history (global rate)"
    return ""


UNKNOWN_INPUTS = ["shipment_mode", "vendor_inco_term", "freight_to_value_ratio", "weight_kg"]
UNKNOWN_GROUPS = {"shipment_mode", "vendor_inco_term", "freight_to_value_ratio", "weight_kg"}
PROFILE_SAMPLE = 400       # real shipments averaged per maker
MIN_COUNTRY_TRAIN = 30     # below this, the profile uses all training shipments


def marginal_predictions(model: xgb.XGBClassifier, w: float, pnl: pd.DataFrame, train: pd.DataFrame,
                         countries: list[str], columns: list[str]) -> pd.DataFrame:
    """Evidence rule, team decision item 6 (15 Nov 2026): shipping mode, delivery terms, freight ratio and weight
    are NOT known for 2026 carboplatin shipments to the UAE. Instead of one invented value, each maker's C2 is the
    AVERAGE prediction over real SCMS training shipments from the same plant country (all training shipments when
    that country has fewer than 30). Only the maker's real facts (plant country, own site history) are fixed.
    Synthetic view (synthetic/, decision S4): when the panel row says inputs_fixed, the maker's shipping profile is
    a labelled synthetic value, so the model predicts on that single profile instead of averaging. The trained
    model is the same; nothing is re-fitted on synthetic data."""
    booster = model.get_booster()
    rows = []
    for _, r in pnl.iterrows():
        real_c = str(r.get("manufacturing_country_real", r["manufacturing_country"]))
        fixed = bool(r.get("inputs_fixed", False))
        if fixed:
            smp = pd.DataFrame([{c: r[c] for c in UNKNOWN_INPUTS}])
            basis = "synthetic shipping profile for UAE orders"
        else:
            pool = train[train["manufacturing_country"] == real_c]
            basis = f"real shipments from {real_c}"
            if len(pool) < MIN_COUNTRY_TRAIN:
                pool, basis = train, "real shipments from all countries (fewer than 30 from this country)"
            smp = pool.sample(n=min(PROFILE_SAMPLE, len(pool)), random_state=SEED)[UNKNOWN_INPUTS].copy()
        smp["manufacturing_country"] = r["manufacturing_country"]
        smp["site_prior_late_rate"] = r["site_prior_late_rate"]
        smp["site_prior_n"] = r["site_prior_n"]
        raw = raw_features(smp.reset_index(drop=True), countries)
        X = encode(raw, columns)
        p = model.predict_proba(X)[:, 1]
        sh = grouped_shap(booster, X).mean()
        rows.append({"manufacturer_id": r["manufacturer_id"],
                     "C2_delivery_risk": round(float(prior_correct(p, w).mean()), 4),
                     "c2_score_weighted_model": round(float(p.mean()), 4),
                     "model_country": raw["manufacturing_country"].iloc[0],
                     "shipment_profile": f"{basis} (n={len(smp)})",
                     "site_prior_shipments": int(r["site_prior_n"]),
                     "shap_top3_reasons": top3_json(sh, raw.iloc[0], averaged=None if fixed else f"{basis}",
                                                    real_country=real_c, synthetic=fixed)})
    return pd.DataFrame(rows)


def top3_json(shap_row: pd.Series, raw_row: pd.Series, averaged: str | None = None,
              real_country: str | None = None, synthetic: bool = False) -> str:
    top = shap_row.reindex(shap_row.abs().sort_values(ascending=False).index)[:3]
    out = []
    for g, v in top.items():
        val = (f"not known for UAE shipments: averaged over {averaged}" if averaged and g in UNKNOWN_GROUPS
               else describe_value(g, raw_row))
        if synthetic and (g in UNKNOWN_GROUPS or (g == "site_prior" and float(raw_row["log_site_prior_n"]) > 0)):
            val += " (synthetic)"
        if g == "manufacturing_country" and real_country and val == "Other" and real_country != "Other":
            val = f"{real_country} (too few past shipments to model on its own; grouped with other small countries)"
        out.append({"feature": FEATURE_LABELS.get(g, g), "value": val,
                    "shap_log_odds": round(float(v), 4),
                    "effect": "raises late-delivery risk" if v > 0 else "lowers late-delivery risk"})
    return json.dumps(out)


def neutralise_unknown_country(panel: pd.DataFrame, matrix: pd.DataFrame) -> pd.DataFrame:
    """Evidence rule: a maker whose plant country is unknown gets the MEDIAN C2 of the rankable makers whose
    country is known, instead of whatever the model says for the pooled 'Other' country. Flagged in the reasons."""
    m = matrix.set_index("manufacturer_id")
    unknown = panel["manufacturer_id"].map(m["manufacturing_country"]).eq("Unknown")
    ref = panel["manufacturer_id"].map(m["eligible_for_ranking"]).fillna(False).astype(bool) & ~unknown
    out = panel.copy()
    out["c2_basis"] = "xgboost_feature_based_inference"
    if unknown.any() and ref.any():
        med = round(float(out.loc[ref, "C2_delivery_risk"].median()), 4)
        out.loc[unknown, "C2_delivery_risk"] = med
        out.loc[unknown, "c2_basis"] = "neutral: plant country unknown (median of rankable makers with known country)"
        out.loc[unknown, "shap_top3_reasons"] = json.dumps([{
            "feature": "Plant country", "value": "unknown (not stated on the drug label)", "shap_log_odds": 0.0,
            "effect": "no data: neutral score = median of the makers whose plant country is known"}])
    return out


# --------------------------------------------------------------------------- #
def panel_frame(inf: pd.DataFrame, global_rate: float) -> pd.DataFrame:
    """Layer 1's feature row per maker (plan 3.1) -> the model's raw features."""
    d = inf.copy()
    n = d["site_prior_n_shipments"].fillna(0).astype(float)
    late = n * (1 - d["site_prior_on_time_rate"].fillna(0))
    d["site_prior_late_rate"], d["site_prior_n"] = smoothed_rate(late, n, global_rate), n
    d["manufacturing_country_real"] = d["manufacturing_country"]
    d["manufacturing_country"] = d["manufacturing_country"].replace({"Unknown": "Other"})
    return d


def run(scms: pd.DataFrame, inf: pd.DataFrame) -> dict:
    """inf may carry inputs_fixed=True rows (synthetic view): see marginal_predictions."""
    train, test, countries, g = training_frames(scms)
    log.info("C2: train %d rows (late %.1f%%), test %d rows (late %.1f%%)",
             len(train), 100 * train["late"].mean(), len(test), 100 * test["late"].mean())
    params, w, p_grid, w_grid = tune(train, countries)

    raw_tr, raw_te = raw_features(train, countries), raw_features(test, countries)
    Xtr = encode(raw_tr)
    Xte = encode(raw_te, list(Xtr.columns))
    model = xgb.XGBClassifier(**{**XGB_PARAMS, **params}, scale_pos_weight=w).fit(Xtr, train["late"])
    p_te = model.predict_proba(Xte)[:, 1]

    base = make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler(),
                         LogisticRegression(class_weight="balanced", max_iter=3000, random_state=SEED))
    base.fit(Xtr, train["late"])
    p_lr = base.predict_proba(Xte)[:, 1]

    m_xgb, m_lr = metrics(test["late"], p_te), metrics(test["late"], p_lr)
    booster = model.get_booster()
    imp = grouped_shap(booster, Xte).abs().mean().sort_values(ascending=False)

    # ---- feature-based inference for the 2026 carboplatin panel (plan 3.1) ----
    pnl = panel_frame(inf, g)
    panel = marginal_predictions(model, w, pnl, train, countries, list(Xtr.columns))
    n_distinct = panel["C2_delivery_risk"].nunique()
    summary = {
        "train_rows": int(len(train)), "test_rows": int(len(test)),
        "train_late_rate": round(float(train["late"].mean()), 4), "test_late_rate": round(float(test["late"].mean()), 4),
        "split": "train: scheduled <= 2013; test: 2014-2015 (out-of-time)",
        "xgboost_params_chosen": params, "param_grid (fit<=2012, validate 2013, by ROC-AUC)": p_grid,
        "scale_pos_weight_chosen": w, "scale_pos_weight_grid (fit<=2012, validate 2013, by F2)": w_grid,
        "xgboost_test": m_xgb, "logistic_regression_test": m_lr,
        "xgboost_beats_baseline_on_roc_auc": m_xgb["roc_auc"] > m_lr["roc_auc"],
        "global_feature_importance_mean_abs_shap": {FEATURE_LABELS.get(k, k): round(float(v), 4)
                                                     for k, v in imp.items()},
        "countries_modelled": countries,
        "panel_distinct_c2_values": int(n_distinct),
        "caveat": ("SCMS covers ARV/HIV-test logistics (2006-2015); the model learns shipment physics, not "
                   "oncology. Panel makers sharing plant country, mode and freight profile get the same C2."),
    }
    test_pred = pd.DataFrame({"id": test["id"].values, "scheduled_year": test["scheduled_year"].values,
                              "late": test["late"].values, "p_xgboost": np.round(p_te, 4),
                              "p_logreg": np.round(p_lr, 4)})
    return {"panel": panel, "metrics": summary, "test_predictions": test_pred,
            "importance": imp.rename("mean_abs_shap").rename_axis("feature").reset_index()}
