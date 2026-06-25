"""Report send/validate dispatch — the SDK delegates here (Phase 9, E7).

Includes a SAFETY guard so the professor's submission address is never emailed by
accident (critical when test-running the bonus with other groups):

* :func:`auto_send` — the autonomous end-of-game email. Fires ONLY when
  ``report.confirm_final`` is true, so a test/bonus game can never email the
  professor. Failures are recorded + swallowed so a run never crashes (E5).
* :func:`send_latest` — the CLI ``report --send`` path. Sending to the configured
  professor address (``report.to``) REQUIRES the explicit ``--final`` flag;
  otherwise it refuses and tells you to use ``--to <your-email>`` for a self-test.
  A ``--to`` override (any other address) always sends.

Validation always runs before transport: a schema-drift / short / bad report
aborts the send rather than emailing a malformed report.
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

#: Shown when a send to the professor's address is blocked for safety.
_BLOCK_MSG = (
    "SAFETY: refusing to email the professor ({to}) without confirmation. "
    "Use `report --send --to <your-email>` to self-test, or add `--final` to send the real submission."
)


def auto_send(
    config: Config, gatekeeper: Gatekeeper, report: dict[str, Any], sender: Any = None
) -> None:
    """Autonomously email the validated report at game end — ONLY when confirmed (E7/E5).

    Gated by ``report.confirm_final`` (default false) so a test/bonus game never emails
    the professor. Any send failure is recorded + swallowed so the game never crashes.
    """
    if not bool(config.get("report.confirm_final", default=False)):
        gatekeeper.record(
            "report_send",
            {
                "sent": False,
                "blocked": "auto_send off — set report.confirm_final: true to email the professor",
            },
        )
        return
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
    final: bool = False,
) -> dict[str, Any]:
    """Load + validate the latest report; optionally send it behind the professor-safety guard.

    Sending to the configured professor address (``report.to``) requires ``final=True``;
    a ``to`` override (a self-test recipient) always sends. ``send=False`` validates only.
    """
    path = reports_dir / "internal_game.json"
    if not path.exists():
        raise FileNotFoundError(
            f"no report at {path}; run `cosmos77-pursuit run --games 6` first to build it"
        )
    report = json.loads(path.read_text(encoding="utf-8"))
    validate_internal_game(report)
    result: dict[str, Any] = {"report": report, "path": str(path), "sent": False, "blocked": None}
    if not send:
        return result
    prof = str(config.get("report.to"))
    recipient = to or prof
    if recipient == prof and not final:
        msg = _BLOCK_MSG.format(to=prof)
        gatekeeper.record("report_send", {"sent": False, "blocked": msg})
        result["blocked"] = msg
        return result
    active = sender or GmailSender(config, to=to)
    result["response"] = active.send(output.canonical_json(report))
    result["sent"] = True
    gatekeeper.record("report_send", {"sent": True, "to": active.to})
    return result


def send_bonus(
    config: Config,
    gatekeeper: Gatekeeper,
    reports_dir: Path,
    *,
    send: bool = False,
    sender: Any = None,
    to: str | None = None,
    final: bool = False,
) -> dict[str, Any]:
    """Validate + Gmail-send ``bonus_game.json`` behind the SAME professor-safety guard (E12).

    The body is the EXACT file content both groups diff + email, so the two submissions
    are byte-identical. Sending to the professor (``report.to``) requires ``final=True``;
    a ``to`` override self-tests. ``send=False`` validates only.
    """
    from cosmos77_ex06.bonus.schema import validate_bonus_game

    path = reports_dir / "bonus_game.json"
    if not path.exists():
        raise FileNotFoundError(
            f"no bonus report at {path}; run `cosmos77-pursuit bonus --partner config/` first"
        )
    body = path.read_text(encoding="utf-8")
    validate_bonus_game(json.loads(body))
    result: dict[str, Any] = {"path": str(path), "sent": False, "blocked": None}
    if not send:
        return result
    prof = str(config.get("report.to"))
    recipient = to or prof
    if recipient == prof and not final:
        msg = _BLOCK_MSG.format(to=prof)
        gatekeeper.record("bonus_send", {"sent": False, "blocked": msg})
        result["blocked"] = msg
        return result
    active = sender or GmailSender(config, to=to, subject="COSMOS77-ex06 bonus_game report")
    result["response"] = active.send(body)
    result["sent"] = True
    gatekeeper.record("bonus_send", {"sent": True, "to": active.to})
    return result
