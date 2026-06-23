"""Report send/validate dispatch — the SDK delegates here (Phase 9, E7).

Extracted from ``sdk.py`` to keep that file under the 150-line cap (rule 1), the
same way ``output.run_sanity_ladder`` is. Two entry points:

* :func:`auto_send` — the autonomous end-of-game email (``report.auto_send`` true);
  failures are recorded and SWALLOWED so a missing ``credentials.json`` never
  crashes the run mid-pipeline (E5) — the JSON is already on disk regardless.
* :func:`send_latest` — the CLI ``report --send`` path: load the latest on-disk
  report, validate it against the pydantic schema BEFORE any send, canonically
  serialize it, and email the JSON-only body.

Validation always runs before transport (PRD §4): a schema-drift / short / bad
report aborts the send rather than emailing a malformed autonomous report.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cosmos77_ex06.report import output
from cosmos77_ex06.report.gmail_sender import GmailSender
from cosmos77_ex06.report.schema import validate_internal_game
from cosmos77_ex06.shared.config import Config
from cosmos77_ex06.shared.gatekeeper import Gatekeeper


def auto_send(
    config: Config, gatekeeper: Gatekeeper, report: dict[str, Any], sender: Any = None
) -> None:
    """Autonomously email the validated report at game end when configured (E7).

    The report has already been validated + saved by the runner. Any send failure
    (e.g. missing ``credentials.json``) is recorded with an actionable message and
    swallowed so the game never crashes after a complete run (E5).
    """
    active = sender or GmailSender(config)
    try:
        response = active.send(output.canonical_json(report))
    except Exception as exc:  # noqa: BLE001 - never crash the run; log + continue (E5)
        gatekeeper.record("report_send", {"sent": False, "error": f"{type(exc).__name__}: {exc}"})
        return
    gatekeeper.record("report_send", {"sent": True, "to": active.to, "response": response})


def send_latest(
    config: Config,
    gatekeeper: Gatekeeper,
    reports_dir: Path,
    *,
    send: bool = False,
    sender: Any = None,
    to: str | None = None,
) -> dict[str, Any]:
    """Load + validate the latest ``reports/internal_game.json``; optionally send it.

    Validates against the pydantic schema (rejecting a malformed report BEFORE any
    send); ``send=False`` validates only. The first send opens the OAuth consent and
    writes ``token.json``. ``sender`` injects a mock GmailSender in tests.
    """
    path = reports_dir / "internal_game.json"
    if not path.exists():
        raise FileNotFoundError(
            f"no report at {path}; run `cosmos77-pursuit run --games 6` first to build it"
        )
    report = json.loads(path.read_text(encoding="utf-8"))
    validate_internal_game(report)
    result: dict[str, Any] = {"report": report, "path": str(path), "sent": False}
    if send:
        active = sender or GmailSender(config, to=to)
        result["response"] = active.send(output.canonical_json(report))
        result["sent"] = True
        gatekeeper.record("report_send", {"sent": True, "to": active.to})
    return result
