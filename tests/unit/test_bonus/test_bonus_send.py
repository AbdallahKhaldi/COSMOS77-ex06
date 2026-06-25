"""Bonus send dispatch — the professor-safety guard on the byte-identical bonus_game JSON (E12)."""

from __future__ import annotations

from pathlib import Path

import pytest

from cosmos77_ex06.report import dispatch
from cosmos77_ex06.shared.config import Config
from cosmos77_ex06.shared.gatekeeper import Gatekeeper

_SAMPLE = Path(__file__).resolve().parents[3] / "reports" / "bonus_game.sample.json"


class _Sender:
    to = "rmisegal+uoh26b@gmail.com"

    def __init__(self) -> None:
        self.body: str | None = None

    def send(self, body: str) -> dict:
        self.body = body
        return {"id": "bonus-msg-1"}


def _with_bonus(tmp_path: Path) -> Path:
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "bonus_game.json").write_text(_SAMPLE.read_text("utf-8"), "utf-8")
    return reports


def test_bonus_send_missing_file_raises(config: Config, tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        dispatch.send_bonus(
            config, Gatekeeper(tmp_path), tmp_path / "reports", send=True, final=True
        )


def test_bonus_send_to_professor_blocked_without_final(config: Config, tmp_path: Path) -> None:
    """A bare bonus --send to the professor is refused without --final (same guard as the report)."""
    reports = _with_bonus(tmp_path)
    sender = _Sender()
    res = dispatch.send_bonus(config, Gatekeeper(tmp_path), reports, send=True, sender=sender)
    assert res["sent"] is False and res["blocked"] and sender.body is None


def test_bonus_send_final_sends_exact_file_bytes(config: Config, tmp_path: Path) -> None:
    """--final sends; the body is byte-identical to the file both groups diff (mutual agreement)."""
    reports = _with_bonus(tmp_path)
    sender = _Sender()
    res = dispatch.send_bonus(
        config, Gatekeeper(tmp_path), reports, send=True, sender=sender, final=True
    )
    assert res["sent"] is True and res["blocked"] is None
    assert sender.body == _SAMPLE.read_text("utf-8")


def test_bonus_send_to_override_self_test_sends(config: Config, tmp_path: Path) -> None:
    reports = _with_bonus(tmp_path)
    sender = _Sender()
    res = dispatch.send_bonus(
        config,
        Gatekeeper(tmp_path),
        reports,
        send=True,
        sender=sender,
        to="abdallahkh12@icloud.com",
    )
    assert res["sent"] is True and res["blocked"] is None


def test_bonus_send_false_validates_only(config: Config, tmp_path: Path) -> None:
    reports = _with_bonus(tmp_path)
    res = dispatch.send_bonus(config, Gatekeeper(tmp_path), reports, send=False)
    assert res["sent"] is False and res["blocked"] is None
