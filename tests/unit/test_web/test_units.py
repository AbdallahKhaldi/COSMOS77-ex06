"""Web internals — the passphrase gate, the feed/SSE drain, the emit hook, CLI serve."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from cosmos77_ex06.orchestrator import turn as turn_mod
from cosmos77_ex06.web import security
from cosmos77_ex06.web.feed import MatchFeed


class _Cfg:
    def __init__(self, env: dict[str, str]) -> None:
        self._env = env

    def env(self, key: str) -> str | None:
        return self._env.get(key)


# --- security.passphrase_ok --------------------------------------------------------------


def test_passphrase_match() -> None:
    assert security.passphrase_ok("s3cret", _Cfg({"WEB_PASSPHRASE": "s3cret"})) is True


def test_passphrase_mismatch() -> None:
    assert security.passphrase_ok("nope", _Cfg({"WEB_PASSPHRASE": "s3cret"})) is False


def test_passphrase_env_unset_fails_closed() -> None:
    assert security.passphrase_ok("anything", _Cfg({})) is False


def test_passphrase_empty_supplied_fails_closed() -> None:
    assert security.passphrase_ok("", _Cfg({"WEB_PASSPHRASE": "s3cret"})) is False


# --- MatchFeed ---------------------------------------------------------------------------


def test_feed_stream_order_then_done_and_drops() -> None:
    feed = MatchFeed()
    feed.register("r1")
    feed.publish("r1", {"type": "turn", "n": 1})
    feed.publish("r1", {"type": "done"})

    async def drain() -> list[dict[str, Any]]:
        return [json.loads(frame["data"]) async for frame in feed.stream("r1")]

    out = asyncio.run(drain())
    assert [e["type"] for e in out] == ["turn", "done"]
    assert feed.has("r1") is False  # dropped after the done sentinel


def test_feed_isolation_between_runs() -> None:
    feed = MatchFeed()
    feed.register("a")
    feed.register("b")
    feed.publish("a", {"who": "a"})
    feed.publish("b", {"who": "b"})
    assert feed._queues["a"].get_nowait()["who"] == "a"  # noqa: SLF001 - test inspects queue
    assert feed._queues["b"].get_nowait()["who"] == "b"  # noqa: SLF001


# --- turn._emit_event (the additive core hook) -------------------------------------------

_ENTRY = {
    "sub_game": 1,
    "turn": 2,
    "role": "cop",
    "nl_message": "you're cornered",
    "tool": "apply_move",
    "board": {"cop": [1, 1], "thief": [0, 0], "barriers": []},
    "coord_flagged": False,
}


class _Eng:
    def __init__(self, on_event: Any) -> None:
        self.on_event = on_event


def test_emit_event_none_is_noop() -> None:
    turn_mod._emit_event(_Eng(None), _ENTRY, False)  # noqa: SLF001 - no raise = pass


def test_emit_event_fires_with_positions_and_no_score() -> None:
    got: list[dict[str, Any]] = []
    turn_mod._emit_event(_Eng(got.append), _ENTRY, True)  # noqa: SLF001
    assert len(got) == 1
    event = got[0]
    assert event["type"] == "turn" and event["role"] == "cop"
    assert event["cop_pos"] == [1, 1] and event["thief_pos"] == [0, 0]
    assert event["captured"] is True and "score" not in event


# --- CLI serve dispatch ------------------------------------------------------------------


def test_cli_serve_dispatches_to_server_main(monkeypatch: Any) -> None:
    from cosmos77_ex06.cli.main import main

    called: dict[str, Any] = {}
    monkeypatch.setattr(
        "cosmos77_ex06.web.server.main",
        lambda host=None, port=None: called.update(host=host, port=port),
    )
    assert main(["serve", "--port", "9999"]) == 0
    assert called["port"] == 9999


# --- per-run game settings (grid / moves / games overrides) ------------------------------


class _BaseCfg:
    def __init__(self) -> None:
        self._data = {"grid_size": [5, 5], "max_moves": 25, "num_games": 1}


def test_run_config_applies_and_clamps_overrides() -> None:
    from cosmos77_ex06.web.routes import _run_config

    cfg = _run_config(_BaseCfg(), {"grid": 99, "moves": 2, "games": 50})
    assert cfg._data["grid_size"] == [8, 8]  # grid clamped to 8
    assert cfg._data["max_moves"] == 5  # moves clamped up to the floor of 5
    assert cfg._data["num_games"] == 8  # games clamped to 8


def test_run_config_no_overrides_keeps_defaults() -> None:
    from cosmos77_ex06.web.routes import _run_config

    cfg = _run_config(_BaseCfg(), {})
    assert cfg._data == {"grid_size": [5, 5], "max_moves": 25, "num_games": 1}
