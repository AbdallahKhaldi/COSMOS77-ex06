"""Byte-for-byte ``bonus_game`` JSON diff-check — run BEFORE either group emails (§8).

A mismatch between the two groups' reports means **0 points for both**, so this
check is mandatory and intentionally dumb-and-total: it compares the two files'
raw bytes. On a mismatch it reports the first differing byte offset and a
normalized key-by-key diff so the offending field (a missing ``sort_keys``, a
float score, an orientation flip, a reordered list — see §8) can be localized and
reconciled before anyone hits send. A clean result is the precondition for setting
``mutual_agreement: true``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def compare_bytes(left: bytes, right: bytes) -> dict[str, Any]:
    """Compare two byte strings; return ``{identical, n_bytes, first_diff}``.

    ``first_diff`` is ``None`` when identical, else the 0-based offset of the first
    differing (or missing) byte.
    """
    if left == right:
        return {"identical": True, "n_bytes": len(left), "first_diff": None}
    limit = min(len(left), len(right))
    offset = next((i for i in range(limit) if left[i] != right[i]), limit)
    return {"identical": False, "n_bytes": max(len(left), len(right)), "first_diff": offset}


def key_diff(left_json: str, right_json: str) -> dict[str, Any]:
    """Return the top-level keys whose values differ between two JSON strings.

    Best-effort localization for a human report; returns ``{}`` if either side is
    not valid JSON (the raw-byte result is still authoritative).
    """
    try:
        a, b = json.loads(left_json), json.loads(right_json)
    except (ValueError, TypeError):
        return {}
    keys = set(a) | set(b)
    return {k: {"left": a.get(k), "right": b.get(k)} for k in sorted(keys) if a.get(k) != b.get(k)}


def diff_files(left: Path | str, right: Path | str) -> dict[str, Any]:
    """Diff two ``bonus_game`` JSON files; return a result dict for reporting."""
    lb = Path(left).read_bytes()
    rb = Path(right).read_bytes()
    result = compare_bytes(lb, rb)
    if not result["identical"]:
        result["key_diff"] = key_diff(lb.decode("utf-8"), rb.decode("utf-8"))
    return result


def format_result(result: dict[str, Any]) -> str:
    """Render a human-readable one-line (plus key diff) verdict from a diff result."""
    if result["identical"]:
        return (
            f"IDENTICAL ({result['n_bytes']} bytes) -> safe to set mutual_agreement:true and send"
        )
    lines = [f"MISMATCH at byte {result['first_diff']} -> DO NOT SEND; reconcile the value object"]
    for key, sides in result.get("key_diff", {}).items():
        lines.append(f"  field {key!r}: left={sides['left']!r} right={sides['right']!r}")
    return "\n".join(lines)
