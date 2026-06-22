"""Tests for the thin ``cosmos77-pursuit`` CLI dispatcher (CLAUDE.md rule 2)."""

from __future__ import annotations

import pytest

from cosmos77_ex06.cli.main import build_parser, main


def test_version_flag_prints_version(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["--version"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "cosmos77-pursuit 1.00" in out


def test_no_command_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main([])
    assert rc == 0
    assert "cosmos77-pursuit" in capsys.readouterr().out


def test_parser_has_subcommands() -> None:
    parser = build_parser()
    args = parser.parse_args(["run", "--cloud", "--games", "6"])
    assert args.command == "run"
    assert args.cloud is True
    assert args.games == 6


def test_parser_has_local_and_grid_flags() -> None:
    args = build_parser().parse_args(["run", "--local", "--games", "2", "--grid", "3"])
    assert args.local is True and args.games == 2 and args.grid == 3


def test_run_local_routes_to_sdk_and_applies_overrides(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    captured: dict[str, object] = {}

    class _FakeSDK:
        def __init__(self) -> None:
            self.config = type("C", (), {"_data": {"num_games": 6, "grid_size": [5, 5]}})()

        def run_local_game(self, *, gui: bool = False) -> dict[str, object]:
            captured["data"] = dict(self.config._data)
            captured["gui"] = gui
            return {"totals": {"cop": 0, "thief": 20}, "sub_games": [{}, {}]}

    monkeypatch.setattr("cosmos77_ex06.sdk.sdk.SDK", _FakeSDK)
    rc = main(["run", "--local", "--games", "2", "--grid", "3"])
    assert rc == 0
    assert captured["data"] == {"num_games": 2, "grid_size": [3, 3]}
    assert "totals" in capsys.readouterr().out


def test_run_command_routes_to_sdk_stub() -> None:
    # The SDK stage is not wired yet, so dispatch surfaces NotImplementedError.
    with pytest.raises(NotImplementedError):
        main(["run"])


def test_report_command_routes_to_sdk_stub() -> None:
    with pytest.raises(NotImplementedError):
        main(["report", "--send"])


def test_bonus_command_routes_to_sdk_stub() -> None:
    with pytest.raises(NotImplementedError):
        main(["bonus"])
