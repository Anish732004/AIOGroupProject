"""
Paths and the locked-schema hand-off shared by the Layer 3 engines.

Layer 3 reads what Layer 1/2 wrote and fills four locked columns of
data/processed/suppliers_matrix.csv (plan 5.1): C2_delivery_risk, C3_price_integrity,
C4_compliance_risk and shap_top3_reasons. Nothing else in the locked 16 columns is touched.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]          # repository root


@dataclass(frozen=True)
class Paths:
    root: Path = ROOT
    l1: Path = ROOT / "layer1_ingestion"
    interim: Path = ROOT / "layer1_ingestion" / "data" / "interim"
    l1_reference: Path = ROOT / "layer1_ingestion" / "reference"
    l1_manifest: Path = ROOT / "layer1_ingestion" / "data" / "manifest.json"
    processed: Path = ROOT / "data" / "processed"
    reference: Path = ROOT / "layer3_engines" / "reference"
    outputs: Path = ROOT / "layer3_engines" / "outputs"


P = Paths()
FILLED_BY_LAYER3 = ["C2_delivery_risk", "C3_price_integrity", "C4_compliance_risk", "shap_top3_reasons"]


def read_interim(name: str, **kw) -> pd.DataFrame:
    p = P.interim / f"{name}.csv"
    if not p.exists():
        raise FileNotFoundError(f"{p} missing - run Layer 1 first: cd layer1_ingestion && python run_ingestion.py")
    return pd.read_csv(p, low_memory=False, **kw)


def as_of() -> pd.Timestamp:
    """Run date of the Layer 1 snapshot (look-back windows must match Layer 1)."""
    if P.l1_manifest.exists():
        return pd.Timestamp(json.loads(P.l1_manifest.read_text())["as_of"])
    return pd.Timestamp.today().normalize()


def locked_columns() -> list[str]:
    return pd.read_csv(P.l1_reference / "locked_schema.csv")["column"].tolist()


def load_matrix() -> pd.DataFrame:
    p = P.processed / "suppliers_matrix.csv"
    if not p.exists():
        raise FileNotFoundError(f"{p} missing - run Layer 1 first")
    m = pd.read_csv(p)
    if list(m.columns[:16]) != locked_columns():
        raise ValueError("suppliers_matrix.csv does not start with the locked 16 columns (plan 5.1)")
    return m


def save_matrix(m: pd.DataFrame) -> Path:
    """Validate the locked schema and the Layer 3 columns, then write in place."""
    locked = locked_columns()
    assert list(m.columns[:16]) == locked, "locked column names / order changed"
    for c in ["C2_delivery_risk", "C3_price_integrity", "C4_compliance_risk"]:
        v = pd.to_numeric(m[c], errors="coerce")
        assert v.notna().all(), f"{c} has empty rows"
        assert v.between(0, 1).all(), f"{c} outside [0, 1]"
    for s in m["shap_top3_reasons"]:
        assert isinstance(json.loads(s), list), "shap_top3_reasons must be a JSON list"
    p = P.processed / "suppliers_matrix.csv"
    m.to_csv(p, index=False)
    return p


def write_output(df_or_obj, name: str) -> Path:
    P.outputs.mkdir(parents=True, exist_ok=True)
    if isinstance(df_or_obj, pd.DataFrame):
        p = P.outputs / f"{name}.csv"
        df_or_obj.to_csv(p, index=False)
    else:
        p = P.outputs / f"{name}.json"
        p.write_text(json.dumps(df_or_obj, indent=2, default=str))
    return p


def links_for(source: str) -> pd.DataFrame:
    """Entity links (Layer 2) from manufacturer to names in one source, after the manual check."""
    c = read_interim("entity_match_candidates")
    return c[c["source"] == source][["labeler_key", "external_name", "match_method", "relationship"]]
