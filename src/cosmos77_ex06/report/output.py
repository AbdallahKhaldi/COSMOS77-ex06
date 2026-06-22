"""On-disk report + transcript writers and the sanity-ladder driver (Phase 7).

Kept out of ``sdk.py`` so that file stays under the 150-line cap (rule 1). The
canonical JSON writer (``sort_keys``, UTF-8, fixed indent) gives the byte-stable
output the inter-group bonus (E12) depends on; the ladder driver overrides the
grid size for each rung (2x2 -> 3x3 -> 4x4 -> 5x5) and saves a transcript per size.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from cosmos77_ex06.shared.config import Config

_LADDER_SIZES = [2, 3, 4, 5]


def canonical_json(payload: Any) -> str:
    """Serialize to byte-stable canonical JSON (sorted keys, UTF-8, indent 2)."""
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2)


def save_report(reports_dir: Path, report: dict[str, Any]) -> Path:
    """Write the validated report to ``reports/internal_game.json`` (canonical)."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / "internal_game.json"
    path.write_text(canonical_json(report) + "\n", encoding="utf-8")
    return path


def save_transcript(path: Path, transcript: list[dict[str, Any]]) -> Path:
    """Write a transcript list to ``path`` as readable UTF-8 JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(transcript, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def run_sanity_ladder(
    config: Config,
    reports_dir: Path,
    run_full_game: Callable[..., dict[str, Any]],
    client_factory: Any = None,
) -> list[dict[str, Any]]:
    """Run the 2x2 -> 3x3 -> 4x4 -> 5x5 ladder, saving a transcript per rung.

    ``run_full_game`` is the SDK method (injected to avoid a circular import). Each
    rung overrides ``grid_size`` in place, runs a full game, and writes
    ``reports/ladder_<n>x<n>.json``; the original grid is always restored.
    """
    original = list(config.get("grid_size"))
    summary: list[dict[str, Any]] = []
    try:
        for n in _LADDER_SIZES:
            config._data["grid_size"] = [n, n]  # noqa: SLF001 - ladder override
            outcome = run_full_game(client_factory=client_factory)
            path = save_transcript(reports_dir / f"ladder_{n}x{n}.json", outcome["transcript"])
            summary.append(
                {
                    "grid": [n, n],
                    "transcript_path": str(path),
                    "sub_games": len(outcome["report"]["sub_games"]),
                }
            )
    finally:
        config._data["grid_size"] = original  # noqa: SLF001 - restore default
    return summary
