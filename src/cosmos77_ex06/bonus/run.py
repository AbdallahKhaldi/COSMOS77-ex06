"""High-level bonus driver: run the series, build + serialize + save the report (E12).

Kept out of ``sdk.py`` so that file stays under the 150-line cap (Rule 1); the SDK
``bonus()`` method is a one-line delegation here. Runs the role-swap series, builds
and validates the §9.2 ``bonus_game`` dict, serializes it via the SHARED canonical
serializer (byte-identical across both groups), optionally writes
``reports/bonus_game.json``, and records the totals on the gatekeeper.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cosmos77_ex06.bonus import report as bonus_report
from cosmos77_ex06.bonus.series import run_series_sync
from cosmos77_ex06.shared.config import Config
from cosmos77_ex06.shared.gatekeeper import Gatekeeper


def run_bonus(
    config: Config,
    gatekeeper: Gatekeeper,
    reports_dir: Path,
    *,
    client_factory: Any = None,
    save: bool = True,
) -> dict[str, Any]:
    """Run the series + build the canonical ``bonus_game`` report; return its dict + JSON.

    Returns ``{report, json, path, reruns}``. ``client_factory`` injects a mock
    genai client (tests); ``save`` writes ``reports/bonus_game.json`` when true.
    """
    series = run_series_sync(config, gatekeeper, client_factory=client_factory)
    report = bonus_report.build_report(config, series["sub_games"])
    text = bonus_report.serialize(report)
    path: str | None = None
    if save:
        reports_dir.mkdir(parents=True, exist_ok=True)
        out = reports_dir / "bonus_game.json"
        out.write_text(text + "\n", encoding="utf-8")
        path = str(out)
    gatekeeper.record(
        "bonus_game",
        {"totals_by_group": report["totals_by_group"], "reruns": series["reruns"]},
    )
    return {"report": report, "json": text, "path": path, "reruns": series["reruns"]}
