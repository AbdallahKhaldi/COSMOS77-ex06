"""Transcript recorder tests (PRD §9, E13 void notes)."""

from __future__ import annotations

from cosmos77_ex06.orchestrator.transcript import Transcript


def test_append_records_full_turn_entry() -> None:
    t = Transcript()
    entry = t.append(
        sub_game=1,
        turn=3,
        role="thief",
        nl_message="all quiet up north",
        tool="apply_move",
        args={"role": "thief", "direction": "SW"},
        board={"cop": [1, 4], "thief": [3, 0], "barriers": [], "move": 3},
        mcp_url="http://localhost:8002/mcp",
    )
    assert entry in t.to_list()
    assert t.messages() == ["all quiet up north"]


def test_note_void_is_recorded_separately() -> None:
    t = Transcript()
    t.note_void(2, "dropped MCP connection")
    assert t.voids == [{"sub_game": 2, "reason": "dropped MCP connection"}]
    assert t.to_list() == []  # a voided sub-game is not a scored turn record
