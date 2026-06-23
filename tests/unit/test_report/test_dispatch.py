"""Report dispatch tests — the professor-safety guard + auto-send + send-latest (mocked)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cosmos77_ex06.report import dispatch, output
from cosmos77_ex06.shared.config import Config
from cosmos77_ex06.shared.gatekeeper import Gatekeeper

_VALID_REPORT = {
    "group_name": "COSMOS77",
    "students": [{"id": "212389712", "name_en": "Abdallah Khaldi", "name_he": "עבדאללה"}],
    "github_repo": "https://github.com/AbdallahKhaldi/COSMOS77-ex06",
    "cop_mcp_url": "https://cop.example/mcp",
    "thief_mcp_url": "https://thief.example/mcp",
    "timezone": "Asia/Jerusalem",
    "sub_games": [
        {
            "index": 1,
            "winner": "cop",
            "moves": 3,
            "capture": True,
            "cop_score": 20,
            "thief_score": 5,
        }
    ],
    "totals": {"cop": 20, "thief": 5},
}


class _Sender:
    to = "rmisegal+uoh26b@gmail.com"

    def __init__(self) -> None:
        self.body: str | None = None

    def send(self, body: str) -> dict:
        self.body = body
        return {"id": "msg-1"}


class _BoomSender:
    to = "rmisegal+uoh26b@gmail.com"

    def send(self, body: str) -> dict:
        raise FileNotFoundError("missing credentials.json")


def _confirm(config: Config) -> None:
    config._data["report"]["confirm_final"] = True  # noqa: SLF001 - test-only flip


# --- auto_send (the game-end auto-email) -------------------------------------------------


def test_auto_send_blocked_unless_confirmed(config: Config, tmp_path: Path) -> None:
    """A test/bonus game must NEVER email the professor: auto_send is off by default."""
    gk = Gatekeeper(tmp_path)
    sender = _Sender()
    dispatch.auto_send(config, gk, _VALID_REPORT, sender=sender)
    assert sender.body is None  # nothing was sent
    assert gk.read("report_send")["sent"] is False
    assert "confirm_final" in gk.read("report_send")["blocked"]


def test_auto_send_sends_when_confirmed(config: Config, tmp_path: Path) -> None:
    _confirm(config)
    gk = Gatekeeper(tmp_path)
    sender = _Sender()
    dispatch.auto_send(config, gk, _VALID_REPORT, sender=sender)
    assert gk.read("report_send")["sent"] is True
    assert json.loads(sender.body) == _VALID_REPORT


def test_auto_send_swallows_failure_never_crashes_run(config: Config, tmp_path: Path) -> None:
    _confirm(config)
    gk = Gatekeeper(tmp_path)
    dispatch.auto_send(config, gk, _VALID_REPORT, sender=_BoomSender())  # no raise
    rec = gk.read("report_send")
    assert rec["sent"] is False and "FileNotFoundError" in rec["error"]


# --- send_latest (the CLI `report --send` path) ------------------------------------------


def test_send_latest_missing_file_raises(config: Config, tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        dispatch.send_latest(
            config, Gatekeeper(tmp_path), tmp_path / "reports", send=True, final=True
        )


def _with_report(tmp_path: Path) -> Path:
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "internal_game.json").write_text(output.canonical_json(_VALID_REPORT), "utf-8")
    return reports


def test_send_latest_to_professor_blocked_without_final(config: Config, tmp_path: Path) -> None:
    """A bare `report --send` (recipient = the professor) is refused without --final."""
    reports = _with_report(tmp_path)
    sender = _Sender()
    res = dispatch.send_latest(config, Gatekeeper(tmp_path), reports, send=True, sender=sender)
    assert res["sent"] is False and res["blocked"] and sender.body is None


def test_send_latest_final_sends_to_professor(config: Config, tmp_path: Path) -> None:
    reports = _with_report(tmp_path)
    sender = _Sender()
    res = dispatch.send_latest(
        config, Gatekeeper(tmp_path), reports, send=True, sender=sender, final=True
    )
    assert res["sent"] is True and res["blocked"] is None
    assert json.loads(sender.body) == _VALID_REPORT


def test_send_latest_to_override_self_test_sends(config: Config, tmp_path: Path) -> None:
    """A `--to <your-email>` self-test always sends (it is not the professor)."""
    reports = _with_report(tmp_path)
    sender = _Sender()
    res = dispatch.send_latest(
        config,
        Gatekeeper(tmp_path),
        reports,
        send=True,
        sender=sender,
        to="abdallahkh12@icloud.com",
    )
    assert res["sent"] is True and res["blocked"] is None


def test_send_latest_send_false_validates_only(config: Config, tmp_path: Path) -> None:
    reports = _with_report(tmp_path)
    res = dispatch.send_latest(config, Gatekeeper(tmp_path), reports, send=False)
    assert res["sent"] is False and res["blocked"] is None and res["report"] == _VALID_REPORT
