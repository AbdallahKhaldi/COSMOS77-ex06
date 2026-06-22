"""Report dispatch tests — auto-send + CLI send-latest, fully mocked (rule 6)."""

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


def test_auto_send_records_sent_true(config: Config, tmp_path: Path) -> None:
    gk = Gatekeeper(tmp_path)
    sender = _Sender()
    dispatch.auto_send(config, gk, _VALID_REPORT, sender=sender)
    assert gk.read("report_send")["sent"] is True
    assert json.loads(sender.body) == _VALID_REPORT  # emailed the canonical JSON, no prose


def test_auto_send_swallows_failure_never_crashes_run(config: Config, tmp_path: Path) -> None:
    """A missing credentials.json must NOT crash the autonomous run (E5)."""
    gk = Gatekeeper(tmp_path)
    dispatch.auto_send(config, gk, _VALID_REPORT, sender=_BoomSender())  # no raise
    rec = gk.read("report_send")
    assert rec["sent"] is False and "FileNotFoundError" in rec["error"]


def test_send_latest_missing_file_raises(config: Config, tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        dispatch.send_latest(config, Gatekeeper(tmp_path), tmp_path / "reports", send=True)


def test_send_latest_validates_then_sends(config: Config, tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "internal_game.json").write_text(output.canonical_json(_VALID_REPORT), "utf-8")
    sender = _Sender()
    result = dispatch.send_latest(config, Gatekeeper(tmp_path), reports, send=True, sender=sender)
    assert result["sent"] is True
    assert json.loads(sender.body) == _VALID_REPORT


def test_send_latest_send_false_validates_only(config: Config, tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "internal_game.json").write_text(output.canonical_json(_VALID_REPORT), "utf-8")
    result = dispatch.send_latest(config, Gatekeeper(tmp_path), reports, send=False)
    assert result["sent"] is False and result["report"] == _VALID_REPORT
