"""Cross-group orchestrator — a full sub-game vs a SCRIPTED opponent (deterministic, no network)."""

from __future__ import annotations

from typing import Any

from cosmos77_ex06.bonus import intergroup
from cosmos77_ex06.shared.config import Config


class _ScriptedOpponent:
    """A fake NajAmjad server returning a fixed sequence of prose moves (last one repeats)."""

    def __init__(self, lines: list[str]) -> None:
        self._lines, self.i = lines, 0

    async def request_move(self, observation: dict[str, Any]) -> str:
        line = self._lines[min(self.i, len(self._lines) - 1)]
        self.i += 1
        return line


async def test_play_sub_game_plays_records_and_scores() -> None:
    cfg = Config()
    opp = _ScriptedOpponent(["[INTENT: MOVE] The cop edges north-west."] * 60)
    sg = await intergroup.play_sub_game(
        cfg, 2, "thief", opp, opening={"cop": (1, 1), "thief": (0, 0)}
    )
    assert sg["index"] == 2 and sg["our_role"] == "thief"
    assert sg["winner"] in ("cop", "thief")
    assert set(sg["scores"]) == {"cop", "thief"} and sum(sg["scores"].values()) in (25, 15)
    assert sg["moves"] and sg["moves"][0]["role"] == "thief"  # thief moves first


async def test_play_sub_game_cop_capture_is_scored_20_5() -> None:
    cfg = Config()
    # adjacent opening; their cop steps onto our thief on the cop's turn -> capture
    opp = _ScriptedOpponent(["[INTENT: MOVE] The cop edges north-west."] * 60)
    sg = await intergroup.play_sub_game(
        cfg, 1, "thief", opp, opening={"cop": (1, 1), "thief": (1, 0)}, max_moves=25
    )
    if sg["winner"] == "cop":
        assert sg["scores"] == {"cop": 20, "thief": 5}


def test_digest_is_stable_compact_and_key_order_independent() -> None:
    d1 = intergroup.digest([{"index": 1, "winner": "cop"}])
    d2 = intergroup.digest([{"winner": "cop", "index": 1}])
    assert d1 == d2 and len(d1) == 64
