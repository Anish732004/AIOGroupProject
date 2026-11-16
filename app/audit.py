"""
Append-only, tamper-evident audit log for human sign-off (plan 2 Layer 5, 6.1).

Each record stores the SHA-256 of the previous record ("hash chain"). Editing or deleting any earlier line breaks
every later hash, which verify() detects. Personal data is minimised (UAE PDPL): only the approver's initials or
staff ID are stored, for the stated purpose of accountability for purchasing decisions.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

GENESIS = "0" * 64


def _digest(record: dict) -> str:
    body = {k: v for k, v in record.items() if k != "record_hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()


def read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def append(path: Path, entry: dict) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = read(path)
    rec = {"seq": len(rows) + 1, "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           **entry, "prev_hash": rows[-1]["record_hash"] if rows else GENESIS}
    rec["record_hash"] = _digest(rec)
    with path.open("a") as fh:
        fh.write(json.dumps(rec, default=str) + "\n")
    return rec


def verify(path: Path) -> tuple[bool, str]:
    rows = read(path)
    prev = GENESIS
    for r in rows:
        if r.get("prev_hash") != prev:
            return False, f"record {r.get('seq')}: link to previous record broken"
        if _digest(r) != r.get("record_hash"):
            return False, f"record {r.get('seq')}: contents changed after signing"
        prev = r["record_hash"]
    return True, f"{len(rows)} record(s), chain intact"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""
